from django import forms
from .models_student import StudentAssignmentSubmission, StudentQuizAttempt

class QuizAttemptForm(forms.ModelForm):
    class Meta:
        model = StudentQuizAttempt
        fields = ['answers']
        widgets = {
            'answers': forms.HiddenInput()
        }

class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = StudentAssignmentSubmission
        fields = ['submission_file']

class QuizAnswerForm(forms.Form):
    def __init__(self, *args, quiz=None, **kwargs):
        super().__init__(*args, **kwargs)
        if quiz:
            for question in quiz.questions.all():
                if question.question_type == 'multiple_choice':
                    choices = [(choice.id, choice.text) for choice in question.choices.all()]
                    self.fields[f'question_{question.id}'] = forms.ChoiceField(
                        choices=choices,
                        widget=forms.RadioSelect(attrs={
                            'class': 'form-radio text-blue-600'
                        }),
                        label=question.text
                    )
                elif question.question_type == 'text':
                    self.fields[f'question_{question.id}'] = forms.CharField(
                        widget=forms.Textarea(attrs={
                            'class': 'form-textarea mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                            'rows': '3'
                        }),
                        label=question.text
                    )

class ExamAnswerForm(forms.Form):
    def __init__(self, *args, exam=None, **kwargs):
        super().__init__(*args, **kwargs)
        if exam:
            for question in exam.questions.all():
                if question.question_type == 'multiple_choice':
                    choices = [(choice.id, choice.text) for choice in question.choices.all()]
                    self.fields[f'question_{question.id}'] = forms.ChoiceField(
                        choices=choices,
                        widget=forms.RadioSelect(attrs={
                            'class': 'form-radio text-blue-600'
                        }),
                        label=question.text
                    )
                elif question.question_type == 'text':
                    self.fields[f'question_{question.id}'] = forms.CharField(
                        widget=forms.Textarea(attrs={
                            'class': 'form-textarea mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                            'rows': '3'
                        }),
                        label=question.text
                    ) 