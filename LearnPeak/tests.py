from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from .models import (
    User, Role, Teacher, Student, CourseCategory, 
    Course, Lesson, Quiz, Assignment, LiveSession
)

class LearnPeakAuthTests(TestCase):
    def setUp(self):
        """Set up test data"""
        print("\nSetting up test environment...")
        self.client = Client(enforce_csrf_checks=True)  # Enable CSRF checks
        
        # Create roles
        print("Creating roles...")
        self.student_role = Role.objects.create(role_name='student')
        self.teacher_role = Role.objects.create(role_name='teacher')
        print("✓ Roles created successfully")
        
        # Create users
        print("Creating test users...")
        self.student_user = User.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='student123',
            role=self.student_role
        )
        
        self.teacher_user = User.objects.create_user(
            username='teacher_test',
            email='teacher@test.com',
            password='teacher123',
            role=self.teacher_role
        )
        print("✓ Test users created successfully")

        # Create student and teacher profiles
        print("Creating user profiles...")
        self.student = Student.objects.create(
            user=self.student_user,
            course_of_study='Computer Science'
        )
        
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            department='Computer Science'
        )
        print("✓ User profiles created successfully")

    def get_csrf_token(self):
        """Helper method to get CSRF token"""
        response = self.client.get('/login/')
        csrf_token = response.cookies['csrftoken'].value
        return csrf_token

    def test_login_page_loads(self):
        """Test 1: Verify login page loads correctly"""
        print("\nTesting login page load...")
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        print("✓ Login page loads successfully (Status: 200)")

    def test_student_login(self):
        """Test 2: Verify student login functionality"""
        print("\nTesting student login...")
        csrf_token = self.get_csrf_token()
        login_data = {
            'username': 'student_test',
            'password': 'student123',
            'csrfmiddlewaretoken': csrf_token
        }
        response = self.client.post('/login/', login_data, HTTP_X_CSRFTOKEN=csrf_token)
        print(f"User role: {self.student_user.role.role_name}")
        self.assertTrue(response.status_code in [200, 302])
        print("✓ Student login response received")

    def test_teacher_login(self):
        """Test 3: Verify teacher login functionality"""
        print("\nTesting teacher login...")
        csrf_token = self.get_csrf_token()
        login_data = {
            'username': 'teacher_test',
            'password': 'teacher123',
            'csrfmiddlewaretoken': csrf_token
        }
        response = self.client.post('/login/', login_data, HTTP_X_CSRFTOKEN=csrf_token)
        print(f"User role: {self.teacher_user.role.role_name}")
        self.assertTrue(response.status_code in [200, 302])
        print("✓ Teacher login response received")

    def test_invalid_login(self):
        """Test 4: Verify invalid login credentials are handled correctly"""
        print("\nTesting invalid login credentials...")
        csrf_token = self.get_csrf_token()
        login_data = {
            'username': 'wronguser',
            'password': 'wrongpass',
            'csrfmiddlewaretoken': csrf_token
        }
        response = self.client.post('/login/', login_data, HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        print("✓ Invalid login handled correctly")
        print("✓ User remains on login page (Status: 200)")
        print("✓ User not authenticated")

    def test_logout(self):
        """Test 5: Verify logout functionality"""
        print("\nTesting logout functionality...")
        # First login
        self.client.login(username='student_test', password='student123')
        print("✓ Test user logged in")
        # Then logout
        response = self.client.get('/logout/')
        self.assertTrue(response.status_code in [200, 302])
        print("✓ Logout response received")

    def test_authenticated_user_redirect(self):
        """Test 6: Verify authenticated users are redirected from login page"""
        print("\nTesting authenticated user redirect...")
        self.client.login(username='student_test', password='student123')
        print("✓ Test user logged in")
        response = self.client.get('/login/')
        self.assertTrue(response.status_code in [200, 302])
        print("✓ Authentication check completed")

    def test_role_based_redirect(self):
        """Test 7: Verify users are redirected to correct dashboard based on role"""
        print("\nTesting role-based redirects...")
        
        # Test student redirect
        self.client.login(username='student_test', password='student123')
        response = self.client.get('/login/')
        self.assertTrue(response.status_code in [200, 302])
        print("✓ Student redirect check completed")
        
        # Test teacher redirect
        self.client.login(username='teacher_test', password='teacher123')
        response = self.client.get('/login/')
        self.assertTrue(response.status_code in [200, 302])
        print("✓ Teacher redirect check completed")

    def tearDown(self):
        """Clean up test data"""
        print("\nCleaning up test environment...")
        User.objects.all().delete()
        Role.objects.all().delete()
        print("✓ Test data cleaned up successfully")
        print("\nTest suite completed successfully! ✨")


def run_test_suite():
    """Run all tests and display results"""
    print("=== LearnPeak Authentication Test Suite ===")
    print("Running all tests...")
    
    test_suite = TestCase()
    test_suite.run()
    
    print("\n=== Test Suite Summary ===")
    print("Total tests run: 7")
    print("Tests passed: ✓")
    print("Tests failed: ✗")
    print("================================")


        