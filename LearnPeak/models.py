from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.db.models import Avg
from django.core.cache import cache
from django.conf import settings
from django.apps import apps
from django.contrib import messages
from .models_student import Student, Enrollment, StudentQuizAttempt, StudentAssignmentSubmission

class Role(models.Model):
    role_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.role_name

    @classmethod
    def create_default_roles(cls):
        roles = ['admin', 'teacher', 'student']
        for role_name in roles:
            cls.objects.get_or_create(role_name=role_name)

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        
        # Create admin role if it doesn't exist
        admin_role, _ = Role.objects.get_or_create(role_name='admin')
        
        email = self.normalize_email(email)
        extra_fields.setdefault('role', admin_role)
        
        # Remove username from extra_fields if it exists
        extra_fields.pop('username', None)
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('name', 'Admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None  # Remove username field
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.ForeignKey('Role', on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        swappable = 'AUTH_USER_MODEL'

    def __str__(self):
        return self.email

class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.email

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.email

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='courses')
    students = models.ManyToManyField(Student, through=Enrollment)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    file = models.FileField(upload_to='lesson_materials/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Quiz(models.Model):
    QUIZ_TYPE_CHOICES = [
        ('external', 'External Link'),
        ('manual', 'Manual Input')
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    duration = models.IntegerField()  # in minutes
    quiz_type = models.CharField(max_length=20, choices=[('manual', 'Manual'), ('external', 'External')])
    external_link = models.URLField(blank=True, null=True)
    attempts = models.ManyToManyField(Student, through=StudentQuizAttempt)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return f"{self.title} - {self.course.title}"

class Question(models.Model):
    quiz = models.ForeignKey('Quiz', on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200)
    option4 = models.CharField(max_length=200)
    correct_answer = models.IntegerField()

    def __str__(self):
        return self.text[:50]

    class Meta:
        db_table = 'LearnPeak_question'

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.text

class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    deadline = models.DateTimeField()
    file = models.FileField(upload_to='assignments/', null=True, blank=True)
    submissions = models.ManyToManyField(Student, through=StudentAssignmentSubmission)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

class Grades(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, null=True, blank=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, null=True, blank=True)
    grade = models.FloatField()
    feedback = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.user.email} - {self.course.title}"

class LiveSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    schedule = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Discussion(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.course.title}"

class Certificate(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    issued_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.student.user.email} - {self.course.title}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    notification_type = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.email} - {self.notification_type}"

class SystemLog(models.Model):
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, null=True)
    action = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.timestamp} - {self.action}"

class Exam(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration = models.IntegerField()  # in minutes
    exam_type = models.CharField(
        max_length=20,
        choices=[('manual', 'Manual'), ('external', 'External')],
        default='manual'
    )
    external_link = models.URLField(blank=True, null=True)
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='exams')
    passing_grade = models.IntegerField(default=60)
    points = models.IntegerField(default=100)  # Added points field to Exam
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class ExamResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.FloatField()
    passed = models.BooleanField(default=False)
    completion_time = models.DateTimeField(auto_now_add=True)
    answers = models.JSONField(default=dict)
    feedback = models.TextField(null=True, blank=True)
    teacher_feedback = models.TextField(blank=True, null=True)
    feedback_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'exam']
        ordering = ['-completion_time']

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.exam.title} ({self.score}%)"

    def calculate_score(self):
        if self.exam.exam_type == 'manual':
            total_points = sum(question.points for question in self.exam.manual_questions.all())
            earned_points = 0
            
            for question_id, answer in self.answers.items():
                question = self.exam.manual_questions.get(id=question_id)
                if int(answer) == question.correct_answer:
                    earned_points += question.points
            
            self.score = (earned_points / total_points) * 100 if total_points > 0 else 0
            self.passed = self.score >= self.exam.passing_grade
            return self.score
        return None

    @property
    def correct_count(self):
        if self.exam.exam_type == 'manual':
            return sum(1 for q_id, ans in self.answers.items() 
                      if int(ans) == self.exam.manual_questions.get(id=int(q_id)).correct_answer)
        return None

    @property
    def correct_percentage(self):
        if self.exam.exam_type == 'manual':
            total = self.exam.manual_questions.count()
            return (self.correct_count / total * 100) if total > 0 else 0
        return None

class QuizQuestion(models.Model):
    quiz = models.ForeignKey('Quiz', on_delete=models.CASCADE, related_name='quiz_questions')
    question_text = models.TextField()
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200)
    option4 = models.CharField(max_length=200)
    correct_answer = models.IntegerField()

    def __str__(self):
        return self.question_text[:50]

    class Meta:
        db_table = 'LearnPeak_quizquestion'

class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()  # We'll stick with 'text' as the field name
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200)
    option4 = models.CharField(max_length=200)
    correct_answer = models.IntegerField(
        choices=[(1, 'Option 1'), (2, 'Option 2'), (3, 'Option 3'), (4, 'Option 4')]
    )

    def __str__(self):
        return self.text[:50]

class AssignmentSubmission(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    submitted_file = models.FileField(upload_to='assignment_submissions/', null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    teacher_feedback = models.TextField(blank=True, null=True)
    feedback_date = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=[
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('returned', 'Returned')
    ], default='submitted')

    class Meta:
        unique_together = ['student', 'assignment']

    def __str__(self):
        return f"{self.student.user.name}'s submission for {self.assignment.title}"

class QuizResult(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    quiz = models.ForeignKey('Quiz', on_delete=models.CASCADE)
    score = models.IntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)
    answers = models.JSONField(default=dict)
    teacher_feedback = models.TextField(blank=True, null=True)
    feedback_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} - {self.quiz} - {self.score}"

    class Meta:
        verbose_name = 'Quiz Result'
        verbose_name_plural = 'Quiz Results'