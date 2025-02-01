from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'LearnPeak'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
     path('login/', views.user_login, name='login'),
    
    
    # Dashboard URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    
    # Password Reset URLs
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='password/password_reset.html',
             email_template_name='password/password_reset_email.html',
             success_url='/password_reset/done/'
         ),
         name='password_reset'),
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='password/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='password/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='password/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    path('enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('course/<int:course_id>/discussions/', views.course_discussions, name='course_discussions'),
    path('teacherdashboard/', views.teacher_dashboard, name='teacherdashboard'),
    path('course/create/', views.course_create, name='course_create'),
    path('course/<int:course_id>/lesson/create/', views.lesson_create, name='lesson_create'),
    path('lesson/<int:lesson_id>/material/upload/', views.material_upload, name='material_upload'),
    path('course/<int:course_id>/quiz/create/', views.quiz_create, name='quiz_create'),
    path('course/<int:course_id>/assignment/create/', views.assignment_create, name='assignment_create'),
    path('submission/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),
    path('course/<int:course_id>/live-session/create/', views.live_session_create, name='live_session_create'),
    path('studentdashboard/', views.student_dashboard, name='studentdashboard'),
]