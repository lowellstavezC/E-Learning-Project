from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'LearnPeak'

urlpatterns = [
    path('', views.get_started, name='get_started'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
]