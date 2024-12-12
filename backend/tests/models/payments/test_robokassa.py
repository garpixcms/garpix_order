import json
from django.utils import timezone
from django_fsm import TransitionNotAllowed
from django.conf import settings
from app.tests import TestMixin
from garpix_order.models.payments.recurring import Recurring
from garpix_order.models.payments.robokassa import RobokassaPayment
from garpix_order.models.order import BaseOrder
from garpix_order.services.robokassa import robokassa_service

class RobokassaPaymentTestCase(TestMixin):
    @classmethod
    def setUpTestData(cls):
        cls._create_user()
        cls.service = robokassa_service

    def setUp(self):
        self.recurring = Recurring.active_objects.create(
            start_at=timezone.datetime(2014, 1, 31),
            end_at=timezone.datetime(3014, 1, 31),
            frequency=Recurring.RecurringFrequency.MONTH,
            payment_system=Recurring.RecurringPaymentSystem.ROBOKASSA
        )

        self.order_manual_paid = BaseOrder.objects.create(
            number=1,
            user=self.user,
            total_amount=300,
            payed_amount=300,
            status=BaseOrder.OrderStatus.PAYED_FULL,
        )
        self.order_auto_paid = BaseOrder.objects.create(
            number=2,
            user=self.user,
            total_amount=300,
            payed_amount=300,
            status=BaseOrder.OrderStatus.PAYED_FULL,
            recurring=self.recurring,
        )
        self.robokassa_manual_payment_paid = RobokassaPayment.objects.create(
            order=self.order_manual_paid,
            amount=300,
            status=RobokassaPayment.PaymentStatus.PENDING,
        )
        self.robokassa_auto_payment_paid = RobokassaPayment.objects.create(
            order=self.order_auto_paid,
            amount=300,
            payment_type=RobokassaPayment.PaymentType.AUTO,
            status=RobokassaPayment.PaymentStatus.PENDING,
        )

        self.order_manual_unpaid = BaseOrder.objects.create(
            number=1,
            user=self.user,
            total_amount=300,
        )
        self.order_auto_unpaid = BaseOrder.objects.create(
            number=2,
            user=self.user,
            total_amount=300,
            recurring=self.recurring,
        )
        self.robokassa_manual_payment_unpaid = RobokassaPayment.objects.create(
            order=self.order_manual_unpaid,
            amount=300,
        )
        self.robokassa_auto_payment_unpaid = RobokassaPayment.objects.create(
            order=self.order_auto_unpaid,
            amount=300,
            payment_type=RobokassaPayment.PaymentType.AUTO,
        )

    def test_refund_manual_paid_payment(self):
        self.robokassa_manual_payment_paid.refund()

        self.robokassa_manual_payment_paid.refresh_from_db()
        self.order_manual_paid.refresh_from_db()

        self.assertEqual(self.order_manual_paid.payed_amount, 0)
        self.assertEqual(self.robokassa_manual_payment_paid.status, RobokassaPayment.PaymentStatus.REFUNDED)
        self.assertEqual(self.order_manual_paid.status, BaseOrder.OrderStatus.REFUNDED)

    def test_refund_auto_paid_payment(self):
        self.robokassa_auto_payment_paid.refund()

        self.robokassa_auto_payment_paid.refresh_from_db()
        self.order_auto_paid.refresh_from_db()

        self.assertEqual(self.order_auto_paid.payed_amount, 0)
        self.assertEqual(self.robokassa_auto_payment_paid.status, RobokassaPayment.PaymentStatus.REFUNDED)
        self.assertEqual(self.order_auto_paid.status, BaseOrder.OrderStatus.REFUNDED)

    def test_refund_manual_paid_payment_with_two_payments_order(self):
        second_payment = RobokassaPayment.objects.create(
            order=self.order_manual_paid,
            amount=300,
            payment_type=RobokassaPayment.PaymentType.AUTO,
        )
        self.order_manual_paid.total_amount += second_payment.amount
        self.order_manual_paid.payed_amount += second_payment.amount
        self.order_manual_paid.save(update_fields=['total_amount', 'payed_amount'])

        self.robokassa_manual_payment_paid.refund()

        self.robokassa_manual_payment_paid.refresh_from_db()
        self.order_manual_paid.refresh_from_db()

        self.assertEqual(self.order_manual_paid.payed_amount, second_payment.amount)
        self.assertEqual(self.robokassa_manual_payment_paid.status, RobokassaPayment.PaymentStatus.REFUNDED)
        self.assertEqual(self.order_manual_paid.status, BaseOrder.OrderStatus.PAYED_PARTIAL)

    def test_refund_auto_paid_payment_with_two_payments_order(self):
        second_payment = RobokassaPayment.objects.create(
            order=self.order_auto_paid,
            amount=300,
            payment_type=RobokassaPayment.PaymentType.AUTO,
        )
        self.order_auto_paid.total_amount += second_payment.amount
        self.order_auto_paid.payed_amount += second_payment.amount
        self.order_auto_paid.save(update_fields=['total_amount', 'payed_amount'])

        self.robokassa_auto_payment_paid.refund()

        self.robokassa_auto_payment_paid.refresh_from_db()
        self.order_auto_paid.refresh_from_db()

        self.assertEqual(self.order_auto_paid.payed_amount, second_payment.amount)
        self.assertEqual(self.robokassa_auto_payment_paid.status, RobokassaPayment.PaymentStatus.REFUNDED)
        self.assertEqual(self.order_auto_paid.status, BaseOrder.OrderStatus.PAYED_PARTIAL)

    def test_refund_manual_unpaid_payment(self):
        with self.assertRaises(TransitionNotAllowed):
            self.robokassa_manual_payment_unpaid.refund()

    def test_refund_auto_unpaid_payment(self):
        with self.assertRaises(TransitionNotAllowed):
            self.robokassa_auto_payment_unpaid.refund()

    def test_cancel_manual_pending_payment(self):
        pending_manual_payment = RobokassaPayment.objects.create(
            order=self.order_manual_paid,
            amount=300,
            status=RobokassaPayment.PaymentStatus.PENDING,
        )

        pending_manual_payment.cancel()

        pending_manual_payment.refresh_from_db()

        self.assertEqual(pending_manual_payment.status, RobokassaPayment.PaymentStatus.CANCELED)

    def test_cancel_auto_pending_payment(self):
        pending_auto_payment = RobokassaPayment.objects.create(
            order=self.order_manual_paid,
            amount=300,
            status=RobokassaPayment.PaymentStatus.PENDING,
            payment_type=RobokassaPayment.PaymentType.AUTO,
        )

        pending_auto_payment.cancel()

        pending_auto_payment.refresh_from_db()

        self.assertEqual(pending_auto_payment.status, RobokassaPayment.PaymentStatus.CANCELED)

    def test_cancel_manual_paid_payment(self):
        self.robokassa_manual_payment_paid.status = RobokassaPayment.PaymentStatus.SUCCEEDED
        self.robokassa_manual_payment_paid.save(update_fields=['status'])

        with self.assertRaises(TransitionNotAllowed):
            self.robokassa_manual_payment_paid.cancel()

    def test_cancel_auto_paid_payment(self):
        self.robokassa_auto_payment_paid.status = RobokassaPayment.PaymentStatus.SUCCEEDED
        self.robokassa_auto_payment_paid.save(update_fields=['status'])

        with self.assertRaises(TransitionNotAllowed):
            self.robokassa_auto_payment_paid.cancel()

    def test_pay_pending_manual_payment(self):
        created_payment = RobokassaPayment.objects.create(
            order=self.order_manual_unpaid,
            amount=300,
            status=RobokassaPayment.PaymentStatus.PENDING,
        )

        result, error = created_payment.pay(data={})

        self.assertEqual(result, False)
        self.assertEqual(error, 'Invoice already in process')

    def test_pay_pending_auto_payment(self):
        created_payment = RobokassaPayment.objects.create(
            order=self.order_auto_unpaid,
            amount=300,
            status=RobokassaPayment.PaymentStatus.PENDING,
            payment_type=RobokassaPayment.PaymentType.AUTO
        )

        result, error = created_payment.pay(data={}, auto=True)

        self.assertEqual(result, False)
        self.assertEqual(error, 'Invoice already in process')

    def test_pay_zero_amount_manual_payment(self):
        zero_amount_payment = RobokassaPayment.objects.create(
            order=self.order_manual_unpaid,
            amount=0,
            status=RobokassaPayment.PaymentStatus.CREATED,
        )

        result, error = zero_amount_payment.pay(data={})

        self.assertEqual(result, False)
        self.assertEqual(error, 'It is not possible to pay 0 amount')
        self.assertEqual(zero_amount_payment.provider_data, json.dumps({'msg': 'It is not possible to pay 0 amount'}))
        self.assertEqual(zero_amount_payment.status, RobokassaPayment.PaymentStatus.FAILED)

    def test_pay_zero_amount_auto_payment(self):
        zero_amount_payment = RobokassaPayment.objects.create(
            order=self.order_auto_unpaid,
            amount=0,
            status=RobokassaPayment.PaymentStatus.CREATED,
            payment_type=RobokassaPayment.PaymentType.AUTO
        )

        result, error = zero_amount_payment.pay(data={}, auto=True)

        self.assertEqual(result, False)
        self.assertEqual(error, 'It is not possible to pay 0 amount')
        self.assertEqual(zero_amount_payment.provider_data, json.dumps({'msg': 'It is not possible to pay 0 amount'}))
        self.assertEqual(zero_amount_payment.status, RobokassaPayment.PaymentStatus.FAILED)

    def test_pay_invalid_signature_manual_payment(self):
        invalid_signature_payment = RobokassaPayment.objects.create(
            order=self.order_manual_unpaid,
            amount=300,
            status=RobokassaPayment.PaymentStatus.CREATED,
        )

        result, error = invalid_signature_payment.pay(data={'OutSum': 'OutSum', 'SignatureValue': 'SignatureValue'})

        self.assertEqual(result, False)
        self.assertEqual(error, 'Invalid signature')
        self.assertEqual(invalid_signature_payment.provider_data, json.dumps({'msg': 'Invalid signature'}))
        self.assertEqual(invalid_signature_payment.status, RobokassaPayment.PaymentStatus.FAILED)

    def test_pay_invalid_signature_auto_payment(self):
        invalid_signature_payment = RobokassaPayment.objects.create(
            order=self.order_auto_unpaid,
            amount=300,
            status=RobokassaPayment.PaymentStatus.CREATED,
            payment_type=RobokassaPayment.PaymentType.AUTO
        )

        result, error = invalid_signature_payment.pay(data={'OutSum': 'OutSum', 'SignatureValue': 'SignatureValue'}, auto=True)

        self.assertEqual(result, False)
        self.assertEqual(error, 'Invalid signature')
        self.assertEqual(invalid_signature_payment.provider_data, json.dumps({'msg': 'Invalid signature'}))
        self.assertEqual(invalid_signature_payment.status, RobokassaPayment.PaymentStatus.FAILED)

    def test_pay_success_manual_payment(self):
        success_payment = RobokassaPayment.objects.create(
            order=self.order_manual_unpaid,
            amount=300,
            status=RobokassaPayment.PaymentStatus.CREATED,
        )

        signature = self.service.calculate_signature('OutSum', success_payment.id, settings.ROBOKASSA['PASSWORD_2'])
        result = success_payment.pay(data={'OutSum': 'OutSum', 'SignatureValue': signature})

        self.order_manual_paid.refresh_from_db()

        self.assertEqual(result, True)
        self.assertEqual(success_payment.provider_data, json.dumps({'msg': 'Payment is successful'}))
        self.assertEqual(success_payment.status, RobokassaPayment.PaymentStatus.SUCCEEDED)
        self.assertEqual(self.order_manual_paid.status, BaseOrder.OrderStatus.PAYED_FULL)

    def test_pay_success_auto_payment(self):
        success_payment = RobokassaPayment.objects.create(
            order=self.order_auto_unpaid,
            amount=300,
            status=RobokassaPayment.PaymentStatus.CREATED,
            payment_type=RobokassaPayment.PaymentType.AUTO
        )

        signature = self.service.calculate_signature('OutSum', success_payment.id, settings.ROBOKASSA['PASSWORD_2'])
        result = success_payment.pay(data={'OutSum': 'OutSum', 'SignatureValue': signature}, auto=True)

        self.order_auto_paid.refresh_from_db()

        self.assertEqual(result, True)
        self.assertEqual(success_payment.provider_data, json.dumps({'msg': 'Payment is successful'}))
        self.assertEqual(success_payment.status, RobokassaPayment.PaymentStatus.SUCCEEDED)
        self.assertEqual(self.order_auto_paid.status, BaseOrder.OrderStatus.PAYED_FULL)
