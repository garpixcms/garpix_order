from garpixcms.settings import *  # noqa

INSTALLED_APPS += [
    'example',
    'fsm_admin',
    'garpix_order',
]

MIGRATION_MODULES.update({  # noqa:F405
    'fcm_django': 'app.migrations.fcm_django',
    'garpix_order': 'app.migrations.garpix_order'
})

ROBOKASSA = {
    'LOGIN': str(os.getenv('ROBOKASSA_LOGIN')),
    'PASSWORD_1': str(os.getenv('ROBOKASSA_PASSWORD_1')),
    'PASSWORD_2': str(os.getenv('ROBOKASSA_PASSWORD_2')),
    'IS_TEST': str(os.getenv('ROBOKASSA_IS_TEST', 0)),
    'ALGORITHM': 'md5'
}

SBER = {
    'api_url': env('SBER_API_URL', ''),
    'token': env('SBER_TOKEN', ''),
    'cryptographic_key': env('SBER_CRYPTOGRAPHIC_KEY', ''),
    'cert_path': '',
}

SBER_PAYMENT_MODEL = "garpix_order.models.payments.sber.SberPayment"
