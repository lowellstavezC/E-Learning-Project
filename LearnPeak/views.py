from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.db import transaction
from .models import User, Role, Student, Teacher, Course, Enrollment, Assignment, Quiz, Discussion, Grades, LiveSession, SystemLog, Certificate, Lesson, Notification, Question, Choice, QuizQuestion, QuizResult, Exam, AssignmentSubmission, ExamQuestion, ExamResult
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from .decorators import admin_only
from django.contrib.auth import logout
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch, Avg, Count
from django.core.cache import cache
from django.db import connection
from django.conf import settings
import logging
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator
from .forms import CustomUserForm, CourseForm, LessonForm, QuizForm, AssignmentForm, ExamForm, ExamQuestionForm
from django.views.decorators.csrf import csrf_protect
import json
from django.http import JsonResponse
import pandas as pd
from django.db.models import Q
from django.apps import apps
import re
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Avg

CustomUser = get_user_model()

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

@login_required
def student_dashboard(request):
    # Check user role and redirect accordingly
    if request.user.is_superuser:
        return redirect('LearnPeak:admin_dashboard')
    elif hasattr(request.user, 'teacher'):
        return redirect('LearnPeak:teacher_dashboard')
    elif not hasattr(request.user, 'student'):
        return redirect('LearnPeak:get_started')
    
    # Get student data
    student = request.user.student
    enrolled_courses = Course.objects.filter(enrollment__student=student)
    pending_assignments = Assignment.objects.filter(
        course__in=enrolled_courses,
        deadline__gt=timezone.now()
    ).order_by('deadline')
    
    context = {
        'enrolled_courses': enrolled_courses,
        'pending_assignments': pending_assignments,
        'student': student,
    }
    
    return render(request, 'student/student_dashboard.html', context)

@login_required
def teacher_dashboard(request):
    # Check user role and redirect accordingly
    if request.user.is_superuser:
        return redirect('LearnPeak:admin_dashboard')
    elif hasattr(request.user, 'student'):
        return redirect('LearnPeak:student_dashboard')
    elif not hasattr(request.user, 'teacher'):
        return redirect('LearnPeak:get_started')
    
    # Get the teacher instance
    teacher = request.user.teacher
    
    # Get courses where the teacher instance is the teacher
    courses = Course.objects.filter(teacher=teacher)
    
    # Get assignments for these courses
    pending_assignments = Assignment.objects.filter(
        course__in=courses,
        deadline__gt=timezone.now()
    ).order_by('deadline')
    
    # Get total students enrolled in teacher's courses
    total_students = Student.objects.filter(
        enrollment__course__in=courses
    ).distinct().count()
    
    context = {
        'teacher': teacher,
        'courses': courses,
        'pending_assignments': pending_assignments,
        'total_students': total_students,
    }
    
    return render(request, 'teacher/teacher_dashboard.html', context)

@csrf_protect
def logout_view(request):
    logout(request)
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

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    # Check user role and redirect accordingly
    if hasattr(request.user, 'teacher'):
        return redirect('LearnPeak:teacher_dashboard')
    elif hasattr(request.user, 'student'):
        return redirect('LearnPeak:student_dashboard')
    elif not request.user.is_superuser:
        return redirect('LearnPeak:get_started')
    
    # Admin dashboard logic here
    return render(request, 'admin/admin_dashboard.html')

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

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    users = User.objects.all().order_by('-date_joined')
    paginator = Paginator(users, 10)
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_users': users.count(),
    }
    
    return render(request, 'admin/user_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def create_user(request):
    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'User created successfully!')
            return redirect('LearnPeak:user_list')
    else:
        form = CustomUserForm()
    
    return render(request, 'admin/user_form.html', {'form': form, 'action': 'Create'})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = CustomUserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully!')
            return redirect('LearnPeak:user_list')
    else:
        form = CustomUserForm(instance=user)
    
    return render(request, 'admin/user_form.html', {'form': form, 'action': 'Edit'})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully!')
    return redirect('LearnPeak:user_list')

@login_required
def create_course(request):
    # Check if user is a teacher
    if not hasattr(request.user, 'teacher'):
        return redirect('LearnPeak:get_started')
    
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user.teacher
            course.save()
            
            # Create system log
            SystemLog.objects.create(
                admin=None,  # Since this is a teacher action
                action=f"Course '{course.title}' created by teacher {request.user.teacher}"
            )
            
            # Create notification for admin
            Notification.objects.create(
                user=User.objects.filter(role__role_name='admin').first(),
                message=f"New course '{course.title}' has been created by {request.user.teacher}",
                notification_type='course_creation',
                status='unread'
            )
            
            messages.success(request, 'Course created successfully!')
            return redirect('LearnPeak:manage_lessons', course_id=course.id)
    else:
        form = CourseForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'teacher/create_course.html', context)

