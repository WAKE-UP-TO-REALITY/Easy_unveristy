from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date
from .models import User, Student, Teacher, Subject, Attendance, Module, Doubt
from .utils import generate_otp, send_otp_via_sms, verify_otp, is_weekend

# Authentication Views
def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        mobile_number = request.POST.get('mobile_number')
        role = request.POST.get('role')
        password = request.POST.get('password')
        
        # Check if user exists
        if User.objects.filter(mobile_number=mobile_number).exists():
            messages.error(request, 'Mobile number already registered')
            return render(request, 'portal/signup.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            mobile_number=mobile_number,
            role=role,
            password=password
        )
        
        # Generate and send OTP
        otp = generate_otp()
        user.otp = otp
        user.save()
        
        # Send OTP via SMS
        send_otp_via_sms(mobile_number, otp)
        
        request.session['user_id'] = user.id
        messages.success(request, 'OTP sent to your mobile number')
        return redirect('verify_otp')
    
    return render(request, 'portal/signup.html')

def verify_otp_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('signup')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        otp = request.POST.get('otp')
        
        if verify_otp(otp, user.otp):
            user.is_mobile_verified = True
            user.otp = None
            user.save()
            
            # Create profile based on role
            if user.role == 'student':
                return redirect('student_subject_enrollment', user_id=user.id)
            else:
                return redirect('teacher_subject_selection', user_id=user.id)
        else:
            messages.error(request, 'Invalid OTP')
    
    return render(request, 'portal/verify_otp.html', {'user': user})

