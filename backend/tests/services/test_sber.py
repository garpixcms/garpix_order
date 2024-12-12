import json
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from garpix_order.exceptions import (
    InvalidOrderStatusPaymentException
)
from garpix_order.models.order import BaseOrder
from garpix_order.models.payments.sber import SberPayment
from garpix_order.services.sber import SberService

User = get_user_model()


@pytest.fixture
def base_order(db):
    user = User.objects.create_user('test', 'test@test.ru', 'test_password')
    return BaseOrder.objects.create(
        user=user,
        total_amount=1000,
        number="order_123"
    )


@pytest.fixture
def sber_payment(base_order, db):
    return SberPayment.objects.create(
        order=base_order,
        external_payment_id="external_123",
        payment_link="https://test.sberbank.ru/payment",
        status="created"
    )


@pytest.fixture
def sber_service():
    return SberService()


@pytest.mark.django_db
class TestSberService:
    def test_request_success(self, mocker, sber_service):
        mock_get = mocker.patch('garpix_order.services.sber.requests.get')
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = json.dumps({'orderId': '12345'}).encode('utf-8')

        response = sber_service._request(
            url='https://test.sberbank.ru/register',
            params={'token': 'test_token'}
        )

        assert response['orderId'] == '12345'
        mock_get.assert_called_once()

    def test_request_failure(self, mocker, sber_service):
        mock_get = mocker.patch('garpix_order.services.sber.requests.get')
        mock_get.side_effect = Exception("Connection error")

        with pytest.raises(Exception, match="Connection error"):
            sber_service._request(
                url='https://test.sberbank.ru/register',
                params={'token': 'test_token'}
            )

    def test_compute_my_checksum(self, sber_service):
        checksum = sber_service._compute_my_checksum(
            secret_key=b'test_key',
            callback_data='test_data'
        )
        assert checksum == '46A5B27B7E6672271C998F4D79ED460FF03C88CACD31355FFC161539E1657824'

    def test_create_payment_success(self, mocker, base_order, sber_service):
        mock_request = mocker.patch('garpix_order.services.sber.SberService._request')
        mock_request.return_value = {
            'orderId': 'external_123',
            'formUrl': 'https://test.sberbank.ru/payment'
        }

        payment = sber_service.create_payment(order=base_order, returnUrl='https://return.url')

        assert payment.external_payment_id == 'external_123'
        assert payment.payment_link == 'https://test.sberbank.ru/payment'
        assert payment.order == base_order

    def test_create_payment_failure(self, mocker, base_order, sber_service):
        mock_request = mocker.patch('garpix_order.services.sber.SberService._request')
        mock_request.return_value = {'errorCode': 5}

        payment = sber_service.create_payment(order=base_order, returnUrl='https://return.url')
        assert payment.status == "failed"

    def test_callback_success(self, sber_service, sber_payment, mocker):
        mock_update_payment = mocker.patch.object(sber_service, 'update_payment')
        mocker.patch.object(
            sber_service,
            '_compute_my_checksum',
            return_value='valid_checksum'
        )
        mocker.patch.object(
            sber_service,
            '_get_cryptographic_key',
            return_value='cripto_key'
        )

        data = {
            'mdOrder': 'external_123',
            'checksum': 'valid_checksum'
        }
        response = sber_service.callback(data)
        assert response.status_code == HTTP_200_OK

        mock_update_payment.assert_called_once_with(payment=sber_payment)

    def test_callback_invalid_checksum(self, sber_service, sber_payment, mocker):
        mocker.patch.object(
            sber_service,
            '_compute_my_checksum',
            return_value='invalid_checksum'
        )

        data = {
            'mdOrder': 'external_123',
            'checksum': 'valid_checksum'
        }
        response = sber_service.callback(data)
        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_update_payment_invalid_order_status(self, mocker, sber_service, sber_payment):
        mock_request = mocker.patch('garpix_order.services.sber.SberService._request')
        mock_request.return_value = {'orderStatus': 999999}

        with pytest.raises(InvalidOrderStatusPaymentException):
            sber_service.update_payment(payment=sber_payment)

    def test_callback_no_cryptographic_key(self, sber_service, sber_payment, monkeypatch):
        monkeypatch.setitem(settings.SBER, 'cryptographic_key', None)

        data = {
            'mdOrder': 'external_123',
            'checksum': 'some_checksum'
        }
        response = sber_service.callback(data)
        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_callback_no_payment_found(self, sber_service, mocker):
        data = {
            'mdOrder': 'nonexistent_order',
            'checksum': 'valid_checksum'
        }
        response = sber_service.callback(data)
        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_callback_no_checksum(self, sber_service, sber_payment):
        data = {
            'mdOrder': 'external_123'
        }
        response = sber_service.callback(data)
        assert response.status_code == HTTP_400_BAD_REQUEST
