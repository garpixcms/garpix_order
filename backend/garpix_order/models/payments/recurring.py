import calendar
import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from garpix_utils.models import ActiveMixin


class Recurring(ActiveMixin, models.Model):
    class RecurringFrequency(models.TextChoices):
        """Частота регулярных платежей"""
        MONTH = 'MONTH', _('Ежемесячный')
        YEAR = 'YEAR', _('Ежегодный')

    class RecurringPaymentSystem(models.TextChoices):
        """Система оплаты"""
        ROBOKASSA = 'ROBOKASSA', _('Робокасса')

    start_at = models.DateTimeField(verbose_name=_('Дата начала платежей'))
    end_at = models.DateTimeField(verbose_name=_('Дата окончания платежей'))
    frequency = models.CharField(max_length=5, choices=RecurringFrequency.choices, default=RecurringFrequency.MONTH,
                                 verbose_name=_('Частота платежей'))
    payment_system = models.CharField(max_length=9, choices=RecurringPaymentSystem.choices,
                                      default=RecurringPaymentSystem.ROBOKASSA, verbose_name=_('Система оплаты'))

    class Meta:
        verbose_name = _('Рекуррент')
        verbose_name_plural = _('Рекурренты')

    def get_next_payment_date(self):
        today = timezone.now().date()
        if self.frequency == self.RecurringFrequency.MONTH:
            month = today.month + 1
            year = today.year

            if month > 12:
                month = 1
                year += 1

            day = min(today.day, calendar.monthrange(year, month)[1])
            return datetime.date(year, month, day)
        else:
            try:
                return today.replace(year=today.year + 1)
            except ValueError:
                return today.replace(year=today.year + 1, day=28)