def student_subject_enrollment(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        enrollment_number = request.POST.get('enrollment_number')
        
        # Create student profile
        student = Student.objects.create(
            user=user,
            enrollment_number=enrollment_number
        )
        
        # Enroll in all 6 subjects
        all_subjects = Subject.objects.all()
        student.subjects.set(all_subjects)
        
        login(request, user)
        messages.success(request, 'Registration complete! You are enrolled in all subjects.')
        return redirect('student_dashboard')
    
    return render(request, 'portal/student_enrollment.html', {'user': user})

def teacher_subject_selection(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        subject_id = request.POST.get('subject')
        
        subject = get_object_or_404(Subject, id=subject_id)
        
        # Create teacher profile
        Teacher.objects.create(
            user=user,
            employee_id=employee_id,
            subject=subject
        )
        
        login(request, user)
        messages.success(request, f'Registration complete! You are assigned to {subject.name}.')
        return redirect('teacher_dashboard')
    
    subjects = Subject.objects.all()
    return render(request, 'portal/teacher_subject_selection.html', {
        'user': user,
        'subjects': subjects
    })

def login_view(request):
    if request.method == 'POST':
        mobile_number = request.POST.get('mobile_number')
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(mobile_number=mobile_number)
            user = authenticate(username=user.username, password=password)
            
            if user:
                # Generate and send OTP
                otp = generate_otp()
                user.otp = otp
                user.save()
                
                send_otp_via_sms(mobile_number, otp)
                
                request.session['login_user_id'] = user.id
                messages.success(request, 'OTP sent to your mobile')
                return redirect('login_verify_otp')
            else:
                messages.error(request, 'Invalid credentials')
        except User.DoesNotExist:
            messages.error(request, 'Mobile number not registered')
    
    return render(request, 'portal/login.html')

def login_verify_otp(request):
    user_id = request.session.get('login_user_id')
    if not user_id:
        return redirect('login')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        otp = request.POST.get('otp')
        
        if verify_otp(otp, user.otp):
            user.otp = None
            user.save()
            login(request, user)
            
            if user.role == 'student':
                return redirect('student_dashboard')
            else:
                return redirect('teacher_dashboard')
        else:
            messages.error(request, 'Invalid OTP')
    
    return render(request, 'portal/login_verify_otp.html')

def logout_view(request):
    logout(request)
    return redirect('login')

# Student Dashboard Views
@login_required
@login_required
@login_required
def student_dashboard(request):
    student = request.user.student_profile
    subjects = student.subjects.all()
    
    # Calculate absence count for each subject
    subject_absences = {}
    total_absences = 0
    high_absence_subjects = []
    
    for subject in subjects:
        absence_count = student.get_absence_count(subject)
        subject_absences[subject] = absence_count
        total_absences += absence_count
        
        # Mark as critical if absences >= 3
        if absence_count >= 3:
            high_absence_subjects.append({
                'get_name_display': subject.get_name_display(),
                'absence_count': absence_count
            })
    
    context = {
        'student': student,
        'subject_absences': subject_absences,
        'total_absences': total_absences,
        'high_absence_subjects': high_absence_subjects,
    }
    
    return render(request, 'portal/student_dashboard.html', context)



@login_required
def student_modules(request):
    student = request.user.student_profile
    subjects = student.subjects.all()
    
    modules = Module.objects.filter(subject__in=subjects).order_by('-uploaded_at')
    
    context = {
        'modules': modules,
        'subjects': subjects,
    }
    return render(request, 'portal/student_modules.html', context)

@login_required
def submit_doubt(request):
    student = request.user.student_profile
    
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        question = request.POST.get('question')
        
        subject = get_object_or_404(Subject, id=subject_id)
        
        # Get the teacher who teaches this subject
        teacher = Teacher.objects.filter(subject=subject).first()
        
        if teacher:
            Doubt.objects.create(
                student=student,
                teacher=teacher,
                subject=subject,
                question=question
            )
            messages.success(request, '✅ Doubt submitted successfully!')
            return redirect('student_doubts')
        else:
            messages.error(request, '❌ No teacher assigned to this subject.')
    
    student = Student.objects.get(user=request.user)
    subjects = student.subjects.all()
    
    return render(request, 'portal/submit_doubt.html', {'subjects': subjects})


@login_required
def student_doubts(request):
    student = request.user.student_profile
    doubts = student.doubts.all()
    
    return render(request, 'portal/student_doubts.html', {'doubts': doubts})

# Teacher Dashboard Views
@login_required
def teacher_dashboard(request):
    teacher = request.user.teacher_profile
    subject = teacher.subject
    
    # Get students enrolled in teacher's subject
    students = Student.objects.filter(subjects=subject)
    
    # Get pending doubts
    pending_doubts = teacher.received_doubts.filter(is_resolved=False).count()
    
    context = {
        'teacher': teacher,
        'subject': subject,
        'students_count': students.count(),
        'pending_doubts': pending_doubts,
    }
    return render(request, 'portal/teacher_dashboard.html', context)

@login_required
def mark_attendance(request):
    teacher = request.user.teacher_profile
    subject = teacher.subject
    students = Student.objects.filter(subjects=subject)
    
    today = date.today()
    
    # Check if today is weekend
    if is_weekend(today):
        messages.warning(request, 'Cannot mark attendance on weekends')
        return redirect('teacher_dashboard')
    
    # Check if attendance already marked
    if Attendance.objects.filter(subject=subject, date=today).exists():
        messages.warning(request, 'Attendance already marked for today')
        return redirect('view_attendance')
    
    if request.method == 'POST':
        present_students = request.POST.getlist('present_students')
        
        for student in students:
            is_present = str(student.id) in present_students
            
            Attendance.objects.create(
                student=student,
                subject=subject,
                date=today,
                is_present=is_present,
                marked_by=teacher
            )
        
        messages.success(request, 'Attendance marked successfully!')
        return redirect('teacher_dashboard')
    
    context = {
        'students': students,
        'subject': subject,
        'today': today,
    }
    return render(request, 'portal/mark_attendance.html', context)

@login_required
def view_attendance(request):
    teacher = request.user.teacher_profile
    subject = teacher.subject
    
    attendances = Attendance.objects.filter(subject=subject).order_by('-date')
    
    return render(request, 'portal/view_attendance.html', {'attendances': attendances})

@login_required
def upload_module(request):
    teacher = request.user.teacher_profile
    
    if request.method == 'POST':
        title = request.POST.get('title')
        module_type = request.POST.get('module_type')
        description = request.POST.get('description')
        file = request.FILES.get('file')
        
        Module.objects.create(
            subject=teacher.subject,
            teacher=teacher,
            title=title,
            module_type=module_type,
            file=file,
            description=description
        )
        
        messages.success(request, 'Module uploaded successfully!')
        return redirect('teacher_modules')
    
    return render(request, 'portal/upload_module.html')

@login_required
def teacher_modules(request):
    teacher = request.user.teacher_profile
    modules = Module.objects.filter(teacher=teacher)
    
    return render(request, 'portal/teacher_modules.html', {'modules': modules})

@login_required
def teacher_doubts(request):
    teacher = request.user.teacher_profile
    doubts = teacher.received_doubts.all()
    
    return render(request, 'portal/teacher_doubts.html', {'doubts': doubts})

@login_required
def respond_doubt(request, doubt_id):
    doubt = get_object_or_404(Doubt, id=doubt_id)
    teacher = request.user.teacher_profile
    
    if doubt.teacher != teacher:
        messages.error(request, 'Unauthorized access')
        return redirect('teacher_doubts')
    
    if request.method == 'POST':
        response = request.POST.get('response')
        
        doubt.response = response
        doubt.is_resolved = True
        doubt.resolved_at = timezone.now()
        doubt.save()
        
        messages.success(request, 'Response submitted successfully!')
        return redirect('teacher_doubts')
    
    return render(request, 'portal/respond_doubt.html', {'doubt': doubt})

