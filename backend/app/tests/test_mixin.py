from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class TestMixin(TestCase):
    @classmethod
    def _create_user(cls):
        cls.user = User.objects.create_user('test', 'test@test.ru', 'test_password')
