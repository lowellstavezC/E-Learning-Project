from django.test import TestCase, Client
from django.urls import reverse
from .models import User

class LearnPeakAuthTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.login_url = reverse('LearnPeak:login')
        self.register_url = reverse('LearnPeak:register')
        
        # Create a test user
        self.user = User.objects.create_user(
            name='Test User',
            email='test@example.com',
            password='testpass123'
        )
        # Set student status after creation
        self.user.user_type = 'student'
        self.user.save()

    def test_login_page_loads(self):
        """Test that login page loads correctly"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_register_page_loads(self):
        """Test that register page loads correctly"""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    def test_user_can_register(self):
        """Test user registration process"""
        data = {
            'name': 'New User',
            'email': 'new@example.com',
            'password': 'newpass123',
            'confirm_password': 'newpass123',
            'user_type': 'student'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)  # Should redirect after success
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

    def test_user_can_login(self):
        """Test user login process"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 302)  # Should redirect after success

    def test_invalid_login(self):
        """Test invalid login credentials"""
        data = {
            'email': 'wrong@example.com',
            'password': 'wrongpass'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)  # Should stay on login page

    def test_invalid_registration(self):
        """Test invalid registration data"""
        data = {
            'email': 'invalid-email',
            'password': 'pass',
            'confirm_password': 'different-pass',
            'user_type': 'invalid'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)  # Should stay on register page


        