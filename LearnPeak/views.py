from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import UserRegistrationForm, LoginForm, CourseForm, LessonForm, MaterialForm, QuizForm, AssignmentForm, GradeSubmissionForm, LiveSessionForm
from .models import User, Role, Student, Teacher, Course, Enrollment, Discussion, Lesson, Material, Quiz, Submission, LiveSession
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect

# Create your views here.
def index(request):
    return render(request, 'index.html')

def home(request):
    return render(request, 'index.html')

@csrf_protect
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create corresponding role-based profile
            if user.role.role_name.lower() == 'student':
                Student.objects.create(
                    user=user,
                    course_of_study='Not specified'  # Default value
                )
            elif user.role.role_name.lower() == 'teacher':
                Teacher.objects.create(
                    user=user,
                    department='Not specified'  # Default value
                )
            
            messages.success(request, 'Registration successful. Please login.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

@csrf_protect
def user_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'role') and request.user.role:
            if request.user.role.role_name == 'teacher':
                return redirect('/teacher/dashboard/')
            elif request.user.role.role_name == 'student':
                return redirect('/student/dashboard/')
        return redirect('/dashboard/')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            if hasattr(user, 'role') and user.role:
                if user.role.role_name == 'teacher':
                    return redirect('/teacher/dashboard/')
                elif user.role.role_name == 'student':
                    return redirect('/student/dashboard/')
            else:
                messages.error(request, 'User role not assigned. Please contact administrator.')
                return redirect('/login/')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'login.html')

@csrf_protect
def user_logout(request):
    logout(request)
    return redirect('/login/')

def is_teacher(user):
    return user.is_authenticated and user.role == 'teacher'

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='login')
def teacher_dashboard(request):
    if not is_teacher(request.user):
        messages.error(request, 'You do not have permission to access the teacher dashboard.')
        return redirect('home')
    
    courses = Course.objects.filter(teacher=request.user)
    return render(request, 'teacherdashboard.html', {
        'courses': courses
    })

# Add student dashboard view
def is_student(user):
    return user.is_authenticated and user.role == 'student'

@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
def student_dashboard(request):
    if not is_student(request.user):
        messages.error(request, 'You do not have permission to access the student dashboard.')
        return redirect('home')
    
    # Get student's enrolled courses
    enrolled_courses = Course.objects.filter(students=request.user)
    return render(request, 'studentdashboard.html', {
        'courses': enrolled_courses
    })

@login_required
def dashboard(request):
    if hasattr(request.user, 'student'):
        return redirect('LearnPeak:student_dashboard')
    elif hasattr(request.user, 'teacher'):
        return redirect('LearnPeak:teacher_dashboard')
    return redirect('LearnPeak:home')

@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    Enrollment.objects.create(student=request.user.student, course=course)
    messages.success(request, 'Enrolled in course successfully.')
    return redirect('LearnPeak:student_dashboard')

@login_required
def course_discussions(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    discussions = Discussion.objects.filter(course=course)
    if request.method == 'POST':
        content = request.POST.get('content')
        Discussion.objects.create(course=course, user=request.user, content=content)
        messages.success(request, 'Discussion posted successfully.')
        return redirect('LearnPeak:course_discussions', course_id=course.id)
    return render(request, 'course_discussions.html', {'course': course, 'discussions': discussions})

@login_required
@user_passes_test(is_teacher)
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.save()
            messages.success(request, 'Course created successfully!')
            return redirect('course_detail', course.id)
    else:
        form = CourseForm()
    return render(request, 'courses/teacher/course_form.html', {'form': form})

@login_required
@user_passes_test(is_teacher)
def lesson_create(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.save()
            return redirect('course_detail', course.id)
    else:
        form = LessonForm()
    return render(request, 'courses/teacher/lesson_form.html', {
        'form': form,
        'course': course
    })

@login_required
@user_passes_test(is_teacher)
def material_upload(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, course__teacher=request.user)
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.lesson = lesson
            material.save()
            return JsonResponse({'success': True})
    else:
        form = MaterialForm()
    return render(request, 'courses/teacher/material_form.html', {
        'form': form,
        'lesson': lesson
    })

@login_required
@user_passes_test(is_teacher)
def quiz_create(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.course = course
            quiz.save()
            return redirect('quiz_add_questions', quiz.id)
    else:
        form = QuizForm()
    return render(request, 'courses/teacher/quiz_form.html', {
        'form': form,
        'course': course
    })

@login_required
@user_passes_test(is_teacher)
def assignment_create(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.course = course
            assignment.save()
            return redirect('course_detail', course.id)
    else:
        form = AssignmentForm()
    return render(request, 'courses/teacher/assignment_form.html', {
        'form': form,
        'course': course
    })

@login_required
@user_passes_test(is_teacher)
def grade_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id, 
                                 assignment__course__teacher=request.user)
    if request.method == 'POST':
        form = GradeSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grade submitted successfully!')
            return redirect('assignment_submissions', submission.assignment.id)
    else:
        form = GradeSubmissionForm(instance=submission)
    return render(request, 'courses/teacher/grade_submission.html', {
        'form': form,
        'submission': submission
    })

@login_required
@user_passes_test(is_teacher)
def live_session_create(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        form = LiveSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.course = course
            session.save()
            return redirect('course_detail', course.id)
    else:
        form = LiveSessionForm()
    return render(request, 'courses/teacher/live_session_form.html', {
        'form': form,
        'course': course
    })