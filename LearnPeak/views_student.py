from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import (Course, Enrollment, Quiz, Assignment, Exam, 
                    QuizResult, AssignmentSubmission, ExamResult, Lesson)
from .decorators import student_required
from .models_student import Student, Enrollment, StudentQuizAttempt, StudentAssignmentSubmission, StudentExamAttempt
from .forms_student import AssignmentSubmissionForm, QuizAnswerForm, ExamAnswerForm, QuizAttemptForm

@login_required
@student_required
def student_dashboard(request):
    student = request.user.student
    enrollments = Enrollment.objects.filter(student=student)
    
    context = {
        'student': student,
        'enrollments': enrollments,
    }
    return render(request, 'student/student_dashboard.html', context)

@login_required
@student_required
def take_quiz(request, course_id, quiz_id):
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    student = request.user.student
    
    # Check if student has already attempted this quiz
    previous_attempt = StudentQuizAttempt.objects.filter(
        student=student, 
        quiz=quiz
    ).first()
    
    if previous_attempt:
        return redirect('LearnPeak:student_quiz_result', 
                      course_id=course_id, 
                      quiz_id=quiz_id, 
                      result_id=previous_attempt.id)
    
    if request.method == 'POST':
        form = QuizAttemptForm(request.POST)
        if form.is_valid():
            attempt = form.save(commit=False)
            attempt.student = student
            attempt.quiz = quiz
            attempt.save()
            return redirect('LearnPeak:student_quiz_result', 
                          course_id=course_id, 
                          quiz_id=quiz_id, 
                          result_id=attempt.id)
    else:
        form = QuizAttemptForm()
    
    context = {
        'course': course,
        'quiz': quiz,
        'form': form,
    }
    return render(request, 'student/take_quiz.html', context)

@login_required
@student_required
def view_assignment(request, course_id, assignment_id):
    course = get_object_or_404(Course, id=course_id)
    assignment = get_object_or_404(Assignment, id=assignment_id, course=course)
    
    # Check if student is enrolled
    if not Enrollment.objects.filter(student=request.user.student, course=course).exists():
        messages.error(request, 'You must be enrolled in this course to view assignments.')
        return redirect('LearnPeak:student_dashboard')
    
    # Get existing submission if any
    submission = AssignmentSubmission.objects.filter(
        student=request.user.student, 
        assignment=assignment
    ).first()
    
    context = {
        'course': course,
        'assignment': assignment,
        'submission': submission
    }
    return render(request, 'student/view_assignment.html', context)

@login_required
@student_required
def take_exam(request, course_id, exam_id):
    course = get_object_or_404(Course, id=course_id)
    exam = get_object_or_404(Exam, id=exam_id, course=course)
    
    # Check if student is enrolled
    if not Enrollment.objects.filter(student=request.user.student, course=course).exists():
        messages.error(request, 'You must be enrolled in this course to take the exam.')
        return redirect('LearnPeak:student_dashboard')
    
    # Check if exam is already taken
    if ExamResult.objects.filter(student=request.user.student, exam=exam).exists():
        messages.warning(request, 'You have already taken this exam.')
        return redirect('LearnPeak:student_exam_result', course_id=course_id, exam_id=exam_id)
    
    context = {
        'course': course,
        'exam': exam,
        'questions': exam.questions.all()
    }
    return render(request, 'student/take_exam.html', context)

@login_required
@student_required
def view_progress(request):
    enrolled_courses = Course.objects.filter(enrollment__student=request.user.student)
    progress_data = []
    
    for course in enrolled_courses:
        quizzes_completed = QuizResult.objects.filter(
            student=request.user.student, 
            quiz__course=course
        ).count()
        assignments_completed = AssignmentSubmission.objects.filter(
            student=request.user.student, 
            assignment__course=course,
            status='graded'
        ).count()
        exams_completed = ExamResult.objects.filter(
            student=request.user.student, 
            exam__course=course
        ).count()
        
        progress_data.append({
            'course': course,
            'quizzes_completed': quizzes_completed,
            'assignments_completed': assignments_completed,
            'exams_completed': exams_completed
        })
    
    context = {
        'progress_data': progress_data
    }
    return render(request, 'student/view_progress.html', context)

@login_required
def available_courses(request):
    # Get the student
    student = request.user.student
    
    # Get courses the student is not enrolled in
    enrolled_courses = Course.objects.filter(enrollment__student=student)
    available_courses = Course.objects.exclude(id__in=enrolled_courses.values_list('id', flat=True))
    
    context = {
        'available_courses': available_courses,
        'student': student,
    }
    return render(request, 'student/available_courses.html', context)

@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    student = request.user.student
    
    # Check if already enrolled
    if Enrollment.objects.filter(student=student, course=course).exists():
        messages.warning(request, 'You are already enrolled in this course.')
    else:
        # Create enrollment
        Enrollment.objects.create(
            student=student,
            course=course,
            status='active'
        )
        messages.success(request, f'Successfully enrolled in {course.title}')
    
    return redirect('LearnPeak:student_dashboard')

@login_required
def student_course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    student = request.user.student
    enrollment = get_object_or_404(Enrollment, student=student, course=course)
    
    context = {
        'course': course,
        'enrollment': enrollment,
        'lessons': course.lessons.all(),
        'quizzes': course.quizzes.all(),
        'assignments': course.assignments.all(),
    }
    return render(request, 'student/student_course_detail.html', context)

