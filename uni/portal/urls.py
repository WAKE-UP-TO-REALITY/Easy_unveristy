from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('login-verify-otp/', views.login_verify_otp, name='login_verify_otp'),
    path('logout/', views.logout_view, name='logout'),
    path('student-enrollment/<int:user_id>/', views.student_subject_enrollment, name='student_subject_enrollment'),
    path('teacher-subject/<int:user_id>/', views.teacher_subject_selection, name='teacher_subject_selection'),
    
    # Student URLs
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/modules/', views.student_modules, name='student_modules'),
    path('student/submit-doubt/', views.submit_doubt, name='submit_doubt'),
    path('student/doubts/', views.student_doubts, name='student_doubts'),
    
    # Teacher URLs
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/mark-attendance/', views.mark_attendance, name='mark_attendance'),
    path('teacher/view-attendance/', views.view_attendance, name='view_attendance'),
    path('teacher/upload-module/', views.upload_module, name='upload_module'),
    path('teacher/modules/', views.teacher_modules, name='teacher_modules'),
    path('teacher/doubts/', views.teacher_doubts, name='teacher_doubts'),
    path('teacher/respond-doubt/<int:doubt_id>/', views.respond_doubt, name='respond_doubt'),
]