@login_required
def manage_lessons(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Check if the logged-in user is the course teacher
    if course.teacher != request.user.teacher:
        return redirect('LearnPeak:teacher_dashboard')
    
    lessons = course.lessons.all().order_by('created_at')
    
    if request.method == 'POST':
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.save()
            messages.success(request, 'Lesson created successfully!')
            return redirect('LearnPeak:manage_lessons', course_id=course.id)
    else:
        form = LessonForm()
    
    context = {
        'course': course,
        'lessons': lessons,
        'form': form
    }
    
    return render(request, 'teacher/manage_lessons.html', context)

@login_required
def manage_quizzes(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Check if the logged-in user is the course teacher
    if course.teacher != request.user.teacher:
        return redirect('LearnPeak:teacher_dashboard')
    
    quizzes = Quiz.objects.filter(course=course).order_by('-created_at')
    
    context = {
        'course': course,
        'quizzes': quizzes,
    }
    
    return render(request, 'teacher/manage_quizzes.html', context)

@login_required
def manage_assignments(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Check if the logged-in user is the course teacher
    if course.teacher != request.user.teacher:
        return redirect('LearnPeak:teacher_dashboard')
    
    assignments = Assignment.objects.filter(course=course)
    
    context = {
        'course': course,
        'assignments': assignments,
    }
    
    return render(request, 'teacher/manage_assignments.html', context)

def is_teacher(user):
    return user.is_authenticated and hasattr(user, 'teacher')

@login_required
@user_passes_test(is_teacher)
def manage_exams(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    exams = Exam.objects.filter(course=course)
    
    context = {
        'course': course,
        'exams': exams,
    }
    return render(request, 'teacher/manage_exams.html', context)

@login_required
@user_passes_test(is_teacher)
def create_exam(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        try:
            # Create the exam
            exam = Exam.objects.create(
                course=course,
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                duration=request.POST.get('duration'),
                exam_type=request.POST.get('exam_type'),
                passing_grade=request.POST.get('passing_grade'),
            )

            if exam.exam_type == 'external':
                exam.external_link = request.POST.get('external_link')
                exam.save()
            else:
                # Process questions
                question_data = {}
                for key, value in request.POST.items():
                    if key.startswith('questions['):
                        # Parse the question index and field
                        parts = key.split('[')
                        idx = parts[1].split(']')[0]
                        field = parts[2].split(']')[0]
                        
                        if idx not in question_data:
                            question_data[idx] = {}
                        question_data[idx][field] = value

                # Create questions
                for idx, data in question_data.items():
                    if 'text' in data:  # Only create if we have question text
                        ExamQuestion.objects.create(
                            exam=exam,
                            text=data['text'],
                            option1=data.get('option1', ''),
                            option2=data.get('option2', ''),
                            option3=data.get('option3', ''),
                            option4=data.get('option4', ''),
                            correct_answer=int(data.get('correct_answer', 1))
                        )

            messages.success(request, 'Exam created successfully!')
            return redirect('LearnPeak:manage_exams', course_id=course.id)

        except Exception as e:
            messages.error(request, f'Error creating exam: {str(e)}')
            return render(request, 'teacher/create_exam.html', {'course': course})

    return render(request, 'teacher/create_exam.html', {'course': course})

@login_required
@user_passes_test(is_teacher)
def delete_exam(request, course_id, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, course_id=course_id)
    exam.delete()
    messages.success(request, 'Exam deleted successfully!')
    return redirect('LearnPeak:manage_exams', course_id=course_id)

@login_required
def create_lesson(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Check if the logged-in user is the course teacher
    if course.teacher != request.user.teacher:
        return redirect('LearnPeak:teacher_dashboard')
    
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.save()
            messages.success(request, 'Lesson created successfully!')
            return redirect('LearnPeak:manage_lessons', course_id=course.id)
    else:
        form = LessonForm()
    
    context = {
        'course': course,
        'form': form
    }
    
    return render(request, 'teacher/create_lesson.html', context)

@login_required
def delete_lesson(request, course_id, lesson_id):
    if request.method != 'POST':
        return redirect('LearnPeak:manage_lessons', course_id=course_id)
        
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    
    # Security check
    if course.teacher != request.user.teacher:
        messages.error(request, 'You do not have permission to delete this lesson.')
        return redirect('LearnPeak:teacher_dashboard')
    
    try:
        lesson_title = lesson.title
        lesson.delete()
        messages.success(request, f'Lesson "{lesson_title}" was deleted successfully.')
    except Exception as e:
        messages.error(request, 'Error deleting lesson.')
    
    return redirect('LearnPeak:manage_lessons', course_id=course_id)

@login_required
def edit_lesson(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    
    # Check if the logged-in user is the course teacher
    if course.teacher != request.user.teacher:
        return redirect('LearnPeak:teacher_dashboard')
    
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lesson updated successfully!')
            return redirect('LearnPeak:manage_lessons', course_id=course.id)
    else:
        form = LessonForm(instance=lesson)
    
    context = {
        'course': course,
        'lesson': lesson,
        'form': form
    }
    
    return render(request, 'teacher/edit_lesson.html', context)

@login_required
def create_quiz(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        quiz_type = request.POST.get('quiz_type')
        
        if quiz_type == 'manual':
            quiz = Quiz.objects.create(
                course=course,
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                duration=request.POST.get('duration'),
                quiz_type='manual'
            )
        else:
            quiz = Quiz.objects.create(
                course=course,
                title=request.POST.get('external_title'),
                external_link=request.POST.get('external_link'),
                quiz_type='external'
            )
        
        messages.success(request, 'Quiz created successfully!')
        return redirect('LearnPeak:manage_quizzes', course_id=course_id)
    
    context = {
        'course': course,  # Pass the course object to the template
        'course_id': course_id  # Pass the course_id explicitly
    }
    return render(request, 'teacher/create_quiz.html', context)

@login_required
def edit_quiz(request, course_id, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        try:
            print("POST data:", request.POST)  # Debug print
            
            # Update basic quiz information
            quiz.title = request.POST.get('title')
            quiz.description = request.POST.get('description')
            quiz.duration = request.POST.get('duration')
            quiz.quiz_type = request.POST.get('quiz_type')
            
            if quiz.quiz_type == 'external':
                quiz.external_link = request.POST.get('external_link')
                quiz.questions.all().delete()
            
            elif quiz.quiz_type == 'manual':
                # First delete existing questions
                quiz.questions.all().delete()
                
                # Create new questions
                question_data = {}
                for key, value in request.POST.items():
                    if key.startswith('questions['):
                        # Parse the question index and field
                        parts = key.split('[')
                        idx = parts[1].split(']')[0]
                        field = parts[2].split(']')[0]
                        
                        if idx not in question_data:
                            question_data[idx] = {}
                        question_data[idx][field] = value
                
                print("Question data:", question_data)  # Debug print
                
                # Create questions from the collected data
                for idx, data in question_data.items():
                    if 'text' in data:  # Only create if we have question text
                        Question.objects.create(
                            quiz=quiz,
                            text=data['text'],
                            option1=data.get('option1', ''),
                            option2=data.get('option2', ''),
                            option3=data.get('option3', ''),
                            option4=data.get('option4', ''),
                            correct_answer=int(data.get('correct_answer', 1))
                        )
            
            quiz.save()
            messages.success(request, 'Quiz updated successfully!')
            return JsonResponse({'success': True})
            
        except Exception as e:
            print(f"Error details: {e}")  # Debug print
            messages.error(request, f'Error updating quiz: {str(e)}')
            return JsonResponse({'success': False, 'error': str(e)})
    
    context = {
        'quiz': quiz,
        'course': course,
        'questions': quiz.questions.all()
    }
    return render(request, 'teacher/edit_quiz.html', context)

@login_required
def delete_quiz(request, course_id, quiz_id):
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    
    if course.teacher != request.user.teacher:
        return redirect('LearnPeak:teacher_dashboard')
    
    if request.method == 'POST':
        quiz.delete()
        messages.success(request, 'Quiz deleted successfully!')
    
    return redirect('LearnPeak:manage_quizzes', course_id=course.id)

@login_required
def edit_question(request, course_id, quiz_id, question_id):
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    question = get_object_or_404(Question, id=question_id, quiz=quiz)
    
    if course.teacher != request.user.teacher:
        return redirect('LearnPeak:teacher_dashboard')
    
    if request.method == 'POST':
        question_form = QuestionForm(request.POST, instance=question)
        choice_forms = [ChoiceForm(request.POST, prefix=f'choice_{i}', 
                         instance=question.choice_set.all()[i] if i < question.choice_set.count() else None) 
                       for i in range(4)]
        
        if question_form.is_valid() and all(form.is_valid() for form in choice_forms):
            question = question_form.save()
            
            for form in choice_forms:
                choice = form.save(commit=False)
                choice.question = question
                choice.save()
            
            messages.success(request, 'Question updated successfully!')
            return redirect('LearnPeak:edit_quiz', course_id=course.id, quiz_id=quiz.id)
    else:
        question_form = QuestionForm(instance=question)
        choice_forms = [ChoiceForm(prefix=f'choice_{i}', 
                         instance=question.choice_set.all()[i] if i < question.choice_set.count() else None) 
                       for i in range(4)]
    
    context = {
        'course': course,
        'quiz': quiz,
        'question': question,
        'question_form': question_form,
        'choice_forms': choice_forms,
    }
    
    return render(request, 'teacher/edit_question.html', context)

@login_required
def delete_question(request, course_id, quiz_id, question_id):
    if request.method != 'POST':
        return redirect('LearnPeak:edit_quiz', course_id=course_id, quiz_id=quiz_id)
        
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    question = get_object_or_404(Question, id=question_id, quiz=quiz)
    
    if course.teacher != request.user.teacher:
        messages.error(request, 'You do not have permission to delete this question.')
        return redirect('LearnPeak:teacher_dashboard')
    
    try:
        question.delete()
        messages.success(request, 'Question deleted successfully!')
    except Exception as e:
        messages.error(request, 'Error deleting question.')
    
    return redirect('LearnPeak:edit_quiz', course_id=course_id, quiz_id=quiz_id)

@login_required
def create_assignment(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Check if the logged-in user is the course teacher
    if course.teacher != request.user.teacher:
        return redirect('LearnPeak:teacher_dashboard')
    
    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.course = course
            assignment.save()
            
            # Create notification for enrolled students
            enrolled_students = Student.objects.filter(
                enrollment__course=course
            )
            
            for student in enrolled_students:
                Notification.objects.create(
                    user=student.user,
                    message=f"New assignment '{assignment.title}' has been posted in {course.title}",
                    notification_type='assignment',
                    status='unread'
                )
            
            messages.success(request, 'Assignment created successfully!')
            return redirect('LearnPeak:manage_assignments', course_id=course.id)
    else:
        form = AssignmentForm()
    
    context = {
        'course': course,
        'form': form,
    }
    
    return render(request, 'teacher/create_assignment.html', context)

@login_required
def edit_assignment(request, course_id, assignment_id):
    course = get_object_or_404(Course, id=course_id)
    assignment = get_object_or_404(Assignment, id=assignment_id, course=course)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        deadline = request.POST.get('deadline')
        
        assignment.title = title
        assignment.description = description
        assignment.deadline = deadline
        assignment.save()
        
        messages.success(request, 'Assignment updated successfully!')
        return redirect('LearnPeak:manage_assignments', course_id=course_id)
    
    return render(request, 'teacher/edit_assignment.html', {
        'course': course,
        'assignment': assignment
    })

@login_required
def delete_assignment(request, course_id, assignment_id):
    if request.method != 'POST':
        return redirect('LearnPeak:manage_assignments', course_id=course_id)
        
    course = get_object_or_404(Course, id=course_id)
    assignment = get_object_or_404(Assignment, id=assignment_id, course=course)
    
    if course.teacher != request.user.teacher:
        messages.error(request, 'You do not have permission to delete this assignment.')
        return redirect('LearnPeak:teacher_dashboard')
    
    try:
        assignment.delete()
        messages.success(request, 'Assignment deleted successfully!')
    except Exception as e:
        messages.error(request, 'Error deleting assignment.')
    
    return redirect('LearnPeak:manage_assignments', course_id=course_id)

@login_required
def take_exam(request, course_id, exam_id):
    course = get_object_or_404(Course, id=course_id)
    exam = get_object_or_404(Exam, id=exam_id, course=course)
    student = request.user.student
    
    # Check if student is enrolled
    if not course.enrollment_set.filter(student=student).exists():
        messages.error(request, 'You are not enrolled in this course.')
        return redirect('LearnPeak:student_dashboard')
    
    # Check if exam is already completed
    try:
        result = ExamResult.objects.get(student=student, exam=exam)
        if result.completion_time:
            messages.info(request, 'You have already completed this exam.')
            return redirect('LearnPeak:exam_result', course_id=course_id, exam_id=exam_id)
    except ExamResult.DoesNotExist:
        result = ExamResult.objects.create(student=student, exam=exam)
    
    if request.method == 'POST':
        answers = {}
        for key, value in request.POST.items():
            if key.startswith('question_'):
                question_id = key.split('_')[1]
                answers[question_id] = value
        
        result.answers = answers
        result.completion_time = timezone.now()
        result.calculate_score()
        result.save()
        
        return redirect('LearnPeak:exam_result', course_id=course_id, exam_id=exam_id)
    
    context = {
        'course': course,
        'exam': exam,
        'result': result,
        'questions': exam.questions.all() if exam.exam_type == 'manual' else None,
        'time_remaining': exam.duration * 60  # Convert to seconds for JS timer
    }
    return render(request, 'student/take_exam.html', context)

@login_required
def exam_result(request, course_id, exam_id):
    course = get_object_or_404(Course, id=course_id)
    exam = get_object_or_404(Exam, id=exam_id, course=course)
    result = get_object_or_404(ExamResult, student=request.user.student, exam=exam)
    
    # Add POST handling for feedback
    if request.method == 'POST':
        feedback = request.POST.get('feedback')
        result.teacher_feedback = feedback
        result.save()
        messages.success(request, 'Feedback submitted successfully!')
        return redirect('LearnPeak:exam_result', course_id=course_id, exam_id=exam_id, result_id=result.id)

    context = {
        'course': course,
        'exam': exam,
        'result': result,
        'questions': exam.questions.all() if exam.exam_type == 'manual' else None
    }
    return render(request, 'student/exam_result.html', context)

@login_required
def exam_results_list(request, course_id, exam_id):
    course = get_object_or_404(Course, id=course_id)
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Get results for specific exam
    results = ExamResult.objects.filter(
        exam=exam
    ).select_related('student', 'student__user')
    
    context = {
        'course': course,
        'exam': exam,
        'results': results,
        'total_students': results.count(),
        'average_score': results.aggregate(Avg('score'))['score__avg'] or 0,
    }
    
    return render(request, 'teacher/exam_results_list.html', context)

@login_required
def import_external_results(request, course_id, exam_id):
    course = get_object_or_404(Course, id=course_id)
    exam = get_object_or_404(Exam, id=exam_id, course=course)
    
    if not request.user.is_teacher or course.teacher != request.user.teacher:
        messages.error(request, 'Permission denied.')
        return redirect('LearnPeak:course_detail', course_id=course_id)
    
    if request.method == 'POST' and request.FILES.get('results_file'):
        try:
            # Read the uploaded file (supports CSV and Excel)
            file = request.FILES['results_file']
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            # Expected columns: email/student_id, score
            required_columns = ['student_identifier', 'score']
            if not all(col in df.columns for col in required_columns):
                messages.error(request, 'Invalid file format. Please ensure the file contains student_identifier and score columns.')
                return redirect('LearnPeak:exam_result', course_id=course_id, exam_id=exam_id)
            
            # Process each row
            success_count = 0
            error_count = 0
            
            for _, row in df.iterrows():
                try:
                    # Find student by email or student ID
                    student = Student.objects.get(
                        Q(user__email=row['student_identifier']) |
                        Q(student_id=row['student_identifier'])
                    )
                    
                    # Create or update result
                    result, created = ExamResult.objects.update_or_create(
                        student=student,
                        exam=exam,
                        defaults={
                            'score': float(row['score']),
                            'passed': float(row['score']) >= exam.passing_grade,
                            'completion_time': timezone.now() if created else F('completion_time')
                        }
                    )
                    success_count += 1
                    
                except Student.DoesNotExist:
                    error_count += 1
                    continue
                except Exception as e:
                    error_count += 1
                    continue
            
            messages.success(
                request, 
                f'Import completed. Successfully imported {success_count} results. '
                f'Failed to import {error_count} results.'
            )
            
        except Exception as e:
            messages.error(request, f'Error importing results: {str(e)}')
    
    return redirect('LearnPeak:exam_result', course_id=course_id, exam_id=exam_id)

@login_required
def teacher_exam_result(request, course_id, exam_id, result_id):
    course = get_object_or_404(Course, id=course_id)
    exam = get_object_or_404(Exam, id=exam_id)
    exam_result = get_object_or_404(ExamResult, id=result_id)
    
    context = {
        'course': course,
        'exam': exam,
        'exam_result': exam_result,
    }
    
    return render(request, 'teacher/exam_result.html', context)

@login_required
def teacher_quiz_result(request, course_id, quiz_id, result_id):
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    result = get_object_or_404(QuizResult, id=result_id, quiz=quiz)
    
    if not hasattr(request.user, 'teacher') or course.teacher != request.user.teacher:
        messages.error(request, 'Permission denied.')
        return redirect('LearnPeak:teacher_dashboard')

    class_results = QuizResult.objects.filter(quiz=quiz).exclude(id=result.id)
    class_average = class_results.aggregate(Avg('score'))['score__avg'] or 0
    total_students = QuizResult.objects.filter(quiz=quiz).count()

    if request.method == 'POST':
        if 'score' in request.POST:
            result.score = float(request.POST['score'])
            result.passed = result.score >= quiz.passing_grade
            result.save()
            messages.success(request, 'Score updated successfully!')
        elif 'feedback' in request.POST:
            result.feedback = request.POST['feedback']
            result.save()
            messages.success(request, 'Feedback saved successfully!')
        return redirect('LearnPeak:teacher_quiz_result', course_id, quiz_id, result_id)

    context = {
        'course': course,
        'quiz': quiz,
        'result': result,
        'class_average': class_average,
        'total_students': total_students,
        'questions': quiz.questions.all() if quiz.quiz_type == 'manual' else None
    }
    return render(request, 'teacher/quiz_result.html', context)

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    assignments = course.assignments.all()
    
    # Process each assignment to get its status
    for assignment in assignments:
        assignment.graded_count = assignment.assignmentsubmission_set.filter(status='graded').count()
        assignment.pending_count = assignment.assignmentsubmission_set.filter(status='submitted').count()
    
    context = {
        'course': course,
        'quizzes': course.quizzes.all(),
        'exams': course.exams.all(),
        'assignments': assignments,
        'current_date': timezone.now().date(),
        'pending_count': sum(a.pending_count for a in assignments),
        'graded_count': sum(a.graded_count for a in assignments),
    }
    
    return render(request, 'teacher/course_detail.html', context)

@login_required
def view_student_progress(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Check if the logged-in user is the course teacher
    if not hasattr(request.user, 'teacher') or course.teacher != request.user.teacher:
        messages.error(request, 'Permission denied.')
        return redirect('LearnPeak:teacher_dashboard')
    
    # Get all enrolled students
    enrolled_students = Student.objects.filter(enrollment__course=course)
    
    # Get progress data for each student
    student_progress = []
    for student in enrolled_students:
        progress = {
            'student': student,
            'quiz_results': QuizResult.objects.filter(
                student=student,
                quiz__course=course
            ),
            'assignment_submissions': AssignmentSubmission.objects.filter(
                student=student,
                assignment__course=course
            ),
            'exam_results': ExamResult.objects.filter(
                student=student,
                exam__course=course
            )
        }
        student_progress.append(progress)
    
    context = {
        'course': course,
        'student_progress': student_progress,
    }
    
    return render(request, 'teacher/view_student_progress.html', context)

@login_required
def quiz_results_list(request, course_id, quiz_id):
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    
    # Create a test result if none exists
    if not QuizResult.objects.filter(quiz=quiz).exists():
        # Get the first student (for testing)
        student = Student.objects.first()
        if student:
            # Create a sample quiz result
            test_result = QuizResult.objects.create(
                student=student,
                quiz=quiz,
                score=85.5,  # Sample score
                passed=True,
                feedback="Test feedback",
                completion_time=timezone.now(),
                answers={"1": "A", "2": "B"}  # Sample answers
            )
            print(f"Created test result with ID: {test_result.id}")
    
    results = QuizResult.objects.filter(quiz=quiz).select_related('student', 'student__user')
    print(f"Found {results.count()} results")
    
    context = {
        'course': course,
        'quiz': quiz,
        'results': results,
        'total_students': results.count(),
        'average_score': results.aggregate(Avg('score'))['score__avg'] or 0
    }
    
    return render(request, 'teacher/quiz_results_list.html', context)

@login_required
def edit_exam(request, course_id, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        try:
            print("POST data:", request.POST)  # Debug print
            
            # Update basic exam information
            exam.title = request.POST.get('title')
            exam.description = request.POST.get('description')
            exam.duration = request.POST.get('duration')
            exam.exam_type = request.POST.get('exam_type')
            exam.passing_grade = request.POST.get('passing_grade')
            
            if exam.exam_type == 'external':
                exam.external_link = request.POST.get('external_link')
                exam.questions.all().delete()
            
            elif exam.exam_type == 'manual':
                # First delete existing questions
                exam.questions.all().delete()
                
                # Create new questions
                question_data = {}
                for key, value in request.POST.items():
                    if key.startswith('questions['):
                        # Parse the question index and field
                        parts = key.split('[')
                        idx = parts[1].split(']')[0]
                        field = parts[2].split(']')[0]
                        
                        if idx not in question_data:
                            question_data[idx] = {}
                        question_data[idx][field] = value
                
                print("Question data:", question_data)  # Debug print
                
                # Create questions from the collected data
                for idx, data in question_data.items():
                    if 'text' in data:  # Only create if we have question text
                        ExamQuestion.objects.create(
                            exam=exam,
                            text=data['text'],
                            option1=data.get('option1', ''),
                            option2=data.get('option2', ''),
                            option3=data.get('option3', ''),
                            option4=data.get('option4', ''),
                            correct_answer=int(data.get('correct_answer', 1))
                        )
            
            exam.save()
            messages.success(request, 'Exam updated successfully!')
            return JsonResponse({'success': True})
            
        except Exception as e:
            print(f"Error details: {e}")
            messages.error(request, f'Error updating exam: {str(e)}')
            return JsonResponse({'success': False, 'error': str(e)})
    
    # Serialize questions for the template
    questions_data = []
    for question in exam.questions.all():
        questions_data.append({
            'text': question.text,
            'option1': question.option1,
            'option2': question.option2,
            'option3': question.option3,
            'option4': question.option4,
            'correct_answer': question.correct_answer,
        })
    
    context = {
        'exam': exam,
        'course': course,
        'questions': json.dumps(questions_data),
    }
    return render(request, 'teacher/edit_exam.html', context)

@login_required
def view_exam_results(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Get all exams and students
    exams = course.exams.all()
    enrolled_students = Student.objects.filter(enrollment__course=course)
    
    # Create a dictionary to store all results
    student_results = {}
    for student in enrolled_students:
        results = ExamResult.objects.filter(
            student=student,
            exam__course=course
        )
        student_results[student] = results
    
    context = {
        'course': course,
        'exams': exams,
        'student_results': student_results,
    }
    
    return render(request, 'teacher/view_exam_results.html', context)

@login_required
def view_quiz_results(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Get all quizzes and students
    quizzes = course.quizzes.all()
    enrolled_students = Student.objects.filter(enrollment__course=course)
    
    # Create a dictionary to store all results
    student_results = {}
    for student in enrolled_students:
        results = QuizResult.objects.filter(
            student=student,
            quiz__course=course
        )
        student_results[student] = results
    
    context = {
        'course': course,
        'quizzes': quizzes,
        'student_results': student_results,
    }
    
    return render(request, 'teacher/view_quiz_results.html', context)

@login_required
def quiz_results_list(request, course_id, quiz_id):
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    
    # Get results for specific quiz
    results = QuizResult.objects.filter(
        quiz=quiz
    ).select_related('student', 'student__user')
    
    # Calculate average score
    average_score = results.aggregate(Avg('score'))['score__avg'] or 0
    
    context = {
        'course': course,
        'quiz': quiz,
        'results': results,
        'average_score': average_score,
    }
    
    return render(request, 'teacher/quiz_results_list.html', context)

@login_required
def teacher_quiz_result(request, course_id, quiz_id, result_id):
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    quiz_result = get_object_or_404(QuizResult, id=result_id, quiz=quiz)
    
    # Add POST handling for feedback
    if request.method == 'POST':
        feedback = request.POST.get('feedback')
        quiz_result.teacher_feedback = feedback
        quiz_result.save()
        messages.success(request, 'Feedback submitted successfully!')
        return redirect('LearnPeak:quiz_result', course_id=course_id, quiz_id=quiz_id, result_id=result_id)

    context = {
        'course': course,
        'quiz': quiz,
        'quiz_result': quiz_result,
    }
    return render(request, 'teacher/quiz_result.html', context)

@login_required
def assignment_submissions_list(request, course_id, assignment_id):
    course = get_object_or_404(Course, id=course_id)
    assignment = get_object_or_404(Assignment, id=assignment_id, course=course)
    
    # Get all submissions for this assignment
    submissions = AssignmentSubmission.objects.filter(
        assignment=assignment
    ).select_related('student', 'student__user')
    
    context = {
        'course': course,
        'assignment': assignment,
        'submissions': submissions,
    }
    return render(request, 'teacher/assignment_submissions_list.html', context)

@login_required
def grade_assignment(request, course_id, assignment_id, submission_id):
    course = get_object_or_404(Course, id=course_id)
    assignment = get_object_or_404(Assignment, id=assignment_id, course=course)
    submission = get_object_or_404(AssignmentSubmission, id=submission_id, assignment=assignment)
    
    if request.method == 'POST':
        grade = request.POST.get('grade')
        feedback = request.POST.get('feedback')
        submission.grade = grade
        submission.teacher_feedback = feedback
        submission.status = 'graded'
        submission.save()
        messages.success(request, 'Assignment graded and feedback submitted successfully!')
        return redirect('LearnPeak:grade_assignment', 
                      course_id=course_id, 
                      assignment_id=assignment_id, 
                      submission_id=submission_id)

    context = {
        'course': course,
        'assignment': assignment,
        'submission': submission,
    }
    return render(request, 'teacher/grade_assignment.html', context)

@login_required
def course_progress_dashboard(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Check if the logged-in user is the teacher of this course
    if not hasattr(request.user, 'teacher') or course.teacher != request.user.teacher:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('LearnPeak:teacher_dashboard')
    
    students = Student.objects.filter(enrollment__course=course)
    
    # Calculate per-student progress
    student_progress = []
    for student in students:
        quiz_scores = QuizResult.objects.filter(student=student, quiz__course=course)
        exam_scores = ExamResult.objects.filter(student=student, exam__course=course)
        assignment_submissions = AssignmentSubmission.objects.filter(student=student, assignment__course=course)
        
        student_progress.append({
            'student': student,
            'quiz_average': quiz_scores.aggregate(Avg('score'))['score__avg'] or 0,
            'exam_average': exam_scores.aggregate(Avg('score'))['score__avg'] or 0,
            'assignments_completed': assignment_submissions.filter(status='graded').count(),
            'overall_progress': (
                (quiz_scores.count() + exam_scores.count() + assignment_submissions.filter(status='graded').count()) /
                (course.quizzes.count() + course.exams.count() + course.assignments.count()) * 100
            ) if (course.quizzes.count() + course.exams.count() + course.assignments.count()) > 0 else 0
        })
    
    context = {
        'course': course,
        'students': student_progress,
    }
    return render(request, 'teacher/view_student_progress.html', context)

@login_required
def student_progress_detail(request, course_id, student_id):
    course = get_object_or_404(Course, id=course_id)
    student = get_object_or_404(Student, id=student_id)
    
    # Get all results
    quiz_results = QuizResult.objects.filter(student=student, quiz__course=course)
    exam_results = ExamResult.objects.filter(student=student, exam__course=course)
    assignment_submissions = AssignmentSubmission.objects.filter(student=student, assignment__course=course)
    
    # Calculate statistics
    progress_data = {
        'quiz_stats': {
            'completed': quiz_results.count(),
            'total': course.quizzes.count(),
            'average_score': quiz_results.aggregate(Avg('score'))['score__avg'] or 0,
            'results': quiz_results
        },
        'exam_stats': {
            'completed': exam_results.count(),
            'total': course.exams.count(),
            'average_score': exam_results.aggregate(Avg('score'))['score__avg'] or 0,
            'results': exam_results
        },
        'assignment_stats': {
            'submitted': assignment_submissions.count(),
            'graded': assignment_submissions.filter(status='graded').count(),
            'total': course.assignments.count(),
            'average_grade': assignment_submissions.filter(status='graded').aggregate(Avg('grade'))['grade__avg'] or 0,
            'submissions': assignment_submissions
        }
    }
    
    context = {
        'course': course,
        'student': student,
        'progress_data': progress_data,
    }
    return render(request, 'teacher/student_progress_detail.html', context)

@login_required
def grade_quiz(request, course_id, quiz_id, result_id):
    quiz_result = get_object_or_404(QuizResult, id=result_id)
    if request.method == 'POST':
        feedback = request.POST.get('feedback')
        quiz_result.teacher_feedback = feedback
        quiz_result.save()
        messages.success(request, 'Feedback submitted successfully!')
        return redirect('LearnPeak:quiz_results', course_id=course_id, quiz_id=quiz_id)
    
    context = {
        'quiz_result': quiz_result,
        'course_id': course_id,
        'quiz_id': quiz_id
    }
    return render(request, 'teacher/grade_quiz.html', context)

@login_required
def grade_exam(request, course_id, exam_id, result_id):
    exam_result = get_object_or_404(ExamResult, id=result_id)
    if request.method == 'POST':
        feedback = request.POST.get('feedback')
        exam_result.teacher_feedback = feedback
        exam_result.save()
        messages.success(request, 'Feedback submitted successfully!')
        return redirect('LearnPeak:exam_results', course_id=course_id, exam_id=exam_id)
    
    context = {
        'exam_result': exam_result,
        'course_id': course_id,
        'exam_id': exam_id
    }
    return render(request, 'teacher/grade_exam.html', context)

@login_required
def quiz_result(request, course_id, quiz_id, result_id):
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    quiz_result = get_object_or_404(QuizResult, id=result_id, quiz=quiz)
    
    # Add POST handling for feedback
    if request.method == 'POST':
        feedback = request.POST.get('feedback')
        quiz_result.teacher_feedback = feedback
        quiz_result.save()
        messages.success(request, 'Feedback submitted successfully!')
        return redirect('LearnPeak:quiz_result', course_id=course_id, quiz_id=quiz_id, result_id=result_id)

    context = {
        'course': course,
        'quiz': quiz,
        'quiz_result': quiz_result,
    }
    return render(request, 'teacher/quiz_result.html', context)

@login_required
def exam_result(request, course_id, exam_id, result_id):
    course = get_object_or_404(Course, id=course_id)
    exam = get_object_or_404(Exam, id=exam_id, course=course)
    exam_result = get_object_or_404(ExamResult, id=result_id, exam=exam)
    
    # Add POST handling for feedback
    if request.method == 'POST':
        feedback = request.POST.get('feedback')
        exam_result.teacher_feedback = feedback
        exam_result.save()
        messages.success(request, 'Feedback submitted successfully!')
        return redirect('LearnPeak:exam_result', course_id=course_id, exam_id=exam_id, result_id=result_id)

    context = {
        'course': course,
        'exam': exam,
        'exam_result': exam_result,
    }
    return render(request, 'teacher/exam_result.html', context)

@login_required
def assignment_submission(request, course_id, assignment_id, submission_id):
    course = get_object_or_404(Course, id=course_id)
    assignment = get_object_or_404(Assignment, id=assignment_id, course=course)
    submission = get_object_or_404(AssignmentSubmission, id=submission_id, assignment=assignment)
    
    # Add POST handling for feedback
    if request.method == 'POST':
        feedback = request.POST.get('feedback')
        submission.teacher_feedback = feedback
        submission.save()
        messages.success(request, 'Feedback submitted successfully!')
        return redirect('LearnPeak:assignment_submission', 
                      course_id=course_id, 
                      assignment_id=assignment_id, 
                      submission_id=submission_id)

    context = {
        'course': course,
        'assignment': assignment,
        'submission': submission,
    }
    return render(request, 'teacher/assignment_submission.html', context)