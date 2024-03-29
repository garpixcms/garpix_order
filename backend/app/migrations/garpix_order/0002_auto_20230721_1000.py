# Generated by Django 3.1 on 2023-07-21 07:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('garpix_order', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Recurring',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_at', models.DateTimeField(verbose_name='Дата начала платежей')),
                ('end_at', models.DateTimeField(verbose_name='Дата окончания платежей')),
                ('last_payment_at', models.DateTimeField(verbose_name='Дата последнего платежа')),
                ('is_active', models.BooleanField(default=True, verbose_name='Включено')),
                ('frequency', models.CharField(choices=[('MONTH', 'Ежемесячный'), ('YEAR', 'Ежегодный')], default='MONTH', max_length=5, verbose_name='Частота платежей')),
            ],
            options={
                'verbose_name': 'Рекуррент',
                'verbose_name_plural': 'Рекурренты',
            },
        ),
        migrations.AddField(
            model_name='baseorder',
            name='recurring',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='garpix_order.recurring', verbose_name='Рекуррент'),
        ),
    ]
