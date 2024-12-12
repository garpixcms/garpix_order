import json
from django_fsm import TransitionNotAllowed
from app.tests import TestMixin
from garpix_order.models.order import BaseOrder
from garpix_order.models.payment import BasePayment

class BaseOrderTestCase(TestMixin):
    @classmethod
    def setUpTestData(cls):
        cls._create_user()

    def test_make_refunded(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100)

        refunded_payment = BasePayment.make_refunded(payment)

        self.assertTrue(refunded_payment is not None)
        self.assertEqual(refunded_payment.title, f'{payment.title}_refunded')
        self.assertEqual(refunded_payment.order, payment.order)
        self.assertEqual(refunded_payment.amount, payment.amount)

    def test_pay_full(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100)

        payment.pay_full()
        order.refresh_from_db()

        self.assertEqual(order.status, BaseOrder.OrderStatus.PAYED_FULL)
        self.assertEqual(order.payed_amount, 100)

    def test_pay_full_to_get_order_partialy_paid(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=50)

        payment.pay_full()
        order.refresh_from_db()

        self.assertEqual(order.status, BaseOrder.OrderStatus.PAYED_PARTIAL)
        self.assertEqual(order.payed_amount, 50)

    def test_pay_full_with_already_partialy_paid_order(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100, payed_amount=50)
        payment = BasePayment.objects.create(title='test', order=order, amount=50)
        already_paid_payment = BasePayment.objects.create(title='test', order=order, amount=50, status=BasePayment.PaymentStatus.SUCCEEDED)

        payment.pay_full()
        order.refresh_from_db()

        self.assertEqual(order.status, BaseOrder.OrderStatus.PAYED_FULL)
        self.assertEqual(order.payed_amount, 100)

    def test_pending_with_created_payment(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100)

        payment.pending()

        self.assertEqual(payment.status, BasePayment.PaymentStatus.PENDING)

    def test_pending_with_invalid_source_status(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.SUCCEEDED)

        with self.assertRaises(TransitionNotAllowed):
            payment.pending()

    def test_waiting_for_capture_with_pending_payment(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.PENDING)

        payment.waiting_for_capture()

        self.assertEqual(payment.status, BasePayment.PaymentStatus.WAITING_FOR_CAPTURE)

    def test_waiting_for_capture_with_invalid_source_status(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.SUCCEEDED)

        with self.assertRaises(TransitionNotAllowed):
            payment.waiting_for_capture()

    def test_succeeded_with_pending_payment(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.PENDING)

        payment.succeeded()

        self.assertEqual(payment.status, BasePayment.PaymentStatus.SUCCEEDED)
        self.assertEqual(order.status, BaseOrder.OrderStatus.PAYED_FULL)

    def test_succeded_with_invalid_source_status(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.SUCCEEDED)

        with self.assertRaises(TransitionNotAllowed):
            payment.succeeded()

    def test_succeeded_with_negative_amount_payment(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=-100)

        with self.assertRaises(TransitionNotAllowed):
            payment.succeeded()

    def test_canceled_with_pending_payment(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.PENDING)

        payment.canceled()

        self.assertEqual(payment.status, BasePayment.PaymentStatus.CANCELED)

    def test_canceled_with_invalid_source_status(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.SUCCEEDED)

        with self.assertRaises(TransitionNotAllowed):
            payment.canceled()

    def test_refunded_with_pending_payment(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100, payed_amount=100, status=BaseOrder.OrderStatus.PAYED_FULL)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.PENDING)

        payment.refunded()
        order.refresh_from_db()

        self.assertEqual(payment.status, BasePayment.PaymentStatus.REFUNDED)
        self.assertEqual(order.status, BaseOrder.OrderStatus.REFUNDED)

    def test_refunded_with_invalid_source_status(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.SUCCEEDED)

        with self.assertRaises(TransitionNotAllowed):
            payment.refunded()

    def test_refunded_to_get_partial_refunded_order(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100, payed_amount=100, status=BaseOrder.OrderStatus.PAYED_FULL)
        payment = BasePayment.objects.create(title='test', order=order, amount=50, status=BasePayment.PaymentStatus.PENDING)

        payment.refunded()
        order.refresh_from_db()

        self.assertEqual(payment.status, BasePayment.PaymentStatus.REFUNDED)
        self.assertEqual(order.status, BaseOrder.OrderStatus.PAYED_PARTIAL)

    def test_failed_with_pending_payment(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.PENDING)

        payment.failed()

        self.assertEqual(payment.status, BasePayment.PaymentStatus.FAILED)

    def test_failed_with_invalid_source_status(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.SUCCEEDED)

        with self.assertRaises(TransitionNotAllowed):
            payment.failed()

    def test_closed(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100)

        payment.closed()

        self.assertEqual(payment.status, BasePayment.PaymentStatus.CLOSED)

    def test_timeout_with_pending_payment(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.PENDING)

        payment.timeout()

        self.assertEqual(payment.status, BasePayment.PaymentStatus.TIMEOUT)

    def test_timeout_with_invalid_source_status(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100, status=BasePayment.PaymentStatus.SUCCEEDED)

        with self.assertRaises(TransitionNotAllowed):
            payment.timeout()

    def test_set_provider_data(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100)

        payment.set_provider_data({'test': 'test'})

        self.assertEqual(payment.provider_data, json.dumps({'test': 'test'}))
