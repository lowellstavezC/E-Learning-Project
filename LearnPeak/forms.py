from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import (
    User, Course, Lesson, Material, Quiz, Question,
    Assignment, LiveSession, Grades, Role, Student, Teacher
)

class UserRegistrationForm(UserCreationForm):
    role = forms.ModelChoiceField(queryset=Role.objects.all(), required=True)
    course_of_study = forms.CharField(
        max_length=100, 
        required=False,
        help_text='Required for students'
    )
    department = forms.CharField(
        max_length=100, 
        required=False,
        help_text='Required for teachers'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role']

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        
        if role:
            if role.role_name.lower() == 'student' and not cleaned_data.get('course_of_study'):
                self.add_error('course_of_study', 'Course of study is required for students')
            elif role.role_name.lower() == 'teacher' and not cleaned_data.get('department'):
                self.add_error('department', 'Department is required for teachers')
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            
            # Create role-specific profile
            if self.cleaned_data['role'].role_name.lower() == 'student':
                Student.objects.create(
                    user=user,
                    course_of_study=self.cleaned_data.get('course_of_study', 'Not specified')
                )
            elif self.cleaned_data['role'].role_name.lower() == 'teacher':
                Teacher.objects.create(
                    user=user,
                    department=self.cleaned_data.get('department', 'Not specified')
                )
                
        return user

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'category', 'teacher']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'content', 'course']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6}),
        }

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['title', 'file', 'file_type', 'lesson']

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'course']

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['quiz', 'text', 'question_type', 'points', 'correct_answer']

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'deadline', 'course']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class GradeSubmissionForm(forms.ModelForm):
    class Meta:
        model = Grades
        fields = ['grade', 'feedback']
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 4}),
        }

class LiveSessionForm(forms.ModelForm):
    class Meta:
        model = LiveSession
        fields = ['title', 'schedule', 'course']
        widgets = {
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        } 