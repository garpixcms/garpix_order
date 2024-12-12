from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from garpix_order.models import BaseOrder
from garpix_order.models import Config
from garpix_order.models.payments.cloudpayments import CloudPayment
from garpix_order.utils import hmac_sha256
from garpix_order.views.cloudpayments import CloudpaymentView

User = get_user_model()


@pytest.fixture
def config(db):
    c = Config.get_solo()
    c.cloudpayments_public_id = 'test_public_id'
    c.cloudpayments_password_api = 'test_api_password'
    c.save()
    return c


@pytest.fixture
def base_order(db):
    user = User.objects.create_user('test', 'test@test.ru', 'test_password')
    return BaseOrder.objects.create(
        user=user,
        total_amount=1000,
        number="order_123"
    )


@pytest.fixture
def payment(db, base_order):
    return CloudPayment.objects.create(
        order=base_order,
        amount=Decimal('100.00'),
        order_number='12345'
    )


@pytest.mark.django_db
class TestCloudPayments:
    def test_payment_data_view_with_existing_payment(self, client, config, payment):
        url = '/cloudpayments/payment_data/'
        response = client.get(url, {'payment_uuid': payment.payment_uuid})
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data['publicId'] == config.cloudpayments_public_id
        assert data['amount'] == str(payment.amount)
        assert data['invoiceId'] == payment.order_number

    def test_payment_data_view_with_nonexistent_payment(self, client, config):
        url = '/cloudpayments/payment_data/'
        response = client.get(url, {'payment_uuid': 'nonexistent'})
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert 'error' in data

    def test_default_view_correct_hmac(self, mocker, client, config, payment):
        url = '/cloudpayments/pay/'
        post_data = {
            'InvoiceId': payment.payment_uuid,
            'Amount': '100.00',
            'Status': 'Completed',
            'TestMode': '1',
            'TransactionId': 'tx_123'
        }
        mocked_callback = mocker.Mock()
        mocked_init_callback = mocker.patch.object(CloudpaymentView, 'init_callback', return_value=mocked_callback)

        hmac_string = '&'.join([f'{k}={v}' for k, v in post_data.items()])
        local_hmac = hmac_sha256(hmac_string, config.cloudpayments_password_api).decode('utf-8')

        response = client.post(url, post_data, HTTP_X_CONTENT_HMAC=local_hmac)

        mocked_init_callback.assert_called_once()
        mocked_callback.callback.assert_called_once_with(payment)

        data = response.json()
        assert response.status_code == status.HTTP_200_OK
        assert data['code'] == 0
        payment.refresh_from_db()
        assert payment.status == CloudPayment.PAYMENT_STATUS_COMPLETED
        assert payment.transaction_id == 'tx_123'
        assert payment.is_test is True

    def test_default_view_wrong_hmac(self, client, config, payment):
        url = '/cloudpayments/pay/'
        post_data = {
            'InvoiceId': payment.payment_uuid,
            'Amount': '100.00',
            'Status': 'Completed',
        }
        response = client.post(url, post_data, HTTP_X_CONTENT_HMAC='wrong_hmac')
        data = response.json()
        assert response.status_code == status.HTTP_200_OK
        assert data['code'] == 13

    def test_default_view_wrong_amount(self, client, config, payment):
        url = '/cloudpayments/pay/'
        post_data = {
            'InvoiceId': payment.payment_uuid,
            'Amount': '200.00',
            'Status': 'Completed',
        }
        hmac_string = '&'.join([f'{k}={v}' for k, v in post_data.items()])
        local_hmac = hmac_sha256(hmac_string, config.cloudpayments_password_api).decode('utf-8')
        response = client.post(url, post_data, HTTP_X_CONTENT_HMAC=local_hmac)
        data = response.json()
        assert response.status_code == status.HTTP_200_OK
        assert data['code'] == 13

    def test_fail_view(self, client, config, payment):
        url = '/cloudpayments/fail/'
        post_data = {
            'InvoiceId': payment.payment_uuid,
            'Amount': '100.00',
            'Status': 'Completed',
        }
        response = client.post(url, post_data)
        assert response.status_code == status.HTTP_200_OK
