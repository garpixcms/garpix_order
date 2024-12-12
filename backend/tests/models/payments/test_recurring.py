import datetime
from unittest.mock import patch
from django.utils import timezone
from app.tests import TestMixin
from garpix_order.models.payments.recurring import Recurring

class RecurringTestCase(TestMixin):

    def setUp(self):
        self.recurring_monthly = Recurring(
            start_at=timezone.datetime(2014, 1, 31),
            end_at=timezone.datetime(3014, 1, 31),
            frequency=Recurring.RecurringFrequency.MONTH,
            payment_system=Recurring.RecurringPaymentSystem.ROBOKASSA
        )

        self.recurring_yearly = Recurring(
            start_at=timezone.datetime(2014, 1, 31),
            end_at=timezone.datetime(3014, 1, 31),
            frequency=Recurring.RecurringFrequency.YEAR,
            payment_system=Recurring.RecurringPaymentSystem.ROBOKASSA
        )

    @patch.object(timezone, 'now', return_value=timezone.datetime(2024, 1, 31))
    def test_get_next_payment_date_monthly_isleap(self, mock_now):
        next_payment_date = self.recurring_monthly.get_next_payment_date()

        self.assertEqual(next_payment_date, datetime.date(2024, 2, 29))
        mock_now.assert_called_once()

    @patch.object(timezone, 'now', return_value=timezone.datetime(2025, 1, 31))
    def test_get_next_payment_date_monthly_not_isleap(self, mock_now):
        next_payment_date = self.recurring_monthly.get_next_payment_date()

        self.assertEqual(next_payment_date, datetime.date(2025, 2, 28))
        mock_now.assert_called_once()

    @patch.object(timezone, 'now', return_value=timezone.datetime(2024, 12, 31))
    def test_get_next_payment_date_monthly_for_next_year(self, mock_now):
        next_payment_date = self.recurring_monthly.get_next_payment_date()

        self.assertEqual(next_payment_date, datetime.date(2025, 1, 31))
        mock_now.assert_called_once()

    @patch.object(timezone, 'now', return_value=timezone.datetime(2024, 2, 29))
    def test_get_next_payment_date_yearly_isleap(self, mock_now):
        next_payment_date = self.recurring_yearly.get_next_payment_date()

        self.assertEqual(next_payment_date, datetime.date(2025, 2, 28))
        mock_now.assert_called_once()

    @patch.object(timezone, 'now', return_value=timezone.datetime(2025, 2, 28))
    def test_get_next_payment_date_yearly_not_isleap(self, mock_now):
        next_payment_date = self.recurring_yearly.get_next_payment_date()

        self.assertEqual(next_payment_date, datetime.date(2026, 2, 28))
        mock_now.assert_called_once()
