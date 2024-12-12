import decimal
import hashlib
from datetime import datetime
from urllib import parse

import requests
from django.conf import settings

from garpix_order.models.payments.recurring import Recurring


class RobokassaService:
    payment_url = 'https://auth.robokassa.ru/Merchant/Index.aspx'
    recurring_payment_url = 'https://auth.robokassa.ru/Merchant/Recurring'
    login = settings.ROBOKASSA['LOGIN']
    password_1 = settings.ROBOKASSA['PASSWORD_1']
    password_2 = settings.ROBOKASSA['PASSWORD_2']
    is_test = settings.ROBOKASSA['IS_TEST']
    algorithm = settings.ROBOKASSA['ALGORITHM']

    @classmethod
    def get_amount_with_decimals(cls, amount: decimal) -> str:
        amount = str(amount)
        if '.' not in amount:
            amount = '{amount}.00'.format(amount=amount)
        amount_args = amount.split('.')
        while len(amount_args[1]) < 2:
            amount_args[1] += '0'
        amount = '.'.join(amount_args)
        return amount

    @classmethod
    def calculate_signature(cls, *args) -> str:
        """Create signature (MD5 - default).
        """
        return getattr(hashlib, cls.algorithm.lower(), 'md5')(':'.join(str(arg) for arg in args).encode()).hexdigest()

    @classmethod
    def generate_payment_link(cls, payment) -> str:
        order_cost = cls.get_amount_with_decimals(payment.amount)
        order_number = str(payment.id)
        signature = cls.calculate_signature(cls.login, order_cost, order_number, cls.password_1)

        data = {
            'MerchantLogin': cls.login,
            'OutSum': order_cost,
            'InvId': order_number,
            'SignatureValue': signature,
            'IsTest': cls.is_test
        }
        return f'{cls.payment_url}?{parse.urlencode(data)}'

    @classmethod
    def check_success_payment(cls, payment, data: dict, auto=False) -> (bool, str):
        if not auto:
            signature = cls.calculate_signature(data['OutSum'], payment.id, cls.password_2)
            if signature.lower() == data['SignatureValue'].lower():
                return True, ''
            return False, 'Invalid signature'
        prev_payment = payment.order.payments.exclude(id=payment.id).order_by('-id').first()
        return cls.send_recurring_request(payment, prev_payment)

    @classmethod
    def send_recurring_request(cls, payment, prev_payment) -> (bool, str):
        data = {
            'MerchantLogin': cls.login,
            'InvoiceID': payment.id,
            'PreviousInvoiceID': prev_payment.id,
            'SignatureValue': cls.calculate_signature(cls.login, payment.total_amount, payment.id, cls.password_1),
            'OutSum': payment.amount,
            'IsTest': cls.is_test
        }
        res = requests.post(cls.recurring_payment_url, data=data)
        if f"OK{payment.id}" != res.text:
            return False, res.text
        return True, res.text

    @classmethod
    def create_recurring_payments(cls):
        from garpix_order.models import BaseOrder, RobokassaPayment
        recurring_objs = Recurring.active_objects.filter(payment_system=Recurring.RecurringPaymentSystem.ROBOKASSA,
                                                         end_at__gt=datetime.now())
        orders_to_pay = BaseOrder.objects.filter(recurring__in=recurring_objs, next_payment_date__date=datetime.now().date())

        for obj in orders_to_pay:
            payment = RobokassaPayment.objects.create(order=obj, amount=obj.total_amount, payment_type=RobokassaPayment.PaymentType.AUTO)
            payment.pay(data={}, auto=True)


robokassa_service = RobokassaService()
