from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.db import transaction
from .models import User, Role, Student, Teacher, Course, Enrollment, Assignment, Quiz, Discussion, Grades, LiveSession, CourseCategory, SystemLog, Certificate
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from .decorators import admin_only
from django.contrib.auth import logout
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch, Avg, Count
from django.core.cache import cache
from django.db import connection
from django.conf import settings
import logging
from django.db.models.functions import TruncDate

User = get_user_model()

logger = logging.getLogger(__name__)

def get_started(request):
    return render(request, 'get_started.html')

def register(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        user_type = request.POST.get('user_type')
        name = request.POST.get('name')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('LearnPeak:register')

        try:
            with transaction.atomic():
                # Check if user already exists
                if User.objects.filter(email=email).exists():
                    messages.error(request, 'Email already registered.')
                    return redirect('LearnPeak:register')

                # Get or create the appropriate role
                role, _ = Role.objects.get_or_create(
                    role_name=user_type,
                    defaults={'created_at': timezone.now()}
                )

                # Create new user
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    name=name,
                    role=role
                )

                # Create the role-specific profile
                if user_type == 'student':
                    Student.objects.create(
                        user=user,
                        course_of_study=''
                    )
                elif user_type == 'teacher':
                    Teacher.objects.create(
                        user=user,
                        department=''  # Empty string for department
                    )

                messages.success(request, 'Registration successful! Please login.')
                return redirect('LearnPeak:login')
            
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return redirect('LearnPeak:register')
    
    return render(request, 'register.html')

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            auth_login(request, user)
            # Check user role and redirect accordingly
            if user.role.role_name == 'student':
                return redirect('LearnPeak:student_dashboard')
            elif user.role.role_name == 'teacher':
                return redirect('LearnPeak:teacher_dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
            
    return render(request, 'login.html')

@cache_page(60 * 15)  # Cache for 15 minutes
def student_dashboard(request):
    try:
        # Get student
        student = request.user.student
        
        # Try to get data from cache
        cache_key = f'student_dashboard_{student.id}'
        dashboard_data = cache.get(cache_key)
        
        if not dashboard_data:
            # Use select_for_update to prevent race conditions
            with connection.cursor() as cursor:
                # Get enrolled courses with optimized query
                enrolled_courses = (Course.objects
                    .filter(enrollment__student=student)
                    .select_related('teacher')
                    .prefetch_related(
                        Prefetch('assignment_set', 
                                queryset=Assignment.objects.select_related('course')),
                        'lesson_set'
                    )
                    .annotate(assignment_count=Count('assignment'))
                    .only('id', 'title', 'description', 'teacher__user__name')
                )

                # Get pending assignments efficiently
                pending_assignments = (Assignment.objects
                    .filter(
                        course__enrollment__student=student,
                        deadline__gte=timezone.now()
                    )
                    .select_related('course')
                    .only('id', 'title', 'deadline', 'course__title')
                    .order_by('deadline')[:5]
                )

                # Get completed courses with minimal fields
                completed_courses = (Course.objects
                    .filter(
                        enrollment__student=student,
                        enrollment__status='completed'
                    )
                    .distinct()
                    .only('id', 'title')
                )

                # Get average grade efficiently
                avg_grade = (Grades.objects
                    .filter(student=student)
                    .aggregate(avg=Avg('grade'))
                )['avg']

                dashboard_data = {
                    'enrolled_courses': enrolled_courses,
                    'pending_assignments': pending_assignments,
                    'completed_courses': completed_courses,
                    'avg_grade': round(avg_grade, 1) if avg_grade else None,
                }
                
                # Cache with reasonable timeout
                cache.set(cache_key, dashboard_data, 60 * 15)  # 15 minutes

        # Add performance monitoring
        if settings.DEBUG:
            query_count = len(connection.queries)
            logger.debug(f"Dashboard queries: {query_count}")

        return render(request, 'student_dashboard.html', dashboard_data)

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return render(request, 'error.html', {'message': 'Unable to load dashboard'})

@login_required
def teacher_dashboard(request):
    # Get the teacher profile
    teacher = request.user.teacher

    # Get courses created by this teacher
    courses = Course.objects.filter(teacher=teacher)

    # Get all assignments from teacher's courses
    assignments = Assignment.objects.filter(course__in=courses).order_by('-created_at')

    # Get all quizzes from teacher's courses
    quizzes = Quiz.objects.filter(course__in=courses).order_by('-created_at')

    # Get upcoming live sessions
    live_sessions = LiveSession.objects.filter(
        course__in=courses,
        schedule__gte=timezone.now()
    ).order_by('schedule')

    # Get recent discussions in teacher's courses
    discussions = Discussion.objects.filter(
        course__in=courses
    ).order_by('-created_at')[:5]

    # Get recent grades given
    recent_grades = Grades.objects.filter(
        course__in=courses
    ).order_by('-updated_at')[:5]

    # Get total number of enrolled students across all courses
    total_students = Enrollment.objects.filter(course__in=courses).count()

    context = {
        'courses': courses,
        'assignments': assignments,
        'quizzes': quizzes,
        'live_sessions': live_sessions,
        'discussions': discussions,
        'recent_grades': recent_grades,
        'total_students': total_students,
    }
    
    return render(request, 'teacher_dashboard.html', context)

def logout(request):
    auth_logout(request)
    return redirect('LearnPeak:get_started')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            # Try to get the user by email
            user = authenticate(username=email, password=password)
            
            if user is not None:
                auth_login(request, user)
                
                # Redirect based on user type
                if user.is_superuser:
                    return redirect('LearnPeak:admin_dashboard')
                elif hasattr(user, 'teacher'):
                    return redirect('LearnPeak:teacher_dashboard')
                elif hasattr(user, 'student'):
                    return redirect('LearnPeak:student_dashboard')
                else:
                    messages.error(request, 'Invalid user type')
                    return redirect('LearnPeak:login')
            else:
                messages.error(request, 'Invalid email or password')
                return redirect('LearnPeak:login')
                
        except Exception as e:
            messages.error(request, 'An error occurred during login')
            return redirect('LearnPeak:login')
            
    return render(request, 'login.html')

def register_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        user_type = request.POST.get('user_type')

        # Validate passwords match
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'register.html')

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'register.html')

        try:
            # Create the user
            user = User.objects.create_user(
                username=email,  # Using email as username
                email=email,
                password=password
            )
            user.name = name  # Assuming your User model has a name field
            user.save()

            # Create Student or Teacher profile based on user_type
            if user_type == 'student':
                Student.objects.create(user=user)
            elif user_type == 'teacher':
                Teacher.objects.create(user=user)

            messages.success(request, 'Registration successful! Please login.')
            return redirect('LearnPeak:login')

        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, 'register.html')

    return render(request, 'register.html')

