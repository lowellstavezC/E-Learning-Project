from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('role_name', 'created_at', 'updated_at')
    search_fields = ('role_name',)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_role', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)

    def get_role(self, obj):
        return obj.role.role_name if obj.role else 'No Role'
    get_role.short_description = 'Role'

@admin.register(Admin)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__username',)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'created_at')
    search_fields = ('user__username', 'department')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course_of_study', 'created_at')
    search_fields = ('user__username', 'course_of_study')

@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'teacher', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'description')

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'created_at')
    list_filter = ('course', 'created_at')
    search_fields = ('title', 'content')

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'created_at')
    list_filter = ('course', 'created_at')
    search_fields = ('title',)

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'deadline', 'created_at')
    list_filter = ('course', 'deadline')
    search_fields = ('title', 'description')

@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'schedule', 'created_at')
    list_filter = ('course', 'schedule')
    search_fields = ('title',)

@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'created_at')
    list_filter = ('course', 'created_at')
    search_fields = ('content',)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'created_at')
    list_filter = ('course', 'created_at')
    search_fields = ('student__user__username', 'course__title')

@admin.register(Grades)
class GradesAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'grade', 'updated_at')
    list_filter = ('course', 'updated_at')
    search_fields = ('student__user__username', 'course__title')

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'issued_date')
    list_filter = ('course', 'issued_date')
    search_fields = ('student__user__username', 'course__title')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'status', 'created_at')
    list_filter = ('notification_type', 'status', 'created_at')
    search_fields = ('user__username', 'message')

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'action', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('admin__user__username', 'action')
