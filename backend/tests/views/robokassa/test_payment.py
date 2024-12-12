import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from garpix_order.models import RobokassaPayment, BaseOrder
from garpix_order.services.robokassa import robokassa_service

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def base_order(db):
    user = User.objects.create_user('test', 'test@test.ru', 'test_password')
    return BaseOrder.objects.create(
        user=user,
        total_amount=1000,
        number="test_order"
    )

@pytest.fixture
def robokassa_payment(db, base_order):
    return RobokassaPayment.objects.create(
        amount=100.00,
        title="Test Payment",
        order=base_order
    )

@pytest.mark.django_db
class TestRobokassaView:
    def test_create_payment(self, api_client, base_order, mocker):
        url = reverse('garpix_order:robokassa-list')
        data = {
            "title": "Test Payment",
            "order": base_order.id,
            "amount": 200.00
        }

        mock_generate_link = mocker.patch(
            'garpix_order.models.RobokassaPayment.generate_payment_link',
            return_value="http://mocked-payment-link.com"
        )

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == "http://mocked-payment-link.com"
        mock_generate_link.assert_called_once()

        payment = RobokassaPayment.objects.get(order=base_order)
        assert payment.amount == 200.00
        assert payment.status == RobokassaPayment.PaymentStatus.CREATED

    def test_list_payments(self, api_client, base_order, robokassa_payment):
        url = reverse('garpix_order:robokassa-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data == [{
            'title': 'Test Payment',
            'order': base_order.id,
            'amount': '100.00'
        }]

    def test_pay_success(self, api_client, robokassa_payment, mocker):
        url = reverse('garpix_order:robokassa-pay', args=[robokassa_payment.id])

        # Мокаем метод check_success_payment для имитации успешной проверки подписи
        mocker.patch.object(robokassa_service, 'check_success_payment', return_value=(True, ''))

        out_sum = robokassa_service.get_amount_with_decimals(robokassa_payment.amount)
        signature = robokassa_service.calculate_signature(out_sum, robokassa_payment.id, robokassa_service.password_2)

        data = {
            "OutSum": out_sum,
            "SignatureValue": signature,
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['result'] == 'success'

        robokassa_payment.refresh_from_db()
        assert robokassa_payment.status == RobokassaPayment.PaymentStatus.SUCCEEDED

    def test_pay_failure_invalid_signature(self, api_client, robokassa_payment, mocker):
        url = reverse('garpix_order:robokassa-pay', args=[robokassa_payment.id])

        # Мокаем метод check_success_payment для имитации проверки подписи с ошибкой
        mocker.patch.object(robokassa_service, 'check_success_payment', return_value=(False, 'Invalid signature'))

        data = {
            "OutSum": "100.00",
            "SignatureValue": "invalid_signature",
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['result'] == ['Invalid signature']

        robokassa_payment.refresh_from_db()
        assert robokassa_payment.status == RobokassaPayment.PaymentStatus.FAILED
