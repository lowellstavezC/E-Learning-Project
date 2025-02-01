from django.contrib import admin
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .decorators import admin_only
from .models import (
    Role, User, Admin, Teacher, Student, 
    CourseCategory, Course, Lesson, Quiz, 
    Assignment, LiveSession, Discussion, 
    Enrollment, Grades, Certificate, 
    Notification, SystemLog
)

# Admin Dashboard View
@login_required
@admin_only
def admin_dashboard(request):
    context = {
        'total_users': User.objects.count(),
        'teacher_count': Teacher.objects.count(),
        'student_count': Student.objects.count(),
        'active_courses': Course.objects.filter(is_active=True).count(),
        'course_categories': CourseCategory.objects.count(),
        'recent_activities': SystemLog.objects.count(),
        'recent_users': User.objects.order_by('-created_at')[:5],
        'system_logs': SystemLog.objects.order_by('-timestamp')[:5],
        'categories': CourseCategory.objects.all(),
        'active_users_today': User.objects.filter(last_login__date=timezone.now().date()).count(),
        'weekly_enrollments': Enrollment.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count(),
        'monthly_completions': Certificate.objects.filter(
            issued_date__gte=timezone.now() - timedelta(days=30)
        ).count(),
        'avg_course_rating': 4.5,  # You can implement actual rating logic
    }
    return render(request, 'admin_dashboard.html', context)

# Register your models
admin.site.register(Role)
admin.site.register(User)
admin.site.register(Admin)
admin.site.register(Teacher)
admin.site.register(Student)
admin.site.register(CourseCategory)
admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Quiz)
admin.site.register(Assignment)
admin.site.register(LiveSession)
admin.site.register(Discussion)
admin.site.register(Enrollment)
admin.site.register(Grades)
admin.site.register(Certificate)
admin.site.register(Notification)
admin.site.register(SystemLog)