# You can remove or keep the admin_dashboard view function
@login_required
@admin_only
def admin_dashboard(request):
    # Get the date 7 days ago
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    context = {
        'total_users': User.objects.count(),
        'teacher_count': Teacher.objects.count(),
        'student_count': Student.objects.count(),
        'course_count': Course.objects.count(),
        'course_categories': CourseCategory.objects.count(),
        'recent_activities': SystemLog.objects.count(),
        'recent_users': User.objects.select_related('teacher', 'student').order_by('-date_joined')[:5],
        'system_logs': SystemLog.objects.order_by('-timestamp')[:5],
        'categories': CourseCategory.objects.all(),
        'active_users_today': User.objects.filter(last_login__date=timezone.now().date()).count(),
        'weekly_enrollments': Enrollment.objects.filter(
            enrollment_date__gte=seven_days_ago  # Changed from created_at to enrollment_date
        ).annotate(
            date=TruncDate('enrollment_date')  # Changed from created_at to enrollment_date
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date'),
        'recent_enrollments': Enrollment.objects.select_related(
            'student__user', 
            'course'
        ).order_by('-enrollment_date')[:5],  # Changed from created_at to enrollment_date
    }
    
    return render(request, 'admin_dashboard.html', context)

def delete_user(request, user_id):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to delete users.')
        return redirect('LearnPeak:admin_dashboard')
        
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            email = user.email
            user.delete()
            messages.success(request, f'User {email} has been deleted successfully.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
    return redirect('LearnPeak:admin_dashboard')

def logout_view(request):
    logout(request)
    return redirect('LearnPeak:login')