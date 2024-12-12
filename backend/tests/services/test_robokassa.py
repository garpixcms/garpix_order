import json
from unittest.mock import patch
from urllib import parse
from django.conf import settings
from django.utils import timezone
from app.tests import TestMixin
from garpix_order.models.order import BaseOrder
from garpix_order.models.payment import BasePayment
from garpix_order.models.payments.robokassa import RobokassaPayment
from garpix_order.models.payments.recurring import Recurring
from garpix_order.services.robokassa import robokassa_service

class BaseOrderTestCase(TestMixin):
    @classmethod
    def setUpTestData(cls):
        cls._create_user()
        cls.service = robokassa_service

    def test_get_amount_with_decimals(self):
        order = BaseOrder.objects.create(user=self.user, total_amount=300, number='test')

        amount = self.service.get_amount_with_decimals(order.total_amount)

        self.assertEqual(amount, '300.00')

    def test_get_amount_with_decimals_for_zero(self):
        order = BaseOrder.objects.create(user=self.user, total_amount=0, number='test')

        amount = self.service.get_amount_with_decimals(order.total_amount)

        self.assertEqual(amount, '0.00')

    def test_get_amount_with_decimals_for_negative_amount(self):
        order = BaseOrder.objects.create(user=self.user, total_amount=-300, number='test')

        amount = self.service.get_amount_with_decimals(order.total_amount)

        self.assertEqual(amount, '-300.00')

    def test_generate_payment_link(self):
        order = BaseOrder.objects.create(user=self.user, total_amount=300, number='test')
        payment = BasePayment.objects.create(title='test', order=order, amount=300)

        order_number = str(payment.id)
        expected_signature = robokassa_service.calculate_signature(
            settings.ROBOKASSA['LOGIN'], '300.00', str(payment.id), settings.ROBOKASSA['PASSWORD_1']
        )

        expected_data = {
            'MerchantLogin': settings.ROBOKASSA['LOGIN'],
            'OutSum': '300.00',
            'InvId': order_number,
            'SignatureValue': expected_signature,
            'IsTest': settings.ROBOKASSA['IS_TEST']
        }

        payment_link = robokassa_service.generate_payment_link(payment)

        self.assertEqual(payment_link, f'{robokassa_service.payment_url}?{parse.urlencode(expected_data)}')

    def test_check_success_payment_for_manual_payment(self):
        order = BaseOrder.objects.create(user=self.user, total_amount=300, number='test')
        payment = BasePayment.objects.create(title='test', order=order, amount=300)

        signature = robokassa_service.calculate_signature(
            '300.00', str(payment.id), settings.ROBOKASSA['PASSWORD_2']
        )

        data = {
            'OutSum': '300.00',
            'SignatureValue': signature,
        }

        result, error = robokassa_service.check_success_payment(payment, data)

        self.assertEqual(result, True)
        self.assertEqual(error, '')

    def test_check_success_payment_for_manual_payment_with_invalid_signature(self):
        order = BaseOrder.objects.create(user=self.user, total_amount=300, number='test')
        payment = BasePayment.objects.create(title='test', order=order, amount=300)

        signature = robokassa_service.calculate_signature(
            '300.00', str(payment.id), 'invalid_password'
        )

        data = {
            'OutSum': '300.00',
            'SignatureValue': signature,
        }

        result, error = robokassa_service.check_success_payment(payment, data)

        self.assertEqual(result, False)
        self.assertEqual(error, 'Invalid signature')

    @patch.object(robokassa_service, 'check_success_payment', return_value=(True, ''))
    def test_create_recurring_payments(self, mock_check_success_payment):
        recurring = Recurring.active_objects.create(
            start_at=timezone.datetime(2014, 1, 31),
            end_at=timezone.datetime(3014, 1, 31),
            frequency=Recurring.RecurringFrequency.MONTH,
            payment_system=Recurring.RecurringPaymentSystem.ROBOKASSA
        )
        order = BaseOrder.objects.create(user=self.user, total_amount=300, number='test', next_payment_date=timezone.now(), recurring=recurring)

        robokassa_service.create_recurring_payments()
        order.refresh_from_db()

        created_payment_qs = RobokassaPayment.objects.filter(
            order=order,
            amount=order.total_amount,
            payment_type=RobokassaPayment.PaymentType.AUTO
        )
        self.assertEqual(created_payment_qs.count(), 1)

        created_payment = created_payment_qs.first()
        self.assertEqual(created_payment.status, RobokassaPayment.PaymentStatus.SUCCEEDED)
        self.assertEqual(created_payment.provider_data, json.dumps({'msg': 'Payment is successful'}))
        self.assertEquals(order.status, BaseOrder.OrderStatus.PAYED_FULL)
