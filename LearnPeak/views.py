from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, LoginForm
from .models import User, Role, Student, Teacher
from django.db import transaction

# Create your views here.
def index(request):
    return render(request, 'index.html')

def home(request):
    return render(request, 'index.html')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Get or create role
                    role, _ = Role.objects.get_or_create(
                        role_name=form.cleaned_data['user_type']
                    )
                    
                    # Create user
                    user = User.objects.create_user(
                        email=form.cleaned_data['email'],
                        name=form.cleaned_data['name'],
                        password=form.cleaned_data['password']
                    )
                    user.role = role
                    user.save()

                    # Create profile based on role
                    if form.cleaned_data['user_type'] == 'student':
                        Student.objects.create(
                            user=user,
                            course_of_study='Not specified'  # Default value
                        )
                    elif form.cleaned_data['user_type'] == 'teacher':
                        Teacher.objects.create(
                            user=user,
                            department='Not specified'  # Default value
                        )

                messages.success(request, 'Registration successful! Please login.')
                return redirect('LearnPeak:login')
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            try:
                # Get user by email
                user = User.objects.get(email=email)
                
                # Check password
                if user.check_password(password):
                    login(request, user)
                    messages.success(request, 'Login successful!')
                    
                    # Redirect based on role
                    if hasattr(user, 'student'):
                        return redirect('LearnPeak:student_dashboard')
                    elif hasattr(user, 'teacher'):
                        return redirect('LearnPeak:teacher_dashboard')
                    else:
                        return redirect('LearnPeak:dashboard')
                else:
                    messages.error(request, 'Invalid password.')
            except User.DoesNotExist:
                messages.error(request, 'No account found with this email.')
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('LearnPeak:login')

@login_required
def student_dashboard(request):
    if not hasattr(request.user, 'student'):
        return redirect('LearnPeak:dashboard')
    context = {
        'user': request.user,
        'enrollments': request.user.student.enrollment_set.all(),
        'grades': request.user.student.grades_set.all(),
    }
    return render(request, 'student_dashboard.html', context)

@login_required
def teacher_dashboard(request):
    if not hasattr(request.user, 'teacher'):
        return redirect('LearnPeak:dashboard')
    context = {
        'user': request.user,
        'courses': request.user.teacher.course_set.all(),
    }
    return render(request, 'teacher_dashboard.html', context)

@login_required
def dashboard(request):
    if hasattr(request.user, 'student'):
        return redirect('LearnPeak:student_dashboard')
    elif hasattr(request.user, 'teacher'):
        return redirect('LearnPeak:teacher_dashboard')
    return redirect('LearnPeak:home')