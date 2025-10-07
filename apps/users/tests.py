from rest_framework.test import APITestCase
from django.urls import reverse_lazy

from apps.users.models import User


class UserTest(APITestCase):

    def setUp(self):
        self.url_register = reverse_lazy('register')
        self.url_login = reverse_lazy('login')

        self.user_data = {
            "username": "testuser",
            "email": "testuser@gmail.com",
            "password": "testpassword123",
            "password_confirmation": "testpassword123",
        }

    def format_datetime(self, dt):
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    def test_register(self):
        response = self.client.post(self.url_register, data=self.user_data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('token', response.json())
        self.assertTrue(User.objects.filter(email=self.user_data['email']).exists())

    def test_login(self):
        self.user_data.pop('password_confirmation')
        User.objects.create_user(**self.user_data)

        user_login_data = {
            "email": self.user_data['email'],
            "password": self.user_data['password']
        }

        response = self.client.post(self.url_login, data=user_login_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())
        self.assertIn('refresh', response.json())
        self.assertIn('user', response.json())