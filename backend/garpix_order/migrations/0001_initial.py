# Generated by Django 3.1 on 2022-03-05 10:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_fsm
import garpix_order.models.payments.cloudpayments


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', django_fsm.FSMField(choices=[('created', 'CREATED'), ('payed_full', 'PAYED_FULL'), ('payed_partial', 'PAYED_PARTIAL'), ('cancel', 'CANCELED'), ('refunded', 'REFUNDED')], default='created', max_length=50)),
                ('number', models.CharField(max_length=255, verbose_name='Номер заказа')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Полная стоимость')),
                ('payed_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Оплачено')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата изменения')),
                ('polymorphic_ctype', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='polymorphic_garpix_order.baseorder_set+', to='contenttypes.contenttype')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Базовый ордер',
                'verbose_name_plural': 'Базовые ордера',
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='BasePayment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='', max_length=255, verbose_name='Название')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Сумма')),
                ('status', django_fsm.FSMField(choices=[('created', 'CREATED'), ('pending', 'PENDING'), ('waiting_for_capture', 'WAITING FOR CAPTURE'), ('succeeded', 'SUCCEEDED'), ('cancel', 'CANCELED'), ('failed', 'FAILED'), ('refunded', 'REFUNDED'), ('timeout', 'TIMEOUT'), ('closed', 'CLOSED')], default='created', max_length=50)),
                ('client_data', models.JSONField(blank=True, null=True, verbose_name='Client payment process data')),
                ('provider_data', models.JSONField(blank=True, null=True, verbose_name='Provider payment process data')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата изменения')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='garpix_order.baseorder', verbose_name='Заказ')),
                ('polymorphic_ctype', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='polymorphic_garpix_order.basepayment_set+', to='contenttypes.contenttype')),
            ],
            options={
                'verbose_name': 'Платеж',
                'verbose_name_plural': 'Платежи',
            },
        ),
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cloudpayments_public_id', models.CharField(max_length=200, verbose_name='publicId из личного кабинета CP')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CashPayment',
            fields=[
                ('basepayment_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='garpix_order.basepayment')),
            ],
            options={
                'verbose_name': 'Платеж наличкой',
                'verbose_name_plural': 'Платежи наличкой',
            },
            bases=('garpix_order.basepayment',),
        ),
        migrations.CreateModel(
            name='CloudPayment',
            fields=[
                ('basepayment_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='garpix_order.basepayment')),
                ('payment_uuid', models.CharField(default=garpix_order.models.payments.cloudpayments.generate_uuid, max_length=64, verbose_name='UUID')),
                ('order_number', models.CharField(max_length=200, verbose_name='Номер заказа')),
                ('transaction_id', models.CharField(blank=True, default='', max_length=200, verbose_name='Номер транзакции')),
                ('is_test', models.BooleanField(default=False, verbose_name='Тестовый платеж')),
            ],
            options={
                'verbose_name': 'Платеж Cloudpayment',
                'verbose_name_plural': 'Платежи Cloudpayment',
            },
            bases=('garpix_order.basepayment',),
        ),
        migrations.CreateModel(
            name='BaseOrderItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Цена')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Количество')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='garpix_order.baseorder', verbose_name='Заказ')),
                ('polymorphic_ctype', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='polymorphic_garpix_order.baseorderitem_set+', to='contenttypes.contenttype')),
            ],
            options={
                'verbose_name': 'Продукт заказа',
                'verbose_name_plural': 'Продукты заказа',
            },
        ),
    ]
