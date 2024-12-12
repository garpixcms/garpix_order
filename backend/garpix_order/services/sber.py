import logging
import time
import requests
from requests import RequestException
import json
from typing import Optional, TypedDict, Type
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac

from django.conf import settings
from django.utils.module_loading import import_string

from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from ..models import BaseOrder, BasePayment, SberPaymentStatus, AbstractSberPayment
from ..types.sber import (
    CreatePaymentData, GetPaymentData, PaymentCreationData, FailedPaymentCreationData
)
from ..exceptions import (
    UndefinedModelPaymentException, InvalidModelPaymentException, InvalidOrderStatusPaymentException
)


logger = logging.getLogger(__name__)


# Sber REST Docs - https://securecardpayment.ru/wiki/doku.php/integration:api:rest:start

class SberService:
    API_URL = settings.SBER.get('api_url')
    TOKEN = settings.SBER.get('token')
    CRYPTOGRAPHIC_KEY = settings.SBER.get('cryptographic_key')
    URLS = {
        'register': f'{API_URL}/register.do',
        'get_order_status_extended': f'{API_URL}/getOrderStatusExtended.do',
    }
    TIMEOUT = 5

    def __init__(self) -> None:
        super().__init__()

    def get_payment_model(self):
        payment_model_path = getattr(settings, 'SBER_PAYMENT_MODEL', None)

        if payment_model_path is None:
            raise UndefinedModelPaymentException

        payment_model = import_string(payment_model_path)

        if not issubclass(payment_model, AbstractSberPayment):
            raise InvalidModelPaymentException

        return payment_model

    def _make_params_for_create_payment(self, order: BaseOrder, **kwargs) -> CreatePaymentData:
        """
        Возвращает params для запроса при создании платежа.
        """
        assert 'returnUrl' in kwargs, f'You must include "returnUrl" parameter in kwargs for {self.__class__.__name__}.create_payment() method.'
        return CreatePaymentData(
            token=self.TOKEN,
            amount=int(order.total_amount) * 100,
            orderNumber=order.number,
            **kwargs
        )

    def _make_params_for_get_payment_data(self, external_payment_id: str, **kwargs) -> GetPaymentData:
        """
        Возвращает params для запроса при получении статуса платежа.
        """
        return GetPaymentData(
            token=self.TOKEN,
            orderId=external_payment_id,
            **kwargs
        )

    def _change_payment_status(self, payment: BasePayment, order_status: int) -> None:
        """
        Изменяет статус модели SberPayment в зависимости от полученного от Сбера статуса.
        """
        if order_status == SberPaymentStatus.PENDING:
            payment.pending()
        elif order_status == SberPaymentStatus.WAITING_FOR_CAPTURE:
            payment.waiting_for_capture()
        elif order_status == SberPaymentStatus.FULL_PAID:
            payment.succeeded()
        elif order_status == SberPaymentStatus.CANCELLED:
            payment.canceled()
        elif order_status == SberPaymentStatus.REFUNDED:
            payment.refunded()
        elif order_status == SberPaymentStatus.DECLINED:
            payment.failed()
        else:
            raise InvalidOrderStatusPaymentException

        payment.save()

    def _compute_my_checksum(self, secret_key: bytes, callback_data: str) -> str:
        """
        Вычисляет чексумму из данных полученных в callback-уведомлении.
        """
        h = hmac.HMAC(secret_key, hashes.SHA256(), backend=default_backend())
        h.update(callback_data.encode())
        my_checksum = h.finalize().hex().upper()

        return my_checksum

    def _get_cryptographic_key(self) -> Optional[bytes]:
        """
        Возвращает криптографический ключ для вычисления чексуммы.
        """
        secret_key = self.CRYPTOGRAPHIC_KEY

        if not secret_key:
            return None

        return secret_key.encode()

    def _request(self, url: str, params: Type[TypedDict]) -> dict:
        """
        Отправляет GET-запрос и возвращает полученные данные в виде словаря.
        Логирует url запроса и ошибку в случае возникновения.
        """
        try:
            cert_path = settings.SBER.get('cert_path', None)
            response = requests.get(url=url, params=params, timeout=self.TIMEOUT, verify=cert_path)
            logger.info(f'Request URL: {response.request.url}')
            response.raise_for_status()
            return json.loads(response.content)
        except RequestException as e:
            logger.error(f'Error processing request: {e}')
            raise e

    def create_payment(self, order: BaseOrder, **kwargs) -> BasePayment:
        """
        Создает платеж в системе Сбера. Возвращает модель SberPayment со ссылкой на оплату в поле payment_link.
        """
        params = self._make_params_for_create_payment(order=order, **kwargs)

        created_payment_data = self._request(url=self.URLS['register'], params=params)

        external_payment_id = created_payment_data.get('orderId')
        payment_link = created_payment_data.get('formUrl')
        error_code = created_payment_data.get('errorCode')  # Если error_code == 0 или не пришел, значит ошибок нет

        params = dict(params)
        params.pop('token', None)

        # Произошла системная ошибка
        if (error_code and int(error_code) != 0) or not external_payment_id or not payment_link:
            payment_creation_data = FailedPaymentCreationData(
                order=order,
                amount=order.total_amount,
                client_data=json.dumps(params, ensure_ascii=False),
                provider_data=json.dumps(created_payment_data, ensure_ascii=False),
                title=f'Платеж по заказу № {order.id}',
            )

            payment = self.get_payment_model().objects.create(**payment_creation_data)
            payment.failed()
            payment.save()

            return payment

        payment_creation_data = PaymentCreationData(
            order=order,
            amount=order.total_amount,
            external_payment_id=external_payment_id,
            payment_link=payment_link,
            client_data=json.dumps(params, ensure_ascii=False),
            provider_data=json.dumps(created_payment_data, ensure_ascii=False),
            title=f'Платеж по заказу № {order.id}',
        )

        return self.get_payment_model().objects.create(**payment_creation_data)

    def update_payment(self, payment: BasePayment, **kwargs) -> None:
        """
        Обновляет модель SberPayment с соответствующим внешним id платежа в системе Сбера на основании статуса,
        полученного от сбера в callback-уведомлении.
        """
        if not payment.external_payment_id:
            return None

        params = self._make_params_for_get_payment_data(external_payment_id=payment.external_payment_id, **kwargs)

        payment_data = self._request(url=self.URLS['get_order_status_extended'], params=params)

        order_status = payment_data.get('orderStatus')
        error_code = payment_data.get('errorCode')  # Если error_code == 0 или не пришел, значит ошибок нет
        payment.provider_data = json.dumps(payment_data, ensure_ascii=False)

        if order_status is not None:  # Пришел внешний статус заказа
            order_status = int(order_status)
            self._change_payment_status(payment=payment, order_status=order_status)

        if error_code and int(error_code) != 0:  # Произошла системная ошибка
            payment.save()

    def callback(self, data: dict, **kwargs) -> Response:
        """
        Получает данные из callback-уведомления, сверяет полученную от Сбера чексумму с рассчитанной нами на основании
        криптографического ключа, если они совпадают, то обновляет статус платежа.
        """
        data.pop('sign_alias', None)
        checksum = data.pop('checksum', None)
        callback_data = ''.join([f'{k};{v};' for k, v in sorted(list(data.items()))])

        payment = self.get_payment_model().objects.filter(external_payment_id=data.get('mdOrder')).first()

        if not payment:
            return Response(status=HTTP_400_BAD_REQUEST)

        secret_key = self._get_cryptographic_key()

        if not secret_key:
            return Response(status=HTTP_400_BAD_REQUEST)

        my_checksum = self._compute_my_checksum(secret_key=secret_key, callback_data=callback_data)

        if checksum == my_checksum:
            self.update_payment(payment=payment, **kwargs)
            return Response(status=HTTP_200_OK)

        return Response(status=HTTP_400_BAD_REQUEST)


sber_service = SberService()
