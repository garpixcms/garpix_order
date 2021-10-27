# Generated by Django 3.1 on 2021-10-17 19:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('example', '0001_initial'),
        ('garpix_order', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('baseorder_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='garpix_order.baseorder')),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
            bases=('garpix_order.baseorder',),
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('baseorderitem_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='garpix_order.baseorderitem')),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
            bases=('garpix_order.baseorderitem',),
        ),
    ]
