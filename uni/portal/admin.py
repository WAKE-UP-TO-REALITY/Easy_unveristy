from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Student, Teacher, Subject, Attendance, Module, Doubt

# Custom User Admin
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'mobile_number', 'role', 'is_mobile_verified', 'is_staff']
    list_filter = ['role', 'is_mobile_verified', 'is_staff', 'is_active']
    search_fields = ['username', 'mobile_number']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'mobile_number')}),
        ('Role & Verification', {'fields': ('role', 'is_mobile_verified', 'otp')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'mobile_number', 'role', 'password1', 'password2'),
        }),
    )

# Student Admin
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['user', 'enrollment_number', 'get_total_subjects']
    search_fields = ['user__username', 'enrollment_number']
    filter_horizontal = ['subjects']
    
    def get_total_subjects(self, obj):
        return obj.subjects.count()
    get_total_subjects.short_description = 'Total Subjects'

# Teacher Admin
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'employee_id']
    list_filter = ['subject']
    search_fields = ['user__username', 'employee_id']

# Subject Admin
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'get_enrolled_students']
    search_fields = ['name', 'code']
    
    def get_enrolled_students(self, obj):
        return obj.enrolled_students.count()
    get_enrolled_students.short_description = 'Enrolled Students'

# Attendance Admin
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'date', 'is_present', 'marked_by']
    list_filter = ['subject', 'date', 'is_present']
    search_fields = ['student__user__username', 'student__enrollment_number']
    date_hierarchy = 'date'
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return ['student', 'subject', 'date', 'marked_by']
        return []

# Module Admin
@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'teacher', 'module_type', 'uploaded_at']
    list_filter = ['subject', 'module_type', 'uploaded_at']
    search_fields = ['title', 'teacher__user__username']
    date_hierarchy = 'uploaded_at'
    readonly_fields = ['uploaded_at']

# Doubt Admin
@admin.register(Doubt)
class DoubtAdmin(admin.ModelAdmin):
    list_display = ['student', 'teacher', 'subject', 'is_resolved', 'created_at', 'resolved_at']
    list_filter = ['is_resolved', 'subject', 'created_at']
    search_fields = ['student__user__username', 'teacher__user__username', 'question']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'resolved_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('student', 'teacher', 'subject')
        }),
        ('Doubt Details', {
            'fields': ('question', 'response', 'is_resolved')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
