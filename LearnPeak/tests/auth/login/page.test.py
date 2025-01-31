from django.test import TestCase
from django.urls import reverse

class LoginPageTest(TestCase):
    def test_login_page_loads(self):
        """Test login page loads correctly"""
        response = self.client.get(reverse('LearnPeak:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_form_submission(self):
        """Test login form submission"""
        response = self.client.post(reverse('LearnPeak:login'), {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login 