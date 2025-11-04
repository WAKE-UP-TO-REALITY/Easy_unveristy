from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime

class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ]
    mobile_number = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    otp = models.CharField(max_length=6, null=True, blank=True)
    is_mobile_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.username} - {self.role}"

class Subject(models.Model):
    SUBJECT_CHOICES = [
        ('subject1', 'Subject 1 (10-11 AM)'),
        ('subject2', 'Subject 2 (11-12 PM)'),
        ('subject3', 'Subject 3 (1-2 PM)'),
        ('subject4', 'Subject 4 (2-3 PM)'),
        ('subject5', 'Subject 5 (3-4 PM)'),
        ('subject6', 'Subject 6 (4-5 PM)'),
    ]
    TIME_SLOTS = {
        'subject1': '10:00-11:00',
        'subject2': '11:00-12:00',
        'subject3': '13:00-14:00',
        'subject4': '14:00-15:00',
        'subject5': '15:00-16:00',
        'subject6': '16:00-17:00',
    }
    
    name = models.CharField(max_length=50, choices=SUBJECT_CHOICES, unique=True)
    code = models.CharField(max_length=10, unique=True)
    
    def __str__(self):
        return f"{self.get_name_display()}"

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    enrollment_number = models.CharField(max_length=20, unique=True)
    subjects = models.ManyToManyField(Subject, related_name='enrolled_students')
    
    def __str__(self):
        return f"{self.user.username} - {self.enrollment_number}"
    
    def get_absence_count(self, subject):
        """Get total absences for a specific subject"""
        return Attendance.objects.filter(
            student=self,
            subject=subject,
            is_present=False
        ).exclude(
            date__week_day__in=[1, 7]  # Exclude Sunday(1) and Saturday(7)
        ).count()

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, related_name='teacher')
    employee_id = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.subject.name if self.subject else 'No Subject'}"

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date = models.DateField()
    is_present = models.BooleanField(default=False)
    marked_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        unique_together = ('student', 'subject', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.student.user.username} - {self.subject.name} - {self.date} - {'Present' if self.is_present else 'Absent'}"

class Module(models.Model):
    MODULE_TYPES = [
        ('class_module', 'Class Module'),
        ('theory', 'Theory'),
    ]
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='modules')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    module_type = models.CharField(max_length=20, choices=MODULE_TYPES)
    file = models.FileField(upload_to='modules/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.title} - {self.subject.name}"

class Doubt(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='doubts')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='received_doubts')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    question = models.TextField()
    response = models.TextField(blank=True, null=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Doubt from {self.student.user.username} to {self.teacher.user.username}"