@login_required
def student_quiz_result(request, course_id, quiz_id, result_id):
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    result = get_object_or_404(StudentQuizAttempt, id=result_id, 
                              student=request.user.student, quiz=quiz)
    
    context = {
        'course': course,
        'quiz': quiz,
        'result': result,
    }
    return render(request, 'student/student_quiz_result.html', context)

@login_required
def submit_assignment(request, course_id, assignment_id):
    course = get_object_or_404(Course, id=course_id)
    assignment = get_object_or_404(Assignment, id=assignment_id, course=course)
    student = request.user.student

    if request.method == 'POST':
        # Change submission_file to file here
        file = request.FILES.get('file')  # Changed from submission_file
        if file:
            submission = StudentAssignmentSubmission.objects.create(
                student=student,
                assignment=assignment,
                file=file  # Changed from submission_file
            )
            messages.success(request, 'Assignment submitted successfully!')
            return redirect('LearnPeak:student_course_detail', course_id=course_id)
    
    context = {
        'course': course,
        'assignment': assignment,
    }
    return render(request, 'student/submit_assignment.html', context)

@login_required
def submit_quiz(request, course_id, quiz_id):
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    student = request.user.student

    if request.method == 'POST':
        # Get answers from the form
        answers = {}
        for question in quiz.questions.all():
            answer = request.POST.get(f'question_{question.id}')
            if answer:
                answers[str(question.id)] = answer

        # Calculate score
        total_questions = quiz.questions.count()
        correct_answers = 0
        for question_id, answer in answers.items():
            question = quiz.questions.get(id=question_id)
            if int(answer) == question.correct_answer:
                correct_answers += 1

        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

        # Create quiz attempt
        quiz_attempt = StudentQuizAttempt.objects.create(
            student=student,
            quiz=quiz,
            score=score,
            answers=answers
        )

        return redirect('LearnPeak:student_quiz_result', 
                      course_id=course_id, 
                      quiz_id=quiz_id, 
                      result_id=quiz_attempt.id)

    return redirect('LearnPeak:take_quiz', course_id=course_id, quiz_id=quiz_id)

@login_required
def submit_exam(request, course_id, exam_id):
    course = get_object_or_404(Course, id=course_id)
    exam = get_object_or_404(Exam, id=exam_id, course=course)
    student = request.user.student

    if request.method == 'POST':
        # Get answers from the form
        answers = {}
        for question in exam.questions.all():
            answer = request.POST.get(f'question_{question.id}')
            if answer:
                answers[str(question.id)] = answer

        # Calculate score
        total_questions = exam.questions.count()
        correct_answers = 0
        for question_id, answer in answers.items():
            question = exam.questions.get(id=question_id)
            if int(answer) == question.correct_answer:
                correct_answers += 1

        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        passed = score >= exam.passing_grade

        # Create exam result
        exam_result = ExamResult.objects.create(
            student=student,
            exam=exam,
            score=score,
            passed=passed,
            answers=answers
        )

        return redirect('LearnPeak:student_exam_result', 
                      course_id=course_id, 
                      exam_id=exam_id, 
                      result_id=exam_result.id)

    return redirect('LearnPeak:take_exam', course_id=course_id, exam_id=exam_id)

@login_required
def exam_result(request, course_id, exam_id, result_id):
    course = get_object_or_404(Course, id=course_id)
    exam = get_object_or_404(Exam, id=exam_id, course=course)
    result = get_object_or_404(ExamResult, id=result_id, student=request.user.student, exam=exam)
    
    context = {
        'course': course,
        'exam': exam,
        'result': result,
        'answers': result.answers,
        'questions': exam.questions.all(),
    }
    return render(request, 'student/exam_result.html', context)

@login_required
def course_progress(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    student = request.user.student
    enrollment = get_object_or_404(Enrollment, student=student, course=course)

    # Get quiz attempts
    quiz_attempts = StudentQuizAttempt.objects.filter(
        student=student,
        quiz__course=course
    )
    
    # Get assignment submissions
    assignment_submissions = StudentAssignmentSubmission.objects.filter(
        student=student,
        assignment__course=course
    )
    
    # Get exam results
    exam_results = ExamResult.objects.filter(
        student=student,
        exam__course=course
    )

    # Calculate progress
    total_items = course.lessons.count() + course.quizzes.count() + course.assignments.count()
    completed_items = (
        quiz_attempts.count() +
        assignment_submissions.filter(grade__isnull=False).count()
    )
    
    progress_percentage = (completed_items / total_items * 100) if total_items > 0 else 0

    context = {
        'course': course,
        'enrollment': enrollment,
        'quiz_attempts': quiz_attempts,
        'assignment_submissions': assignment_submissions,
        'exam_results': exam_results,
        'progress_percentage': round(progress_percentage, 1),
        'completed_items': completed_items,
        'total_items': total_items
    }
    
    return render(request, 'student/course_progress.html', context)

@login_required
def view_lesson(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    student = request.user.student
    
    # Verify student is enrolled in the course
    enrollment = get_object_or_404(Enrollment, student=student, course=course)
    
    # Get next and previous lessons
    next_lesson = Lesson.objects.filter(
        course=course, 
        created_at__gt=lesson.created_at
    ).order_by('created_at').first()
    
    prev_lesson = Lesson.objects.filter(
        course=course, 
        created_at__lt=lesson.created_at
    ).order_by('-created_at').first()
    
    context = {
        'course': course,
        'lesson': lesson,
        'next_lesson': next_lesson,
        'prev_lesson': prev_lesson,
        'enrollment': enrollment,
    }
    return render(request, 'student/view_lesson.html', context)