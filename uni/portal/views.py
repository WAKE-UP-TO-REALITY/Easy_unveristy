from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date
from .models import User, Student, Teacher, Doctor, Subject, Attendance, Module, Doubt, MedicalLeaveRequest
from .utils import generate_otp, send_otp_via_sms, verify_otp, is_weekend


# Authentication Views
def signup(request):
    """Signup - now supports student, teacher, and doctor"""
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
    """Verify OTP and redirect based on role"""
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
            elif user.role == 'teacher':
                return redirect('teacher_subject_selection', user_id=user.id)
            elif user.role == 'doctor':
                return redirect('doctor_profile_setup', user_id=user.id)
        else:
            messages.error(request, 'Invalid OTP')
    
    return render(request, 'portal/verify_otp.html', {'user': user})


def student_subject_enrollment(request, user_id):
    """Student enrollment"""
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
    """Teacher subject selection"""
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


def doctor_profile_setup(request, user_id):
    """Doctor profile setup - NEW"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        specialization = request.POST.get('specialization')
        
        # Create doctor profile
        Doctor.objects.create(
            user=user,
            employee_id=employee_id,
            specialization=specialization
        )
        
        login(request, user)
        messages.success(request, 'Registration complete! You are set up as a doctor.')
        return redirect('doctor_dashboard')
    
    return render(request, 'portal/doctor_profile_setup.html', {'user': user})


def login_view(request):
    """Login with OTP"""
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
    """Login OTP verification"""
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
            elif user.role == 'teacher':
                return redirect('teacher_dashboard')
            elif user.role == 'doctor':
                return redirect('doctor_dashboard')
        else:
            messages.error(request, 'Invalid OTP')
    
    return render(request, 'portal/login_verify_otp.html')


def logout_view(request):
    """Logout"""
    logout(request)
    return redirect('login')


# Student Dashboard Views
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


# Medical Leave Views - STUDENT
@login_required
def medical_leave_request(request):
    """Student submits medical leave request"""
    student = request.user.student_profile
    
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        symptoms = request.POST.get('symptoms')
        leave_from = request.POST.get('leave_from')
        leave_to = request.POST.get('leave_to')
        
        doctor = get_object_or_404(Doctor, id=doctor_id)
        
        MedicalLeaveRequest.objects.create(
            student=student,
            doctor=doctor,
            symptoms=symptoms,
            leave_from=leave_from,
            leave_to=leave_to
        )
        
        messages.success(request, '✅ Medical leave request submitted successfully!')
        return redirect('student_medical_leaves')
    
    doctors = Doctor.objects.all()
    context = {
        'doctors': doctors,
    }
    return render(request, 'portal/medical_leave_request.html', context)


@login_required
def student_medical_leaves(request):
    """View all medical leave requests with filtering"""
    student = request.user.student_profile
    
    # Get filter status
    status = request.GET.get('status', 'all')
    
    # Filter requests
    if status == 'all':
        medical_leaves = student.medical_leaves.all().order_by('-requested_at')
    else:
        medical_leaves = student.medical_leaves.filter(status=status).order_by('-requested_at')
    
    context = {
        'medical_leaves': medical_leaves,
        'status': status,
    }
    return render(request, 'portal/student_medical_leaves.html', context)



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


# Doctor Dashboard Views
@login_required
def doctor_dashboard(request):
    """Doctor dashboard to manage leave requests"""
    doctor = request.user.doctor_profile
    
    pending_requests = doctor.leave_requests.filter(status='pending').count()
    approved_requests = doctor.leave_requests.filter(status='approved').count()
    
    context = {
        'doctor': doctor,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
    }
    return render(request, 'portal/doctor_dashboard.html', context)


@login_required
def doctor_leave_requests(request):
    """View all leave requests for doctor"""
    doctor = request.user.doctor_profile
    
    # Filter by status if needed
    status = request.GET.get('status', 'all')
    
    if status == 'all':
        leave_requests = doctor.leave_requests.all()
    else:
        leave_requests = doctor.leave_requests.filter(status=status)
    
    context = {
        'leave_requests': leave_requests,
        'status': status,
    }
    return render(request, 'portal/doctor_leave_requests.html', context)


@login_required
def respond_medical_leave(request, leave_id):
    """Doctor can reject immediately OR schedule meeting"""
    leave_request = get_object_or_404(MedicalLeaveRequest, id=leave_id)
    doctor = request.user.doctor_profile
    
    if leave_request.doctor != doctor:
        messages.error(request, '❌ Unauthorized access')
        return redirect('doctor_leave_requests')
    
    if request.method == 'POST':
        action = request.POST.get('action')  # 'reject' or 'schedule'
        
        if action == 'reject':
            # Immediate rejection
            status = 'rejected'
            reason = request.POST.get('reason')
            
            if not reason:
                messages.error(request, '❌ Please provide reason for rejection')
                return render(request, 'portal/respond_medical_leave.html', {'leave_request': leave_request})
            
            leave_request.status = status
            leave_request.doctor_response = reason
            leave_request.responded_at = timezone.now()
            leave_request.save()
            
            messages.success(request, '✅ Leave request rejected!')
            return redirect('doctor_leave_requests')
        
        elif action == 'schedule':
            # Schedule meeting
            meeting_date = request.POST.get('meeting_date')
            meeting_time = request.POST.get('meeting_time')
            meeting_link = request.POST.get('meeting_link')
            
            if not all([meeting_date, meeting_time, meeting_link]):
                messages.error(request, '❌ All meeting fields are required')
                return render(request, 'portal/respond_medical_leave.html', {'leave_request': leave_request})
            
            # Save meeting details
            meeting_datetime = f"{meeting_date} {meeting_time}"
            leave_request.meeting_scheduled_time = datetime.strptime(meeting_datetime, '%Y-%m-%d %H:%M')
            leave_request.meeting_link = meeting_link
            leave_request.save()
            
            messages.success(request, '✅ Meeting scheduled! Now waiting for after-meeting decision.')
            return redirect('finalize_medical_leave', leave_id=leave_id)
    
    return render(request, 'portal/respond_medical_leave.html', {'leave_request': leave_request})


@login_required
def finalize_medical_leave(request, leave_id):
    """After meeting - Doctor approves/rejects with decision"""
    leave_request = get_object_or_404(MedicalLeaveRequest, id=leave_id)
    doctor = request.user.doctor_profile
    
    if leave_request.doctor != doctor:
        messages.error(request, '❌ Unauthorized access')
        return redirect('doctor_leave_requests')
    
    # Check if meeting was scheduled
    if not leave_request.meeting_link:
        messages.error(request, '❌ Please schedule meeting first')
        return redirect('respond_medical_leave', leave_id=leave_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')  # 'approved' or 'rejected'
        doctor_response = request.POST.get('doctor_response')
        
        if not all([status, doctor_response]):
            messages.error(request, '❌ Please fill all fields')
            return render(request, 'portal/finalize_medical_leave.html', {'leave_request': leave_request})
        
        # Finalize decision
        leave_request.status = status
        leave_request.doctor_response = doctor_response
        leave_request.responded_at = timezone.now()
        
        # If approved, add certificate if provided
        if status == 'approved' and 'medical_certificate' in request.FILES:
            leave_request.medical_certificate = request.FILES['medical_certificate']
        
        leave_request.save()
        
        messages.success(request, f'✅ Leave request {status}!')
        return redirect('doctor_leave_requests')
    
    return render(request, 'portal/finalize_medical_leave.html', {'leave_request': leave_request})

