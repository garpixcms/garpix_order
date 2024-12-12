from app.tests import TestMixin
from garpix_order.models.order import BaseOrder
from garpix_order.models.payment import BasePayment
from garpix_order.models.order_item import BaseOrderItem

class BaseOrderTestCase(TestMixin):
    @classmethod
    def setUpTestData(cls):
        cls._create_user()

    def test_make_full_payment_without_kwargs(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        order.make_full_payment()

        created_payment = BasePayment.objects.filter(order=order, amount=order.total_amount).first()
        self.assertTrue(created_payment is not None)
        self.assertEqual(created_payment.order, order)
        self.assertEqual(created_payment.amount, order.total_amount)

    def test_make_full_payment_with_kwargs(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        order.make_full_payment(title='test payment title')

        created_payment = BasePayment.objects.filter(order=order, amount=order.total_amount, title='test payment title').first()
        self.assertTrue(created_payment is not None)
        self.assertEqual(created_payment.order, order)
        self.assertEqual(created_payment.amount, order.total_amount)
        self.assertEqual(created_payment.title, 'test payment title')

    def test_payment_amount_without_payments(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payments = order.payments.filter(status=BasePayment.PaymentStatus.SUCCEEDED)
        payment_amount = order.payment_amount()

        self.assertEqual(payment_amount, 0)
        self.assertEqual(payments.count(), 0)

    def test_payment_amount_with_payments(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=50, status=BasePayment.PaymentStatus.SUCCEEDED)

        payments = order.payments.filter(status=BasePayment.PaymentStatus.SUCCEEDED)
        payment_amount = order.payment_amount()

        self.assertEqual(payment_amount, 50)
        self.assertEqual(payments.count(), 1)
        self.assertTrue(payment in payments)

    def test_payment_amount_without_succeeded_payments(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=50, status=BasePayment.PaymentStatus.PENDING)

        payments = order.payments.filter(status=BasePayment.PaymentStatus.SUCCEEDED)
        payment_amount = order.payment_amount()

        self.assertEqual(payment_amount, 0)
        self.assertEqual(payments.count(), 0)
        self.assertTrue(payment not in payments)

    def test_items_amount_without_items(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        items_amount = order.items_amount()

        self.assertEqual(items_amount, 0)

    def test_items_amount_with_items(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        BaseOrderItem.objects.create(order=order, amount=50, quantity=2)

        items_amount = order.items_amount()

        self.assertEqual(items_amount, 100)

    def test_pay_with_partial_payment(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=50)

        order.pay(payment)

        self.assertEqual(order.status, BaseOrder.OrderStatus.PAYED_PARTIAL)

    def test_pay_with_full_payment(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100)
        payment = BasePayment.objects.create(title='test', order=order, amount=100)

        order.pay(payment)

        self.assertEqual(order.status, BaseOrder.OrderStatus.PAYED_FULL)

    def test_refunded_partial(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100, payed_amount=100, status=BaseOrder.OrderStatus.PAYED_FULL)
        payment = BasePayment.objects.create(title='test', order=order, amount=50)

        order.refunded(payment)

        self.assertEqual(order.status, BaseOrder.OrderStatus.PAYED_PARTIAL)

    def test_refunded_full(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100, payed_amount=100, status=BaseOrder.OrderStatus.PAYED_FULL)
        payment = BasePayment.objects.create(title='test', order=order, amount=100)

        order.refunded(payment)

        self.assertEqual(order.status, BaseOrder.OrderStatus.REFUNDED)

    def test_split_order_with_created_order(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100, status=BaseOrder.OrderStatus.CREATED)
        order_total_amount = order.total_amount
        order_item_for_split = BaseOrderItem.objects.create(order=order, amount=50, quantity=1)
        BaseOrderItem.objects.create(order=order, amount=50, quantity=1)

        splitted_order = BaseOrder.split_order(number='test splitted_order', item=order_item_for_split)
        order.refresh_from_db()

        self.assertTrue(splitted_order is not None)
        self.assertEqual(splitted_order.total_amount, order_item_for_split.full_amount())
        self.assertEqual(order.total_amount, order_total_amount - order_item_for_split.full_amount())

    def test_split_order_with_payed_order(self):
        order = BaseOrder.objects.create(number='test', user=self.user, total_amount=100, status=BaseOrder.OrderStatus.PAYED_FULL)
        order_item_for_split = BaseOrderItem.objects.create(order=order, amount=50, quantity=1)

        splited_order = BaseOrder.split_order(number='test splitted_order', item=order_item_for_split)

        self.assertTrue(splited_order is None)
