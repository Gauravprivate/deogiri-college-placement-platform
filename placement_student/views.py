from django.shortcuts import render, redirect


import csv

from django.http import HttpResponse

from django.contrib.auth import authenticate, login, logout

from django.contrib.auth.decorators import login_required

from django.views.decorators.http import require_POST

from django.db.models import Q

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone


from .models import (
    Student,
    Job,
    Application,
    Recruiter,
    Resume,
    Notice,
    Notification,
    Interview,
    OnlineTest,
    TestQuestion,
    TestAssignment,
    TestAttempt,
    TestAnswer,
    Feedback,
)

from django.utils import timezone

from datetime import timedelta

def home(request):

    notices = Notice.objects.filter(

        is_active=True

    ).order_by("-notice_date")

    total_students = Student.objects.count()

    total_recruiters = Recruiter.objects.count()

    total_jobs = Job.objects.count()

    selected_students = Application.objects.filter(

        status="Selected"

    ).count()

    return render(

        request,

        "placement_student/home.html",

        {

            "notices": notices,

            "total_students": total_students,

            "total_recruiters": total_recruiters,

            "total_jobs": total_jobs,

            "selected_students": selected_students

        }

    )

# =========================

# STUDENT LOGIN

# =========================

def student_login(request):

    # Student already logged in
    if request.session.get("student_prn"):
        return redirect("dashboard")

    if request.method == "POST":

        prn = request.POST.get("prn", "").strip()
        password = request.POST.get("password", "")

        # Check empty fields
        if not prn or not password:
            return render(
                request,
                "placement_student/student_login.html",
                {
                    "error": "Please enter both PRN and password."
                }
            )

        try:
            student = Student.objects.get(prn=prn)

        except Student.DoesNotExist:
            return render(
                request,
                "placement_student/student_login.html",
                {
                    "error": "Invalid PRN or password."
                }
            )

        # Check student password
        if not student.password or not check_password(
            password,
            student.password
        ):
            return render(
                request,
                "placement_student/student_login.html",
                {
                    "error": "Invalid PRN or password."
                }
            )

        # Login successful
        request.session["student_prn"] = str(student.prn)

        # Rotate session key after successful login
        request.session.cycle_key()

        return redirect("dashboard")

    return render(
        request,
        "placement_student/student_login.html"
    )


def normalize_department(value):

    value = (value or "").strip().lower()

    return "computer science" if value == "cs" else value

def is_student_eligible_for_job(student, job):

    courses = [x.strip().lower() for x in (job.eligible_courses or "").split(",") if x.strip()]

    departments = [normalize_department(x) for x in (job.eligible_departments or "").split(",") if x.strip()]

    return (

        (student.course or "").strip().lower() in courses

        and normalize_department(student.department) in departments

        and student.graduation_year == job.graduation_year

    )

def get_unread_notifications_count(student):

    return Notification.objects.filter(student=student, is_read=False).count()

def get_eligible_jobs(student):

    return [job for job in Job.objects.all() if is_student_eligible_for_job(student, job)]

def dashboard(request):
    prn = request.session.get("student_prn")
    if not prn:
        return redirect("student_login")
    try:
        student = Student.objects.get(prn=prn)
    except Student.DoesNotExist:
        return redirect("student_login")
    create_deadline_notifications(student)
    available_jobs_count = sum(1 for job in get_eligible_jobs(student) if job.is_application_open())
    return render(request, "placement_student/student_profile.html",  {
        "student": student,
        "available_jobs_count": available_jobs_count,
        "applications_count": Application.objects.filter(student=student).count(),
        "notices": Notice.objects.filter(is_active=True).order_by("-notice_date"),
        "unread_notifications_count": get_unread_notifications_count(student),
        "recent_notifications": Notification.objects.filter(student=student).order_by("-created_at")[:5],
    })

def my_profile(request):
    prn = request.session.get("student_prn")

    if not prn:
        return redirect("student_login")

    try:
        student = Student.objects.get(prn=prn)
    except Student.DoesNotExist:
        request.session.pop("student_prn", None)
        return redirect("student_login")

    return render(
        request,
        "placement_student/my_profile.html",
        {
            "student": student,
            "unread_notifications_count": get_unread_notifications_count(student)
        }
    )


@require_POST
def upload_profile_photo(request):
    student = get_logged_in_student(request)

    if not student:
        return redirect("student_login")

    uploaded_photo = request.FILES.get("profile_photo")

    if not uploaded_photo:
        return redirect("my_profile")

    # Maximum file size: 5 MB
    max_size = 5 * 1024 * 1024

    if uploaded_photo.size > max_size:
        return render(
            request,
            "placement_student/my_profile.html",
            {
                "student": student,
                "unread_notifications_count":
                    get_unread_notifications_count(student),
                "photo_error": "Profile photo must be smaller than 5 MB."
            }
        )

    # Allowed image extensions
    allowed_extensions = (".jpg", ".jpeg", ".png")

    if not uploaded_photo.name.lower().endswith(allowed_extensions):
        return render(
            request,
            "placement_student/my_profile.html",
            {
                "student": student,
                "unread_notifications_count":
                    get_unread_notifications_count(student),
                "photo_error": "Only JPG, JPEG and PNG images are allowed."
            }
        )

    # Validate browser supplied content type too
    allowed_content_types = [
        "image/jpeg",
        "image/png"
    ]

    if uploaded_photo.content_type not in allowed_content_types:
        return render(
            request,
            "placement_student/my_profile.html",
            {
                "student": student,
                "unread_notifications_count":
                    get_unread_notifications_count(student),
                "photo_error": "Please upload a valid JPG, JPEG or PNG image."
            }
        )

    # Delete previous profile photo before saving new one
    if student.profile_photo:
        student.profile_photo.delete(save=False)

    student.profile_photo = uploaded_photo
    student.save(update_fields=["profile_photo"])

    return redirect("my_profile")


@require_POST
def remove_profile_photo(request):
    student = get_logged_in_student(request)

    if not student:
        return redirect("student_login")

    if student.profile_photo:
        student.profile_photo.delete(save=False)

        student.profile_photo = None
        student.save(update_fields=["profile_photo"])

    return redirect("my_profile")


def update_student_skills(request):

    prn = request.session.get("student_prn")

    if not prn:

        return redirect("student_login")

    try:

        student = Student.objects.get(prn=prn)

    except Student.DoesNotExist:

        return redirect("student_login")

    if request.method == "POST":

        skills = request.POST.get("skills", "")

        student.skills = skills

        student.save()

        return redirect("my_profile")

    return redirect("my_profile")

def student_notifications(request):

    prn = request.session.get("student_prn")

    if not prn: return redirect("student_login")

    try: student = Student.objects.get(prn=prn)

    except Student.DoesNotExist: return redirect("student_login")

    notifications = Notification.objects.filter(student=student).order_by("-created_at")

    return render(request, "placement_student/student_notifications.html", {"student": student, "notifications": notifications, "unread_count": notifications.filter(is_read=False).count(), "unread_notifications_count": notifications.filter(is_read=False).count()})

@require_POST

def mark_notification_read(request, notification_id):

    prn = request.session.get("student_prn")

    if not prn:

        return redirect("student_login")

    try:

        student = Student.objects.get(prn=prn)

        notification = Notification.objects.get(id=notification_id, student=student)

    except (Student.DoesNotExist, Notification.DoesNotExist):

        return redirect("student_notifications")

    if not notification.is_read:

        notification.is_read = True

        notification.save(update_fields=["is_read"])

    return redirect("student_notifications")

@require_POST

def mark_all_notifications_read(request):

    prn = request.session.get("student_prn")

    if not prn:

        return redirect("student_login")

    try:

        student = Student.objects.get(prn=prn)

    except Student.DoesNotExist:

        return redirect("student_login")

    Notification.objects.filter(student=student, is_read=False).update(is_read=True)

    return redirect("student_notifications")

def create_new_job_notifications(job):

    for student in Student.objects.all():

        if not is_student_eligible_for_job(student, job):

            continue

        Notification.objects.get_or_create(

            student=student, job=job, notification_type="New Job",

            defaults={"title": "New Job Available", "message": f"{job.company_name} has posted a new job: {job.job_title}."}

        )

def create_deadline_notifications(student):

    today = timezone.localdate()

    jobs = Job.objects.filter(application_deadline__gte=today, application_deadline__lte=today + timedelta(days=3))

    applied = set(Application.objects.filter(student=student).values_list("job_id", flat=True))

    for job in jobs:

        if job.id in applied or not is_student_eligible_for_job(student, job):

            continue

        days = (job.application_deadline - today).days

        if days == 0:

            message = f"Applications for {job.job_title} at {job.company_name} close today."

        elif days == 1:

            message = f"Only 1 day left to apply for {job.job_title} at {job.company_name}."

        else:

            message = f"Only {days} days left to apply for {job.job_title} at {job.company_name}."

        Notification.objects.get_or_create(

            student=student, job=job, notification_type="Deadline", message=message,

            defaults={"title": "Application Deadline Reminder"}

        )

def calculate_job_match(student, job):

    student_skills = [

        skill.strip().lower()

        for skill in student.skills.split(",")

        if skill.strip()

    ]

    required_skills = [

        skill.strip().lower()

        for skill in job.required_skills.split(",")

        if skill.strip()

    ]

    if not required_skills:

        return {

            "percentage": 0,

            "matched_skills": [],

            "missing_skills": [],

            "match_label": "Skills Not Specified"

        }

    matched_skills = []

    for skill in required_skills:

        if skill in student_skills:

            matched_skills.append(skill)

    missing_skills = []

    for skill in required_skills:

        if skill not in student_skills:

            missing_skills.append(skill)

    percentage = round(

        (len(matched_skills) / len(required_skills)) * 100

    )

    if percentage >= 80:

        match_label = "Excellent Match"

    elif percentage >= 60:

        match_label = "Good Match"

    elif percentage >= 40:

        match_label = "Moderate Match"

    else:

        match_label = "Low Match"

    return {

        "percentage": percentage,

        "matched_skills": matched_skills,

        "missing_skills": missing_skills,

        "match_label": match_label

    }

def available_jobs(request):

    prn = request.session.get("student_prn")

    if not prn:
        return redirect("student_login")

    try:
        student = Student.objects.get(prn=prn)

    except Student.DoesNotExist:
        request.session.pop("student_prn", None)
        return redirect("student_login")

    # Create deadline notifications
    create_deadline_notifications(student)

    # ---------------------------------
    # SEARCH & FILTER
    # ---------------------------------

    search_query = request.GET.get("search", "").strip()
    location_filter = request.GET.get("location", "").strip()

    jobs = Job.objects.all().order_by("-id")

    # Search by Job Title, Company Name or Required Skills
    if search_query:

        jobs = jobs.filter(
            Q(job_title__icontains=search_query)
            | Q(company_name__icontains=search_query)
            | Q(required_skills__icontains=search_query)
        )

    # Filter by Location
    if location_filter:

        jobs = jobs.filter(
            location__icontains=location_filter
        )

    # ---------------------------------
    # STUDENT APPLICATIONS
    # ---------------------------------

    applied_job_ids = list(
        Application.objects.filter(
            student=student
        ).values_list(
            "job_id",
            flat=True
        )
    )

    eligible_jobs = []

    today = timezone.localdate()

    # ---------------------------------
    # ELIGIBILITY + SMART JOB MATCH
    # ---------------------------------

    for job in jobs:

        match_result = calculate_job_match(student, job)

        job.match_percentage = match_result["percentage"]
        job.match_label = match_result["match_label"]
        job.matched_skills = match_result["matched_skills"]
        job.missing_skills = match_result["missing_skills"]

        job.days_left = (
            (job.application_deadline - today).days
            if job.application_deadline
            else None
        )

        if is_student_eligible_for_job(student, job):
            eligible_jobs.append(job)

    # ---------------------------------
    # PAGE
    # ---------------------------------

    return render(
        request,
        "placement_student/available_jobs.html",
        {
            "jobs": jobs,
            "eligible_jobs": eligible_jobs,
            "applied_job_ids": applied_job_ids,

            "search_query": search_query,
            "location_filter": location_filter,

            "unread_notifications_count":
                get_unread_notifications_count(student),
        }
    )

def apply_job(request, job_id):

    student = get_logged_in_student(request)

    if not student:
        return redirect("student_login")

    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return redirect("available_jobs")

    # Check application deadline
    if not job.is_application_open():
        return redirect("available_jobs")

    # Check student eligibility
    if not is_student_eligible_for_job(student, job):
        return redirect("available_jobs")

    # Prevent duplicate applications
    existing_application = Application.objects.filter(
        student=student,
        job=job
    ).first()

    if existing_application:
        return redirect("available_jobs")

    # Show consent form
    if request.method == "GET":
        return render(
            request,
            "placement_student/application_confirmation.html",
            {
                "student": student,
                "job": job,
            }
        )

    # Submit consent form
    if request.method == "POST":

        willing_to_relocate = request.POST.get(
            "willing_to_relocate"
        ) == "Yes"

        comfortable_with_location = request.POST.get(
            "comfortable_with_location"
        ) == "Yes"

        willing_to_work_shifts = request.POST.get(
            "willing_to_work_shifts"
        ) == "Yes"

        has_active_backlogs = request.POST.get(
            "has_active_backlogs"
        ) == "Yes"

        available_to_join = request.POST.get(
            "available_to_join"
        ) == "Yes"

        declaration_accepted = (
            request.POST.get("declaration_accepted") == "on"
        )

        # Declaration is mandatory
        if not declaration_accepted:
            return render(
                request,
                "placement_student/application_confirmation.html",
                {
                    "student": student,
                    "job": job,
                    "error": "Please accept the declaration before applying.",
                }
            )

        Application.objects.create(
            student=student,
            job=job,
            willing_to_relocate=willing_to_relocate,
            comfortable_with_location=comfortable_with_location,
            willing_to_work_shifts=willing_to_work_shifts,
            has_active_backlogs=has_active_backlogs,
            available_to_join=available_to_join,
            declaration_accepted=declaration_accepted,
            consent_submitted_at=timezone.now(),
        )

        return redirect("available_jobs")

    return redirect("available_jobs")

def my_applications(request):
    prn = request.session.get("student_prn")

    if not prn:
        return redirect("student_login")

    try:
        student = Student.objects.get(prn=prn)
    except Student.DoesNotExist:
        request.session.pop("student_prn", None)
        return redirect("student_login")

    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    applications = Application.objects.filter(
        student=student
    ).select_related("job").order_by("-applied_at")

    if search_query:
        applications = applications.filter(
            Q(job__job_title__icontains=search_query)
            | Q(job__company_name__icontains=search_query)
            | Q(job__location__icontains=search_query)
        )

    if status_filter:
        applications = applications.filter(status=status_filter)

    return render(
        request,
        "placement_student/my_applications.html",
        {
            "applications": applications,
            "search_query": search_query,
            "status_filter": status_filter,
            "result_count": applications.count(),
            "unread_notifications_count": get_unread_notifications_count(student),
        }
    )

def resume(request):
    prn = request.session.get("student_prn")

    if not prn:
        return redirect("student_login")

    try:
        student = Student.objects.get(prn=prn)
    except Student.DoesNotExist:
        request.session.pop("student_prn", None)
        return redirect("student_login")

    resume, created = Resume.objects.get_or_create(
        student=student
    )

    return render(
        request,
        "placement_student/resume.html",
        {
            "student": student,
            "unread_notifications_count": get_unread_notifications_count(student),
            "resume": resume
        }
    )

def edit_resume(request):
    prn = request.session.get("student_prn")

    if not prn:
        return redirect("student_login")

    try:
        student = Student.objects.get(prn=prn)
    except Student.DoesNotExist:
        request.session.pop("student_prn", None)
        return redirect("student_login")

    resume, created = Resume.objects.get_or_create(
        student=student
    )

    if request.method == "POST":
        resume.career_objective = request.POST.get("career_objective")
        resume.technical_skills = request.POST.get("technical_skills")
        resume.projects = request.POST.get("projects")
        resume.certifications = request.POST.get("certifications")
        resume.achievements = request.POST.get("achievements")
        resume.save()

        return redirect("resume")

    return render(
        request,
        "placement_student/edit_resume.html",
        {
            "student": student,
            "unread_notifications_count": get_unread_notifications_count(student),
            "resume": resume
        }
    )

@require_POST
def upload_resume(request):

    student = get_logged_in_student(request)

    if not student:
        return redirect("student_login")

    resume, created = Resume.objects.get_or_create(
        student=student
    )

    uploaded_file = request.FILES.get("uploaded_resume")

    if not uploaded_file:
        return redirect("resume")

    # Maximum file size: 5 MB
    max_size = 5 * 1024 * 1024

    if uploaded_file.size > max_size:
        return render(
            request,
            "placement_student/resume.html",
            {
                "student": student,
                "resume": resume,
                "upload_error": "Resume PDF must be smaller than 5 MB.",
                "unread_notifications_count":
                    get_unread_notifications_count(student),
            }
        )

    # Check file extension
    if not uploaded_file.name.lower().endswith(".pdf"):
        return render(
            request,
            "placement_student/resume.html",
            {
                "student": student,
                "resume": resume,
                "upload_error": "Please upload a PDF file only.",
                "unread_notifications_count":
                    get_unread_notifications_count(student),
            }
        )

    # Check browser reported content type
    if uploaded_file.content_type != "application/pdf":
        return render(
            request,
            "placement_student/resume.html",
            {
                "student": student,
                "resume": resume,
                "upload_error": "Please upload a valid PDF file.",
                "unread_notifications_count":
                    get_unread_notifications_count(student),
            }
        )

    # Check actual PDF file signature
    file_header = uploaded_file.read(5)
    uploaded_file.seek(0)

    if file_header != b"%PDF-":
        return render(
            request,
            "placement_student/resume.html",
            {
                "student": student,
                "resume": resume,
                "upload_error": "The selected file is not a valid PDF.",
                "unread_notifications_count":
                    get_unread_notifications_count(student),
            }
        )

    # Delete previous resume only after new file passes validation
    if resume.uploaded_resume:
        resume.uploaded_resume.delete(save=False)

    resume.uploaded_resume = uploaded_file
    resume.save(update_fields=["uploaded_resume"])

    return redirect("resume")



 
def logout_student(request):

    request.session.flush()

    return redirect("student_login")

# =========================

# RECRUITER REGISTRATION

# =========================

def recruiter_register(request):

    if request.session.get("recruiter_id"):
        return redirect("recruiter_dashboard")

    if request.method == "POST":

        company_name = request.POST.get(
            "company_name", ""
        ).strip()

        recruiter_name = request.POST.get(
            "recruiter_name", ""
        ).strip()

        email = request.POST.get(
            "email", ""
        ).strip().lower()

        password = request.POST.get(
            "password", ""
        )

        company_website = request.POST.get(
            "company_website", ""
        ).strip()

        company_description = request.POST.get(
            "company_description", ""
        ).strip()

        company_address = request.POST.get(
            "company_address", ""
        ).strip()

        company_contact = request.POST.get(
            "company_contact", ""
        ).strip()

        form_data = {
            "company_name": company_name,
            "recruiter_name": recruiter_name,
            "email": email,
            "company_website": company_website,
            "company_description": company_description,
            "company_address": company_address,
            "company_contact": company_contact,
        }

        # Required fields
        if (
            not company_name
            or not recruiter_name
            or not email
            or not password
        ):
            form_data["error"] = (
                "Please fill all required fields."
            )

            return render(
                request,
                "placement_student/recruiter_register.html",
                form_data
            )

        # Minimum password length
        if len(password) < 8:

            form_data["error"] = (
                "Password must contain at least 8 characters."
            )

            return render(
                request,
                "placement_student/recruiter_register.html",
                form_data
            )

        # Duplicate email check
        if Recruiter.objects.filter(
            email__iexact=email
        ).exists():

            form_data["error"] = (
                "A recruiter with this email already exists."
            )

            return render(
                request,
                "placement_student/recruiter_register.html",
                form_data
            )

        # Create recruiter with hashed password
        Recruiter.objects.create(

            company_name=company_name,

            recruiter_name=recruiter_name,

            email=email,

            password=make_password(password),

            company_website=company_website,

            company_description=company_description,

            company_address=company_address,

            company_contact=company_contact,

            verification_status="Pending"
        )

        return render(
            request,
            "placement_student/recruiter_register.html",
            {
                "success": (
                    "Registration submitted successfully. "
                    "Your company is now waiting for "
                    "College Admin verification."
                )
            }
        )

    return render(
        request,
        "placement_student/recruiter_register.html"
    )
# =========================

# RECRUITER LOGIN

# =========================

def recruiter_login(request):

    # Recruiter already logged in
    if request.session.get("recruiter_id"):
        return redirect("recruiter_dashboard")

    if request.method == "POST":

        email = request.POST.get(
            "email", ""
        ).strip().lower()

        password = request.POST.get(
            "password", ""
        )

        # Empty field check
        if not email or not password:

            return render(
                request,
                "placement_student/recruiter_login.html",
                {
                    "error": "Please enter both email and password."
                }
            )

        try:

            recruiter = Recruiter.objects.get(
                email__iexact=email
            )

        except Recruiter.DoesNotExist:

            return render(
                request,
                "placement_student/recruiter_login.html",
                {
                    "error": "Invalid email or password."
                }
            )

        # Check verification status
        if recruiter.verification_status == "Pending":

            return render(
                request,
                "placement_student/recruiter_login.html",
                {
                    "error": (
                        "Your company registration is still pending "
                        "College Admin verification."
                    )
                }
            )

        if recruiter.verification_status == "Rejected":

            return render(
                request,
                "placement_student/recruiter_login.html",
                {
                    "error": (
                        "Your company registration has been rejected "
                        "by the College Admin."
                    )
                }
            )

        # Only approved recruiters can login
        if recruiter.verification_status != "Approved":

            return render(
                request,
                "placement_student/recruiter_login.html",
                {
                    "error": (
                        "Your recruiter account is not approved."
                    )
                }
            )

        # Secure password verification
        if (
            not recruiter.password
            or not check_password(
                password,
                recruiter.password
            )
        ):

            return render(
                request,
                "placement_student/recruiter_login.html",
                {
                    "error": "Invalid email or password."
                }
            )

        # Login successful
        request.session["recruiter_id"] = recruiter.id

        # Rotate session ID after login
        request.session.cycle_key()

        return redirect(
            "recruiter_dashboard"
        )

    return render(
        request,
        "placement_student/recruiter_login.html"
    )

def recruiter_dashboard(request):

    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    jobs = Job.objects.filter(
        recruiter=recruiter
    )

    applications = Application.objects.filter(
        job__recruiter=recruiter
    )

    total_jobs = jobs.count()

    total_applicants = applications.count()

    applied_count = applications.filter(
        status="Applied"
    ).count()

    shortlisted_count = applications.filter(
        status="Shortlisted"
    ).count()

    interview_count = applications.filter(
        status="Interview"
    ).count()

    selected_count = applications.filter(
        status="Selected"
    ).count()

    rejected_count = applications.filter(
        status="Rejected"
    ).count()

    return render(
        request,
        "placement_student/recruiter_dashboard.html",
        {
            "recruiter": recruiter,
            "jobs": jobs,
            "total_jobs": total_jobs,
            "total_applicants": total_applicants,
            "applied_count": applied_count,
            "shortlisted_count": shortlisted_count,
            "interview_count": interview_count,
            "selected_count": selected_count,
            "rejected_count": rejected_count
        }
    )


def parse_future_deadline(deadline_value):

    if not deadline_value:

        return None, "Please select an application deadline."

    try:

        deadline_date = timezone.datetime.strptime(deadline_value, "%Y-%m-%d").date()

    except ValueError:

        return None, "Please select a valid application deadline."

    if deadline_date < timezone.localdate():

        return None, "Application deadline cannot be in the past."

    return deadline_date, None

def post_job(request):

    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    if request.method == "POST":

        deadline_date, deadline_error = parse_future_deadline(
            request.POST.get("application_deadline")
        )

        if deadline_error:
            return render(
                request,
                "placement_student/post_job.html",
                {
                    "recruiter": recruiter,
                    "error": deadline_error
                }
            )

        job = Job.objects.create(
            recruiter=recruiter,
            company_name=recruiter.company_name,
            job_title=request.POST.get("job_title"),
            description=request.POST.get("description"),
            eligible_courses=request.POST.get("eligible_courses"),
            eligible_departments=request.POST.get("eligible_departments"),
            graduation_year=request.POST.get("graduation_year"),
            location=request.POST.get("location"),
            salary=request.POST.get("salary"),
            required_skills=request.POST.get("required_skills"),
            application_deadline=deadline_date
        )

        create_new_job_notifications(job)

        return render(
            request,
            "placement_student/post_job.html",
            {
                "recruiter": recruiter,
                "message": "Job posted successfully!"
            }
        )

    return render(
        request,
        "placement_student/post_job.html",
        {
            "recruiter": recruiter
        }
    )


def my_jobs(request):

    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    jobs = Job.objects.filter(
        recruiter=recruiter
    )

    return render(
        request,
        "placement_student/my_jobs.html",
        {
            "recruiter": recruiter,
            "jobs": jobs
        }
    )

def edit_job(request, job_id):

    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        job = Job.objects.get(
            id=job_id,
            recruiter=recruiter
        )

    except Job.DoesNotExist:
        return redirect("my_jobs")

    if request.method == "POST":

        job.job_title = request.POST.get("job_title")
        job.description = request.POST.get("description")
        job.eligible_courses = request.POST.get("eligible_courses")
        job.eligible_departments = request.POST.get("eligible_departments")
        job.graduation_year = request.POST.get("graduation_year")
        job.location = request.POST.get("location")
        job.salary = request.POST.get("salary")
        job.required_skills = request.POST.get("required_skills")

        deadline_date, deadline_error = parse_future_deadline(
            request.POST.get("application_deadline")
        )

        if deadline_error:
            return render(
                request,
                "placement_student/edit_job.html",
                {
                    "recruiter": recruiter,
                    "job": job,
                    "error": deadline_error
                }
            )

        job.application_deadline = deadline_date
        job.save()

        return redirect("my_jobs")

    return render(
        request,
        "placement_student/edit_job.html",
        {
            "recruiter": recruiter,
            "job": job
        }
    )

@require_POST
def delete_job(request, job_id):

    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        job = Job.objects.get(
            id=job_id,
            recruiter=recruiter
        )

    except Job.DoesNotExist:
        return redirect("my_jobs")

    job.delete()

    return redirect("my_jobs")

def view_applicants(request, job_id):

    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        job = Job.objects.get(
            id=job_id,
            recruiter=recruiter
        )

    except Job.DoesNotExist:
        return redirect("my_jobs")

    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    applications = Application.objects.filter(
        job=job
    ).select_related(
        "student"
    ).order_by(
        "-applied_at"
    )

    if search_query:
        applications = applications.filter(
            Q(student__name__icontains=search_query)
            | Q(student__prn__icontains=search_query)
            | Q(student__email__icontains=search_query)
        )

    if status_filter:
        applications = applications.filter(
            status=status_filter
        )

    return render(
        request,
        "placement_student/view_applicants.html",
        {
            "recruiter": recruiter,
            "job": job,
            "applications": applications,
            "search_query": search_query,
            "status_filter": status_filter,
            "result_count": applications.count(),
        }
    )


def applicant_profile(request, application_id):

    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        application = Application.objects.select_related(
            "student",
            "job"
        ).get(
            id=application_id,
            job__recruiter=recruiter
        )

    except Application.DoesNotExist:
        return redirect("recruiter_dashboard")

    student = application.student

    return render(
        request,
        "placement_student/applicant_profile.html",
        {
            "recruiter": recruiter,
            "application": application,
            "student": student
        }
    )



def applicant_resume(request, application_id):

    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        application = Application.objects.select_related(
            "student",
            "job"
        ).get(
            id=application_id,
            job__recruiter=recruiter
        )

    except Application.DoesNotExist:
        return redirect("recruiter_dashboard")

    student = application.student

    resume, created = Resume.objects.get_or_create(
        student=student
    )

    return render(
        request,
        "placement_student/applicant_resume.html",
        {
            "recruiter": recruiter,
            "application": application,
            "student": student,
            "resume": resume
        }
    )


@require_POST
def update_application_status(request, application_id):

    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        application = Application.objects.select_related(
            "student",
            "job"
        ).get(
            id=application_id,
            job__recruiter=recruiter
        )

    except Application.DoesNotExist:
        return redirect("recruiter_dashboard")

    new_status = request.POST.get("status", "").strip()

    valid_statuses = [
        "Applied",
        "Shortlisted",
        "Interview",
        "Selected",
        "Rejected"
    ]

    # Reject invalid or manipulated status values
    if new_status not in valid_statuses:
        return redirect(
            "view_applicants",
            job_id=application.job.id
        )

    old_status = application.status

    # Update only when status actually changes
    if old_status != new_status:

        application.status = new_status
        application.save(update_fields=["status"])

        Notification.objects.create(
            student=application.student,
            title="Application Status Updated",
            message=(
                f"Your application for "
                f"{application.job.job_title} at "
                f"{application.job.company_name} "
                f"has been updated from "
                f"{old_status} to {new_status}."
            ),
            notification_type="Status Update",
            job=application.job
        )

    return redirect(
        "view_applicants",
        job_id=application.job.id
    )

# =========================
# INTERVIEW SCHEDULING
# =========================

def get_logged_in_recruiter(request):
    recruiter_id = request.session.get("recruiter_id")

    if not recruiter_id:
        return None

    try:
        recruiter = Recruiter.objects.get(
            id=recruiter_id,
            verification_status="Approved"
        )
        return recruiter

    except Recruiter.DoesNotExist:
        # Remove invalid/stale recruiter session
        request.session.pop("recruiter_id", None)
        return None

def parse_interview_datetime(date_value, time_value):
    if not date_value or not time_value:
        return None, None, "Please select both interview date and time."
    try:
        interview_date = timezone.datetime.strptime(date_value, "%Y-%m-%d").date()
        interview_time = timezone.datetime.strptime(time_value, "%H:%M").time()
    except ValueError:
        return None, None, "Please enter a valid interview date and time."
    interview_datetime = timezone.make_aware(
        timezone.datetime.combine(interview_date, interview_time),
        timezone.get_current_timezone()
    )
    if interview_datetime <= timezone.localtime():
        return None, None, "Interview date and time must be in the future."
    return interview_date, interview_time, None

def schedule_interview(request, application_id):
    recruiter = get_logged_in_recruiter(request)
    if not recruiter:
        return redirect("recruiter_login")
    try:
        application = Application.objects.select_related("student", "job").get(
            id=application_id,
            job__recruiter=recruiter
        )
    except Application.DoesNotExist:
        return redirect("recruiter_dashboard")
    if hasattr(application, "interview"):
        return redirect("edit_interview", interview_id=application.interview.id)
    if application.status not in ["Shortlisted", "Interview"]:
        return redirect("view_applicants", job_id=application.job.id)

    if request.method == "POST":
        date_value = request.POST.get("interview_date", "").strip()
        time_value = request.POST.get("interview_time", "").strip()
        mode = request.POST.get("mode", "").strip()
        venue = request.POST.get("venue", "").strip()
        meeting_link = request.POST.get("meeting_link", "").strip()
        instructions = request.POST.get("instructions", "").strip()
        interview_date, interview_time, error = parse_interview_datetime(date_value, time_value)

        if not error and mode not in ["Online", "Offline"]:
            error = "Please select a valid interview mode."
        if not error and mode == "Online" and not meeting_link:
            error = "Meeting link is required for an online interview."
        if not error and mode == "Offline" and not venue:
            error = "Venue is required for an offline interview."

        if error:
            return render(request, "placement_student/schedule_interview.html", {
                "recruiter": recruiter,
                "application": application,
                "error": error,
                "form_data": request.POST
            })

        interview = Interview.objects.create(
            application=application,
            interview_date=interview_date,
            interview_time=interview_time,
            mode=mode,
            venue=venue if mode == "Offline" else "",
            meeting_link=meeting_link if mode == "Online" else "",
            instructions=instructions,
            status="Scheduled"
        )

        old_status = application.status
        application.status = "Interview"
        application.save(update_fields=["status"])

        if old_status != "Interview":
            Notification.objects.create(
                student=application.student,
                title="Application Status Updated",
                message=f"Your application for {application.job.job_title} at {application.job.company_name} has been updated from {old_status} to Interview.",
                notification_type="Status Update",
                job=application.job
            )

        detail = (
            f"Meeting link: {interview.meeting_link}"
            if interview.mode == "Online"
            else f"Venue: {interview.venue}"
        )
        Notification.objects.create(
            student=application.student,
            title="Interview Scheduled",
            message=f"Your interview for {application.job.job_title} at {application.job.company_name} is scheduled on {interview.interview_date.strftime('%d %b %Y')} at {interview.interview_time.strftime('%I:%M %p')}. Mode: {interview.mode}. {detail}",
            notification_type="Interview",
            job=application.job
        )
        return redirect("view_applicants", job_id=application.job.id)

    return render(request, "placement_student/schedule_interview.html", {
        "recruiter": recruiter,
        "application": application
    })

def edit_interview(request, interview_id):
    recruiter = get_logged_in_recruiter(request)
    if not recruiter:
        return redirect("recruiter_login")
    try:
        interview = Interview.objects.select_related(
            "application__student",
            "application__job"
        ).get(
            id=interview_id,
            application__job__recruiter=recruiter
        )
    except Interview.DoesNotExist:
        return redirect("recruiter_interviews")

    application = interview.application
    if interview.status == "Completed":
        return redirect("recruiter_interviews")

    if request.method == "POST":
        date_value = request.POST.get("interview_date", "").strip()
        time_value = request.POST.get("interview_time", "").strip()
        mode = request.POST.get("mode", "").strip()
        venue = request.POST.get("venue", "").strip()
        meeting_link = request.POST.get("meeting_link", "").strip()
        instructions = request.POST.get("instructions", "").strip()
        interview_date, interview_time, error = parse_interview_datetime(date_value, time_value)

        if not error and mode not in ["Online", "Offline"]:
            error = "Please select a valid interview mode."
        if not error and mode == "Online" and not meeting_link:
            error = "Meeting link is required for an online interview."
        if not error and mode == "Offline" and not venue:
            error = "Venue is required for an offline interview."

        if error:
            return render(request, "placement_student/edit_interview.html", {
                "recruiter": recruiter,
                "interview": interview,
                "application": application,
                "error": error,
                "form_data": request.POST
            })

        interview.interview_date = interview_date
        interview.interview_time = interview_time
        interview.mode = mode
        interview.venue = venue if mode == "Offline" else ""
        interview.meeting_link = meeting_link if mode == "Online" else ""
        interview.instructions = instructions
        interview.status = "Scheduled"
        interview.save()

        if application.status != "Interview":
            application.status = "Interview"
            application.save(update_fields=["status"])

        detail = (
            f"Meeting link: {interview.meeting_link}"
            if interview.mode == "Online"
            else f"Venue: {interview.venue}"
        )
        Notification.objects.create(
            student=application.student,
            title="Interview Rescheduled",
            message=f"Your interview for {application.job.job_title} at {application.job.company_name} has been rescheduled to {interview.interview_date.strftime('%d %b %Y')} at {interview.interview_time.strftime('%I:%M %p')}. Mode: {interview.mode}. {detail}",
            notification_type="Interview",
            job=application.job
        )
        return redirect("recruiter_interviews")

    return render(request, "placement_student/edit_interview.html", {
        "recruiter": recruiter,
        "interview": interview,
        "application": application
    })

@require_POST
def cancel_interview(request, interview_id):
    recruiter = get_logged_in_recruiter(request)
    if not recruiter:
        return redirect("recruiter_login")
    try:
        interview = Interview.objects.select_related(
            "application__student",
            "application__job"
        ).get(
            id=interview_id,
            application__job__recruiter=recruiter
        )
    except Interview.DoesNotExist:
        return redirect("recruiter_interviews")

    if interview.status != "Cancelled":
        interview.status = "Cancelled"
        interview.save(update_fields=["status", "updated_at"])
        application = interview.application
        if application.status == "Interview":
            application.status = "Shortlisted"
            application.save(update_fields=["status"])
        Notification.objects.create(
            student=application.student,
            title="Interview Cancelled",
            message=f"Your interview for {application.job.job_title} at {application.job.company_name} has been cancelled. Please check your placement portal for further updates.",
            notification_type="Interview",
            job=application.job
        )
    return redirect("recruiter_interviews")

@require_POST
def complete_interview(request, interview_id):
    recruiter = get_logged_in_recruiter(request)
    if not recruiter:
        return redirect("recruiter_login")
    try:
        interview = Interview.objects.get(
            id=interview_id,
            application__job__recruiter=recruiter
        )
    except Interview.DoesNotExist:
        return redirect("recruiter_interviews")

    if interview.status == "Scheduled":
        interview.status = "Completed"
        interview.save(update_fields=["status", "updated_at"])
    return redirect("recruiter_interviews")

def recruiter_interviews(request):
    recruiter = get_logged_in_recruiter(request)
    if not recruiter:
        return redirect("recruiter_login")

    interviews = Interview.objects.filter(
        application__job__recruiter=recruiter
    ).select_related(
        "application__student",
        "application__job"
    ).order_by("interview_date", "interview_time")

    today = timezone.localdate()
    return render(request, "placement_student/recruiter_interviews.html", {
        "recruiter": recruiter,
        "interviews": interviews,
        "upcoming_count": interviews.filter(
            status="Scheduled",
            interview_date__gte=today
        ).count(),
        "completed_count": interviews.filter(status="Completed").count(),
        "cancelled_count": interviews.filter(status="Cancelled").count()
    })




def student_interviews(request):
    student = get_logged_in_student(request)

    if not student:
        return redirect("student_login")

    interviews = Interview.objects.filter(
        application__student=student
    ).select_related(
        "application__job"
    ).order_by("interview_date", "interview_time")

    today = timezone.localdate()

    return render(
        request,
        "placement_student/student_interviews.html",
        {
            "student": student,
            "interviews": interviews,
            "upcoming_count": interviews.filter(
                status="Scheduled",
                interview_date__gte=today
            ).count(),
            "completed_count": interviews.filter(
                status="Completed"
            ).count(),
            "cancelled_count": interviews.filter(
                status="Cancelled"
            ).count(),
            "unread_notifications_count":
                get_unread_notifications_count(student),
        }
    )
@login_required
def manage_interviews(request):
    if not request.user.is_staff:
        return redirect("admin_dashboard")

    interviews = Interview.objects.select_related(
        "application__student",
        "application__job",
        "application__job__recruiter"
    ).order_by("interview_date", "interview_time")

    today = timezone.localdate()
    return render(request, "placement_student/manage_interviews.html", {
        "interviews": interviews,
        "total_interviews": interviews.count(),
        "scheduled_count": interviews.filter(status="Scheduled").count(),
        "upcoming_count": interviews.filter(
            status="Scheduled",
            interview_date__gte=today
        ).count(),
        "completed_count": interviews.filter(status="Completed").count(),
        "cancelled_count": interviews.filter(status="Cancelled").count()
    })

def recruiter_logout(request):

    request.session.flush()

    return redirect(

        "recruiter_login"

    )

# =========================

# COLLEGE ADMIN LOGIN

# =========================

def college_admin_login(request):

    if request.user.is_authenticated:

        if request.user.is_staff:
            return redirect("admin_dashboard")

        logout(request)

    if request.method == "POST":

        username = request.POST.get(

            "username"

        )

        password = request.POST.get(

            "password"

        )

        user = authenticate(

            request,

            username=username,

            password=password

        )

        if user is not None and user.is_staff:

            login(

                request,

                user

            )

            return redirect(

                "admin_dashboard"

            )

        return render(

            request,

            "placement_student/college_admin_login.html",

            {

                "error": "Invalid admin username or password."

            }

        )

    return render(

        request,

        "placement_student/college_admin_login.html"

    )

# =========================

# COLLEGE ADMIN LOGOUT

# =========================

def college_admin_logout(request):

    logout(request)

    return redirect(

        "college_admin_login"

    )

# =========================

# COLLEGE ADMIN DASHBOARD

# =========================

@login_required

def admin_dashboard(request):

    if not request.user.is_staff:
        return redirect("college_admin_login")

    total_students = Student.objects.count()

    total_recruiters = Recruiter.objects.count()

    total_jobs = Job.objects.count()

    total_applications = Application.objects.count()

    applied_count = Application.objects.filter(

        status="Applied"

    ).count()

    shortlisted_count = Application.objects.filter(

        status="Shortlisted"

    ).count()

    interview_count = Application.objects.filter(

        status="Interview"

    ).count()

    selected_count = Application.objects.filter(

        status="Selected"

    ).count()

    rejected_count = Application.objects.filter(

        status="Rejected"

    ).count()

    recent_jobs = Job.objects.order_by(

        "-id"

    )[:5]

    recent_applications = Application.objects.order_by(

        "-applied_at"

    )[:5]

    return render(

        request,

        "placement_student/admin_dashboard.html",

        {

            "total_students": total_students,

            "total_recruiters": total_recruiters,

            "total_jobs": total_jobs,

            "total_applications": total_applications,

            "applied_count": applied_count,

            "shortlisted_count": shortlisted_count,

            "interview_count": interview_count,

            "selected_count": selected_count,

            "rejected_count": rejected_count,

            "recent_jobs": recent_jobs,

            "recent_applications": recent_applications

        }

    )

# =========================

# MANAGE STUDENTS

# =========================

@login_required
def manage_students(request):
    if not request.user.is_staff:
        return redirect("admin_dashboard")

    search_query = request.GET.get("search", "").strip()
    course_filter = request.GET.get("course", "").strip()
    department_filter = request.GET.get("department", "").strip()

    students = Student.objects.all().order_by("prn")

    if search_query:
        students = students.filter(
            Q(prn__icontains=search_query)
            | Q(name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone__icontains=search_query)
        )

    if course_filter:
        students = students.filter(course__icontains=course_filter)

    if department_filter:
        students = students.filter(department__icontains=department_filter)

    return render(
        request,
        "placement_student/manage_students.html",
        {
            "students": students,
            "search_query": search_query,
            "course_filter": course_filter,
            "department_filter": department_filter,
            "result_count": students.count(),
        }
    )

@login_required
def manage_recruiters(request):
    if not request.user.is_staff:
        return redirect("admin_dashboard")

    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    recruiters = Recruiter.objects.all().order_by("company_name")

    if search_query:
        recruiters = recruiters.filter(
            Q(company_name__icontains=search_query)
            | Q(recruiter_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    if status_filter:
        recruiters = recruiters.filter(verification_status=status_filter)

    return render(
        request,
        "placement_student/manage_recruiters.html",
        {
            "recruiters": recruiters,
            "search_query": search_query,
            "status_filter": status_filter,
            "result_count": recruiters.count(),
        }
    )

@login_required
@require_POST

def approve_recruiter(request, recruiter_id):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    try:

        recruiter = Recruiter.objects.get(

            id=recruiter_id

        )

    except Recruiter.DoesNotExist:

        return redirect("manage_recruiters")

    if request.method == "POST":

        recruiter.verification_status = "Approved"

        recruiter.save()

    return redirect("manage_recruiters")

# =========================

# REJECT RECRUITER

# =========================

@login_required
@require_POST

def reject_recruiter(request, recruiter_id):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    try:

        recruiter = Recruiter.objects.get(

            id=recruiter_id

        )

    except Recruiter.DoesNotExist:

        return redirect("manage_recruiters")

    if request.method == "POST":

        recruiter.verification_status = "Rejected"

        recruiter.save()

    return redirect("manage_recruiters")

@login_required
def edit_recruiter(request, recruiter_id):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    try:

        recruiter = Recruiter.objects.get(
            id=recruiter_id
        )

    except Recruiter.DoesNotExist:

        return redirect("manage_recruiters")

    if request.method == "POST":

        company_name = request.POST.get(
            "company_name", ""
        ).strip()

        recruiter_name = request.POST.get(
            "recruiter_name", ""
        ).strip()

        email = request.POST.get(
            "email", ""
        ).strip().lower()

        new_password = request.POST.get(
            "password", ""
        )

        # Required field validation
        if (
            not company_name
            or not recruiter_name
            or not email
        ):

            return render(
                request,
                "placement_student/edit_recruiter.html",
                {
                    "recruiter": recruiter,
                    "error": "Please fill all required fields."
                }
            )

        # Duplicate email check
        if Recruiter.objects.filter(
            email__iexact=email
        ).exclude(
            id=recruiter.id
        ).exists():

            return render(
                request,
                "placement_student/edit_recruiter.html",
                {
                    "recruiter": recruiter,
                    "error": (
                        "Another recruiter already uses this email."
                    )
                }
            )

        # Validate password only if admin enters a new one
        if new_password and len(new_password) < 8:

            return render(
                request,
                "placement_student/edit_recruiter.html",
                {
                    "recruiter": recruiter,
                    "error": (
                        "Password must contain at least 8 characters."
                    )
                }
            )

        recruiter.company_name = company_name
        recruiter.recruiter_name = recruiter_name
        recruiter.email = email

        # Reset password only when admin enters one
        if new_password:
            recruiter.password = make_password(
                new_password
            )

        recruiter.save()

        return redirect(
            "manage_recruiters"
        )

    return render(
        request,
        "placement_student/edit_recruiter.html",
        {
            "recruiter": recruiter
        }
    )

@login_required
@require_POST

def delete_recruiter(request, recruiter_id):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    try:

        recruiter = Recruiter.objects.get(id=recruiter_id)

    except Recruiter.DoesNotExist:

        return redirect("manage_recruiters")

    if request.method == "POST":

        recruiter.delete()

        return redirect("manage_recruiters")

    return redirect("manage_recruiters")

@login_required
def add_recruiter(request):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    if request.method == "POST":

        company_name = request.POST.get(
            "company_name", ""
        ).strip()

        recruiter_name = request.POST.get(
            "recruiter_name", ""
        ).strip()

        email = request.POST.get(
            "email", ""
        ).strip().lower()

        password = request.POST.get(
            "password", ""
        )

        # Required fields
        if (
            not company_name
            or not recruiter_name
            or not email
            or not password
        ):

            return render(
                request,
                "placement_student/add_recruiter.html",
                {
                    "error": "Please fill all required fields."
                }
            )

        # Password validation
        if len(password) < 8:

            return render(
                request,
                "placement_student/add_recruiter.html",
                {
                    "error": (
                        "Password must contain at least 8 characters."
                    )
                }
            )

        # Duplicate email check
        if Recruiter.objects.filter(
            email__iexact=email
        ).exists():

            return render(
                request,
                "placement_student/add_recruiter.html",
                {
                    "error": (
                        "A recruiter with this email already exists."
                    )
                }
            )

        # Admin-created recruiter
        Recruiter.objects.create(

            company_name=company_name,

            recruiter_name=recruiter_name,

            email=email,

            password=make_password(password),

            verification_status="Approved"
        )

        return redirect(
            "manage_recruiters"
        )

    return render(
        request,
        "placement_student/add_recruiter.html"
    )


@login_required
def manage_jobs(request):
    if not request.user.is_staff:
        return redirect("admin_dashboard")

    search_query = request.GET.get("search", "").strip()
    location_filter = request.GET.get("location", "").strip()

    jobs = Job.objects.all().select_related("recruiter").order_by("-id")

    if search_query:
        jobs = jobs.filter(
            Q(job_title__icontains=search_query)
            | Q(company_name__icontains=search_query)
            | Q(required_skills__icontains=search_query)
        )

    if location_filter:
        jobs = jobs.filter(location__icontains=location_filter)

    return render(
        request,
        "placement_student/manage_jobs.html",
        {
            "jobs": jobs,
            "search_query": search_query,
            "location_filter": location_filter,
            "result_count": jobs.count(),
        }
    )

@login_required

def add_admin_job(request):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    recruiters = Recruiter.objects.filter(verification_status="Approved").order_by("company_name")

    if request.method == "POST":

        try:

            recruiter = Recruiter.objects.get(id=request.POST.get("recruiter"), verification_status="Approved")

        except Recruiter.DoesNotExist:

            return redirect("manage_jobs")

        deadline_date, deadline_error = parse_future_deadline(request.POST.get("application_deadline"))

        if deadline_error:

            return render(request, "placement_student/add_admin_job.html", {"recruiters": recruiters, "error": deadline_error})

        job = Job.objects.create(

            recruiter=recruiter, company_name=recruiter.company_name,

            job_title=request.POST.get("job_title"), description=request.POST.get("description"),

            eligible_courses=request.POST.get("eligible_courses"), eligible_departments=request.POST.get("eligible_departments"),

            graduation_year=request.POST.get("graduation_year"), location=request.POST.get("location"),

            salary=request.POST.get("salary"), required_skills=request.POST.get("required_skills"),

            application_deadline=deadline_date

        )

        create_new_job_notifications(job)

        return redirect("manage_jobs")

    return render(request, "placement_student/add_admin_job.html", {"recruiters": recruiters})

@login_required

@login_required

def edit_admin_job(request, job_id):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    try:

        job = Job.objects.get(id=job_id)

    except Job.DoesNotExist:

        return redirect("manage_jobs")

    recruiters = Recruiter.objects.filter(

        verification_status="Approved"

    ).order_by("company_name")

    if request.method == "POST":

        recruiter_id = request.POST.get("recruiter")

        try:

            recruiter = Recruiter.objects.get(

                id=recruiter_id,

                verification_status="Approved"

            )

        except Recruiter.DoesNotExist:

            return redirect("manage_jobs")

        job.recruiter = recruiter

        job.company_name = recruiter.company_name

        job.job_title = request.POST.get(

            "job_title"

        )

        job.description = request.POST.get(

            "description"

        )

        job.eligible_courses = request.POST.get(

            "eligible_courses"

        )

        job.eligible_departments = request.POST.get(

            "eligible_departments"

        )

        job.graduation_year = request.POST.get(

            "graduation_year"

        )

        job.location = request.POST.get(

            "location"

        )

        job.salary = request.POST.get(

            "salary"

        )

        job.required_skills = request.POST.get("required_skills")

        deadline_date, deadline_error = parse_future_deadline(request.POST.get("application_deadline"))

        if deadline_error:

            return render(request, "placement_student/edit_admin_job.html", {"job": job, "recruiters": recruiters, "error": deadline_error})

        job.application_deadline = deadline_date

        job.save()

        return redirect("manage_jobs")

    return render(

        request,

        "placement_student/edit_admin_job.html",

        {

            "job": job,

            "recruiters": recruiters

        }

    )

@login_required
@require_POST

def delete_admin_job(request, job_id):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    try:

        job = Job.objects.get(id=job_id)

    except Job.DoesNotExist:

        return redirect("manage_jobs")

    if request.method == "POST":

        job.delete()

    return redirect("manage_jobs")

@login_required
def admin_job_applicants(request, job_id):
    if not request.user.is_staff:
        return redirect("admin_dashboard")

    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return redirect("manage_jobs")

    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    applications = Application.objects.filter(
        job=job
    ).select_related("student").order_by("-applied_at")

    if search_query:
        applications = applications.filter(
            Q(student__name__icontains=search_query)
            | Q(student__prn__icontains=search_query)
            | Q(student__email__icontains=search_query)
        )

    if status_filter:
        applications = applications.filter(status=status_filter)

    return render(
        request,
        "placement_student/admin_job_applicants.html",
        {
            "job": job,
            "applications": applications,
            "search_query": search_query,
            "status_filter": status_filter,
            "result_count": applications.count(),
        }
    )

@login_required

def manage_notices(request):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    notices = Notice.objects.all().order_by("-notice_date")

    return render(

        request,

        "placement_student/manage_notices.html",

        {

            "notices": notices

        }

    )

@login_required

def add_notice(request):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    if request.method == "POST":

        title = request.POST.get("title")

        description = request.POST.get("description")

        is_active = request.POST.get("is_active") == "on"

        Notice.objects.create(

            title=title,

            description=description,

            is_active=is_active

        )

        return redirect("manage_notices")

    return render(

        request,

        "placement_student/add_notice.html"

    )

@login_required

def edit_notice(request, notice_id):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    try:

        notice = Notice.objects.get(id=notice_id)

    except Notice.DoesNotExist:

        return redirect("manage_notices")

    if request.method == "POST":

        notice.title = request.POST.get(

            "title"

        )

        notice.description = request.POST.get(

            "description"

        )

        notice.is_active = request.POST.get(

            "is_active"

        ) == "on"

        notice.save()

        return redirect("manage_notices")

    return render(

        request,

        "placement_student/edit_notice.html",

        {

            "notice": notice

        }

    )

@login_required
@require_POST

def delete_notice(request, notice_id):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    try:

        notice = Notice.objects.get(id=notice_id)

    except Notice.DoesNotExist:

        return redirect("manage_notices")

    if request.method == "POST":

        notice.delete()

    return redirect("manage_notices")

@login_required
@require_POST

def toggle_notice(request, notice_id):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    try:

        notice = Notice.objects.get(id=notice_id)

    except Notice.DoesNotExist:

        return redirect("manage_notices")

    notice.is_active = not notice.is_active

    notice.save()

    return redirect("manage_notices")

# =========================

# EDIT STUDENT

# =========================

@login_required
def edit_student(request, student_id):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    try:
        student = Student.objects.get(id=student_id)

    except Student.DoesNotExist:
        return redirect("manage_students")

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        course = request.POST.get("course", "").strip()
        department = request.POST.get("department", "").strip()
        phone = request.POST.get("phone", "").strip()
        new_password = request.POST.get("password", "")

        # Check required student information
        if (
            not name
            or not email
            or not course
            or not department
            or not phone
        ):
            return render(
                request,
                "placement_student/edit_student.html",
                {
                    "student": student,
                    "error": "Please fill all required fields."
                }
            )

        # Check whether another student already uses this email
        if Student.objects.filter(
            email=email
        ).exclude(
            id=student.id
        ).exists():

            return render(
                request,
                "placement_student/edit_student.html",
                {
                    "student": student,
                    "error": "Another student already uses this email."
                }
            )

        # Validate new password only if admin entered one
        if new_password and len(new_password) < 8:

            return render(
                request,
                "placement_student/edit_student.html",
                {
                    "student": student,
                    "error": "Password must contain at least 8 characters."
                }
            )

        # Update student information
        student.name = name
        student.email = email
        student.course = course
        student.department = department
        student.phone = phone

        # Reset password only when admin enters a new password
        if new_password:
            student.password = make_password(new_password)

        student.save()

        return redirect("manage_students")

    return render(
        request,
        "placement_student/edit_student.html",
        {
            "student": student
        }
    )

# =========================

# DELETE STUDENT

# =========================

@login_required
@require_POST

def delete_student(request, student_id):

    if not request.user.is_staff:

        return redirect("admin_dashboard")

    try:

        student = Student.objects.get(id=student_id)

    except Student.DoesNotExist:

        return redirect("manage_students")

    if request.method == "POST":

        student.delete()

        return redirect("manage_students")

        return redirect("manage_students")

# =========================

# ADD STUDENT

# =========================

@login_required
def add_student(request):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    if request.method == "POST":

        prn = request.POST.get("prn", "").strip()
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        course = request.POST.get("course", "").strip()
        department = request.POST.get("department", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")

        # Check required fields
        if (
            not prn
            or not name
            or not email
            or not course
            or not department
            or not phone
            or not password
        ):
            return render(
                request,
                "placement_student/add_student.html",
                {
                    "error": "Please fill all required fields."
                }
            )

        # Check duplicate PRN
        if Student.objects.filter(prn=prn).exists():
            return render(
                request,
                "placement_student/add_student.html",
                {
                    "error": "A student with this PRN already exists."
                }
            )

        # Check duplicate email
        if Student.objects.filter(email=email).exists():
            return render(
                request,
                "placement_student/add_student.html",
                {
                    "error": "A student with this email already exists."
                }
            )

        # Minimum password security
        if len(password) < 8:
            return render(
                request,
                "placement_student/add_student.html",
                {
                    "error": "Password must contain at least 8 characters."
                }
            )

        Student.objects.create(
            prn=prn,
            name=name,
            email=email,
            course=course,
            department=department,
            phone=phone,

            # Store hashed password, never plain text
            password=make_password(password)
        )

        return redirect("manage_students")

    return render(
        request,
        "placement_student/add_student.html"
    )

# =========================
# ONLINE TEST MODULE
# =========================

def get_logged_in_student(request):
    prn = request.session.get("student_prn")

    if not prn:
        return None

    try:
        student = Student.objects.get(prn=prn)
        return student

    except Student.DoesNotExist:
        # Remove invalid/stale student session
        request.session.pop("student_prn", None)
        return None

def parse_test_deadline(deadline_value):
    if not deadline_value:
        return None, "Please select a test deadline."

    try:
        deadline = timezone.datetime.strptime(
            deadline_value,
            "%Y-%m-%dT%H:%M"
        )

        deadline = timezone.make_aware(
            deadline,
            timezone.get_current_timezone()
        )

    except ValueError:
        return None, "Please enter a valid test deadline."

    if deadline <= timezone.now():
        return None, "Test deadline must be in the future."

    return deadline, None

# =========================
# RECRUITER - TEST LIST
# =========================

def recruiter_tests(request):
    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    tests = OnlineTest.objects.filter(
        recruiter=recruiter
    ).select_related(
        "job"
    ).order_by("-created_at")

    return render(
        request,
        "placement_student/recruiter_tests.html",
        {
            "recruiter": recruiter,
            "tests": tests,
            "total_tests": tests.count(),
            "active_tests": tests.filter(
                is_active=True
            ).count(),
        }
    )

# =========================
# RECRUITER - CREATE TEST
# =========================

def create_online_test(request):
    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    jobs = Job.objects.filter(
        recruiter=recruiter
    ).order_by("-id")

    if request.method == "POST":

        job_id = request.POST.get("job")
        title = request.POST.get("title", "").strip()
        test_type = request.POST.get(
            "test_type",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        instructions = request.POST.get(
            "instructions",
            ""
        ).strip()

        duration_value = request.POST.get(
            "duration_minutes",
            ""
        ).strip()

        passing_value = request.POST.get(
            "passing_percentage",
            ""
        ).strip()

        deadline_value = request.POST.get(
            "test_deadline",
            ""
        ).strip()

        error = None

        try:
            job = Job.objects.get(
                id=job_id,
                recruiter=recruiter
            )
        except Job.DoesNotExist:
            job = None
            error = "Please select a valid job."

        if not title:
            error = error or "Test title is required."

        if test_type not in [
            "Aptitude",
            "Technical",
            "Mixed"
        ]:
            error = error or "Please select a valid test type."

        try:
            duration_minutes = int(duration_value)

            if duration_minutes <= 0:
                raise ValueError

        except (TypeError, ValueError):
            duration_minutes = None
            error = error or (
                "Duration must be greater than 0 minutes."
            )

        try:
            passing_percentage = int(passing_value)

            if (
                passing_percentage < 0
                or passing_percentage > 100
            ):
                raise ValueError

        except (TypeError, ValueError):
            passing_percentage = None
            error = error or (
                "Passing percentage must be between 0 and 100."
            )

        deadline, deadline_error = parse_test_deadline(
            deadline_value
        )

        if deadline_error:
            error = error or deadline_error

        if error:
            return render(
                request,
                "placement_student/create_online_test.html",
                {
                    "recruiter": recruiter,
                    "jobs": jobs,
                    "error": error,
                    "form_data": request.POST,
                }
            )

        online_test = OnlineTest.objects.create(
            recruiter=recruiter,
            job=job,
            title=title,
            test_type=test_type,
            description=description,
            instructions=instructions,
            duration_minutes=duration_minutes,
            passing_percentage=passing_percentage,
            test_deadline=deadline,
            is_active=True,
        )

        return redirect(
            "manage_test_questions",
            test_id=online_test.id
        )

    return render(
        request,
        "placement_student/create_online_test.html",
        {
            "recruiter": recruiter,
            "jobs": jobs,
        }
    )

# =========================
# RECRUITER - EDIT TEST
# =========================

def edit_online_test(request, test_id):
    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        online_test = OnlineTest.objects.get(
            id=test_id,
            recruiter=recruiter
        )
    except OnlineTest.DoesNotExist:
        return redirect("recruiter_tests")

    jobs = Job.objects.filter(
        recruiter=recruiter
    ).order_by("-id")

    if request.method == "POST":

        job_id = request.POST.get("job")
        title = request.POST.get("title", "").strip()
        test_type = request.POST.get(
            "test_type",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        instructions = request.POST.get(
            "instructions",
            ""
        ).strip()

        duration_value = request.POST.get(
            "duration_minutes",
            ""
        ).strip()

        passing_value = request.POST.get(
            "passing_percentage",
            ""
        ).strip()

        deadline_value = request.POST.get(
            "test_deadline",
            ""
        ).strip()

        is_active = (
            request.POST.get("is_active") == "on"
        )

        error = None

        try:
            job = Job.objects.get(
                id=job_id,
                recruiter=recruiter
            )
        except Job.DoesNotExist:
            job = None
            error = "Please select a valid job."

        if not title:
            error = error or "Test title is required."

        if test_type not in [
            "Aptitude",
            "Technical",
            "Mixed"
        ]:
            error = error or "Please select a valid test type."

        try:
            duration_minutes = int(duration_value)

            if duration_minutes <= 0:
                raise ValueError

        except (TypeError, ValueError):
            duration_minutes = None
            error = error or (
                "Duration must be greater than 0 minutes."
            )

        try:
            passing_percentage = int(passing_value)

            if (
                passing_percentage < 0
                or passing_percentage > 100
            ):
                raise ValueError

        except (TypeError, ValueError):
            passing_percentage = None
            error = error or (
                "Passing percentage must be between 0 and 100."
            )

        deadline, deadline_error = parse_test_deadline(
            deadline_value
        )

        if deadline_error:
            error = error or deadline_error

        if error:
            return render(
                request,
                "placement_student/edit_online_test.html",
                {
                    "recruiter": recruiter,
                    "online_test": online_test,
                    "jobs": jobs,
                    "error": error,
                    "form_data": request.POST,
                }
            )

        online_test.job = job
        online_test.title = title
        online_test.test_type = test_type
        online_test.description = description
        online_test.instructions = instructions
        online_test.duration_minutes = duration_minutes
        online_test.passing_percentage = passing_percentage
        online_test.test_deadline = deadline
        online_test.is_active = is_active
        online_test.save()

        return redirect("recruiter_tests")

    return render(
        request,
        "placement_student/edit_online_test.html",
        {
            "recruiter": recruiter,
            "online_test": online_test,
            "jobs": jobs,
        }
    )

# =========================
# RECRUITER - DELETE TEST
# =========================

@require_POST
def delete_online_test(request, test_id):
    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        online_test = OnlineTest.objects.get(
            id=test_id,
            recruiter=recruiter
        )
    except OnlineTest.DoesNotExist:
        return redirect("recruiter_tests")

    online_test.delete()

    return redirect("recruiter_tests")

# =========================
# RECRUITER - QUESTIONS
# =========================

def manage_test_questions(request, test_id):
    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        online_test = OnlineTest.objects.get(
            id=test_id,
            recruiter=recruiter
        )
    except OnlineTest.DoesNotExist:
        return redirect("recruiter_tests")

    questions = online_test.questions.all().order_by("id")

    total_marks = sum(
        question.marks
        for question in questions
    )

    return render(
        request,
        "placement_student/manage_test_questions.html",
        {
            "recruiter": recruiter,
            "online_test": online_test,
            "questions": questions,
            "total_marks": total_marks,
        }
    )

def add_test_question(request, test_id):
    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        online_test = OnlineTest.objects.get(
            id=test_id,
            recruiter=recruiter
        )
    except OnlineTest.DoesNotExist:
        return redirect("recruiter_tests")

    if request.method == "POST":

        question_text = request.POST.get(
            "question_text",
            ""
        ).strip()

        option_a = request.POST.get(
            "option_a",
            ""
        ).strip()

        option_b = request.POST.get(
            "option_b",
            ""
        ).strip()

        option_c = request.POST.get(
            "option_c",
            ""
        ).strip()

        option_d = request.POST.get(
            "option_d",
            ""
        ).strip()

        correct_answer = request.POST.get(
            "correct_answer",
            ""
        ).strip()

        marks_value = request.POST.get(
            "marks",
            "1"
        ).strip()

        error = None

        if (
            not question_text
            or not option_a
            or not option_b
            or not option_c
            or not option_d
        ):
            error = "Please fill all question and option fields."

        if correct_answer not in [
            "A",
            "B",
            "C",
            "D"
        ]:
            error = error or (
                "Please select the correct answer."
            )

        try:
            marks = int(marks_value)

            if marks <= 0:
                raise ValueError

        except (TypeError, ValueError):
            marks = None
            error = error or (
                "Marks must be greater than 0."
            )

        if error:
            return render(
                request,
                "placement_student/add_test_question.html",
                {
                    "recruiter": recruiter,
                    "online_test": online_test,
                    "error": error,
                    "form_data": request.POST,
                }
            )

        TestQuestion.objects.create(
            test=online_test,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct_answer,
            marks=marks,
        )

        return redirect(
            "manage_test_questions",
            test_id=online_test.id
        )

    return render(
        request,
        "placement_student/add_test_question.html",
        {
            "recruiter": recruiter,
            "online_test": online_test,
        }
    )

def edit_test_question(request, question_id):
    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        question = TestQuestion.objects.select_related(
            "test"
        ).get(
            id=question_id,
            test__recruiter=recruiter
        )
    except TestQuestion.DoesNotExist:
        return redirect("recruiter_tests")

    if request.method == "POST":

        question_text = request.POST.get(
            "question_text",
            ""
        ).strip()

        option_a = request.POST.get(
            "option_a",
            ""
        ).strip()

        option_b = request.POST.get(
            "option_b",
            ""
        ).strip()

        option_c = request.POST.get(
            "option_c",
            ""
        ).strip()

        option_d = request.POST.get(
            "option_d",
            ""
        ).strip()

        correct_answer = request.POST.get(
            "correct_answer",
            ""
        ).strip()

        marks_value = request.POST.get(
            "marks",
            "1"
        ).strip()

        error = None

        if (
            not question_text
            or not option_a
            or not option_b
            or not option_c
            or not option_d
        ):
            error = "Please fill all question and option fields."

        if correct_answer not in [
            "A",
            "B",
            "C",
            "D"
        ]:
            error = error or (
                "Please select the correct answer."
            )

        try:
            marks = int(marks_value)

            if marks <= 0:
                raise ValueError

        except (TypeError, ValueError):
            marks = None
            error = error or (
                "Marks must be greater than 0."
            )

        if error:
            return render(
                request,
                "placement_student/edit_test_question.html",
                {
                    "recruiter": recruiter,
                    "question": question,
                    "online_test": question.test,
                    "error": error,
                    "form_data": request.POST,
                }
            )

        question.question_text = question_text
        question.option_a = option_a
        question.option_b = option_b
        question.option_c = option_c
        question.option_d = option_d
        question.correct_answer = correct_answer
        question.marks = marks
        question.save()

        return redirect(
            "manage_test_questions",
            test_id=question.test.id
        )

    return render(
        request,
        "placement_student/edit_test_question.html",
        {
            "recruiter": recruiter,
            "question": question,
            "online_test": question.test,
        }
    )

@require_POST
def delete_test_question(request, question_id):
    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        question = TestQuestion.objects.get(
            id=question_id,
            test__recruiter=recruiter
        )
    except TestQuestion.DoesNotExist:
        return redirect("recruiter_tests")

    test_id = question.test_id

    question.delete()

    return redirect(
        "manage_test_questions",
        test_id=test_id
    )

# =========================
# RECRUITER - ASSIGN TEST
# =========================

def assign_online_test(request, test_id):
    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        online_test = OnlineTest.objects.select_related(
            "job"
        ).get(
            id=test_id,
            recruiter=recruiter
        )
    except OnlineTest.DoesNotExist:
        return redirect("recruiter_tests")

    applications = Application.objects.filter(
        job=online_test.job
    ).select_related(
        "student"
    ).order_by("student__name")

    assigned_application_ids = set(
        TestAssignment.objects.filter(
            test=online_test
        ).values_list(
            "application_id",
            flat=True
        )
    )

    if request.method == "POST":

        selected_ids = request.POST.getlist(
    "application_ids"
)

        if not selected_ids:
            return render(
                request,
                "placement_student/assign_online_test.html",
                {
                    "recruiter": recruiter,
                    "online_test": online_test,
                    "applications": applications,
                    "assigned_application_ids": assigned_application_ids,
                    "error": (
                        "Please select at least one applicant."
                    ),
                }
            )

        valid_applications = Application.objects.filter(
            id__in=selected_ids,
            job=online_test.job
        ).select_related("student")

        assigned_count = 0

        for application in valid_applications:

            assignment, created = (
                TestAssignment.objects.get_or_create(
                    test=online_test,
                    application=application
                )
            )

            if created:
                assigned_count += 1

                Notification.objects.create(
                    student=application.student,
                    title="Online Test Assigned",
                    message=(
                        f"{online_test.job.company_name} "
                        f"has assigned you "
                        f"{online_test.title} for the "
                        f"{online_test.job.job_title} position. "
                        f"Complete the test before "
                        f"{timezone.localtime(online_test.test_deadline).strftime('%d %b %Y, %I:%M %p')}."
                    ),
                    notification_type="Online Test",
                    job=online_test.job,
                )

        return redirect(
            "test_assignments",
            test_id=online_test.id
        )

    return render(
        request,
        "placement_student/assign_online_test.html",
        {
            "recruiter": recruiter,
            "online_test": online_test,
            "applications": applications,
            "assigned_application_ids": assigned_application_ids,
        }
    )

def test_assignments(request, test_id):
    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        online_test = OnlineTest.objects.get(
            id=test_id,
            recruiter=recruiter
        )
    except OnlineTest.DoesNotExist:
        return redirect("recruiter_tests")

    assignments = TestAssignment.objects.filter(
        test=online_test
    ).select_related(
        "application__student",
        "application__job"
    ).order_by("-assigned_at")

    return render(
        request,
        "placement_student/test_assignments.html",
        {
            "recruiter": recruiter,
            "online_test": online_test,
            "assignments": assignments,
        }
    )

@require_POST
def remove_test_assignment(request, assignment_id):
    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    try:
        assignment = TestAssignment.objects.get(
            id=assignment_id,
            test__recruiter=recruiter
        )
    except TestAssignment.DoesNotExist:
        return redirect("recruiter_tests")

    test_id = assignment.test_id

    if not hasattr(assignment, "attempt"):
        assignment.delete()

    return redirect(
        "test_assignments",
        test_id=test_id
    )

# =========================
# RECRUITER - TEST RESULTS
# =========================

def recruiter_test_results(request, test_id):
    recruiter = get_logged_in_recruiter(request)
    if not recruiter:
        return redirect("recruiter_login")
    try:
        online_test = OnlineTest.objects.get(id=test_id, recruiter=recruiter)
    except OnlineTest.DoesNotExist:
        return redirect("recruiter_tests")
    assignments = TestAssignment.objects.filter(test=online_test).select_related("application__student", "application__job").order_by("application__student__name")
    return render(request, "placement_student/recruiter_test_results.html", {
        "recruiter": recruiter,
        "online_test": online_test,
        "assignments": assignments,
        "total_assigned": assignments.count(),
        "total_submitted": assignments.filter(attempt__status="Submitted").count(),
        "total_passed": assignments.filter(attempt__status="Submitted", attempt__passed=True).count(),
    })

# =========================
# STUDENT - MY TESTS
# =========================

def student_tests(request):
    student = get_logged_in_student(request)
    if not student:
        return redirect("student_login")
    assignments = TestAssignment.objects.filter(application__student=student).select_related("test", "test__job", "application").order_by("-assigned_at")
    return render(request, "placement_student/student_tests.html", {
        "student": student,
        "assignments": assignments,
        "total_assigned": assignments.count(),
        "total_completed": assignments.filter(attempt__status="Submitted").count(),
        "total_pending": assignments.exclude(attempt__status="Submitted").count(),
        "unread_notifications_count": get_unread_notifications_count(student),
    })

# =========================
# STUDENT - TEST INSTRUCTIONS
# =========================

def student_test_instructions(request, assignment_id):
    student = get_logged_in_student(request)

    if not student:
        return redirect("student_login")

    try:
        assignment = TestAssignment.objects.select_related(
            "test",
            "test__job",
            "application"
        ).get(
            id=assignment_id,
            application__student=student
        )
    except TestAssignment.DoesNotExist:
        return redirect("student_tests")

    online_test = assignment.test

    question_count = online_test.questions.count()

    total_marks = sum(
        question.marks
        for question in online_test.questions.all()
    )

    attempt = getattr(
        assignment,
        "attempt",
        None
    )

    return render(
        request,
        "placement_student/student_test_instructions.html",
        {
            "student": student,
            "assignment": assignment,
            "online_test": online_test,
            "question_count": question_count,
            "total_marks": total_marks,
            "attempt": attempt,
            "unread_notifications_count":
                get_unread_notifications_count(student),
        }
    )

# =========================
# STUDENT - START TEST
# =========================

@require_POST
def start_online_test(request, assignment_id):
    student = get_logged_in_student(request)

    if not student:
        return redirect("student_login")

    try:
        assignment = TestAssignment.objects.select_related(
            "test",
            "application"
        ).get(
            id=assignment_id,
            application__student=student
        )
    except TestAssignment.DoesNotExist:
        return redirect("student_tests")

    online_test = assignment.test

    if not online_test.is_test_open():
        return redirect(
            "student_test_instructions",
            assignment_id=assignment.id
        )

    if not online_test.questions.exists():
        return redirect(
            "student_test_instructions",
            assignment_id=assignment.id
        )

    attempt, created = TestAttempt.objects.get_or_create(
        assignment=assignment
    )

    if (
        not created
        and attempt.status == "Submitted"
    ):
        return redirect(
            "student_test_result",
            attempt_id=attempt.id
        )

    return redirect(
        "take_online_test",
        attempt_id=attempt.id
    )

# =========================
# STUDENT - TAKE TEST
# =========================

def take_online_test(request, attempt_id):
    student = get_logged_in_student(request)

    if not student:
        return redirect("student_login")

    try:
        attempt = TestAttempt.objects.select_related(
            "assignment__test",
            "assignment__application"
        ).get(
            id=attempt_id,
            assignment__application__student=student
        )
    except TestAttempt.DoesNotExist:
        return redirect("student_tests")

    if attempt.status == "Submitted":
        return redirect(
            "student_test_result",
            attempt_id=attempt.id
        )

    online_test = attempt.assignment.test

    if (
        online_test.test_deadline
        and timezone.now() > online_test.test_deadline
    ):
        return submit_online_test(
            request,
            attempt.id,
            force_submit=True
        )

    end_time = (
        attempt.started_at
        + timedelta(
            minutes=online_test.duration_minutes
        )
    )

    if timezone.now() >= end_time:
        return submit_online_test(
            request,
            attempt.id,
            force_submit=True
        )

    questions = online_test.questions.all().order_by("id")

    remaining_seconds = int(
        (end_time - timezone.now()).total_seconds()
    )

    return render(
        request,
        "placement_student/take_online_test.html",
        {
            "student": student,
            "attempt": attempt,
            "online_test": online_test,
            "questions": questions,
            "remaining_seconds": max(
                remaining_seconds,
                0
            ),
        }
    )

# =========================
# STUDENT - SUBMIT + SCORE
# =========================

def submit_online_test(
    request,
    attempt_id,
    force_submit=False
):
    student = get_logged_in_student(request)

    if not student:
        return redirect("student_login")

    try:
        attempt = TestAttempt.objects.select_related(
            "assignment__test",
            "assignment__application__student",
            "assignment__application__job"
        ).get(
            id=attempt_id,
            assignment__application__student=student
        )
    except TestAttempt.DoesNotExist:
        return redirect("student_tests")

    if attempt.status == "Submitted":
        return redirect(
            "student_test_result",
            attempt_id=attempt.id
        )

    if (
        request.method != "POST"
        and not force_submit
    ):
        return redirect(
            "take_online_test",
            attempt_id=attempt.id
        )

    online_test = attempt.assignment.test

    questions = online_test.questions.all().order_by("id")

    score = 0
    total_marks = 0

    TestAnswer.objects.filter(
        attempt=attempt
    ).delete()

    for question in questions:

        total_marks += question.marks

        selected_answer = request.POST.get(
            f"question_{question.id}",
            ""
        )

        is_correct = (
            selected_answer
            == question.correct_answer
        )

        marks_awarded = (
            question.marks
            if is_correct
            else 0
        )

        score += marks_awarded

        TestAnswer.objects.create(
            attempt=attempt,
            question=question,
            selected_answer=selected_answer,
            is_correct=is_correct,
            marks_awarded=marks_awarded,
        )

    if total_marks > 0:
        percentage = round(
            (score / total_marks) * 100,
            2
        )
    else:
        percentage = 0

    passed = (
        percentage
        >= online_test.passing_percentage
    )

    attempt.score = score
    attempt.total_marks = total_marks
    attempt.percentage = percentage
    attempt.passed = passed
    attempt.status = "Submitted"
    attempt.submitted_at = timezone.now()
    attempt.save()

    Notification.objects.create(
        student=student,
        title="Online Test Submitted",
        message=(
            f"You completed {online_test.title} "
            f"for {online_test.job.company_name}. "
            f"Your score is {score}/{total_marks} "
            f"({percentage}%). "
            f"Result: "
            f"{'Passed' if passed else 'Not Passed'}."
        ),
        notification_type="Online Test",
        job=online_test.job,
    )

    return redirect(
        "student_test_result",
        attempt_id=attempt.id
    )

# =========================
# STUDENT - RESULT
# =========================

def student_test_result(request, attempt_id):
    student = get_logged_in_student(request)

    if not student:
        return redirect("student_login")

    try:
        attempt = TestAttempt.objects.select_related(
            "assignment__test",
            "assignment__test__job",
            "assignment__application"
        ).get(
            id=attempt_id,
            assignment__application__student=student,
            status="Submitted"
        )
    except TestAttempt.DoesNotExist:
        return redirect("student_tests")

    answers = attempt.answers.select_related(
        "question"
    ).order_by("question__id")

    return render(
        request,
        "placement_student/student_test_result.html",
        {
            "student": student,
            "attempt": attempt,
            "online_test": attempt.assignment.test,
            "answers": answers,
            "unread_notifications_count":
                get_unread_notifications_count(student),
        }
    )

# =========================
# ADMIN - ALL TESTS
# =========================

@login_required
def manage_online_tests(request):
    if not request.user.is_staff:
        return redirect("admin_dashboard")
    tests = OnlineTest.objects.select_related("recruiter", "job").order_by("-created_at")
    return render(request, "placement_student/manage_online_tests.html", {
        "tests": tests,
        "total_tests": tests.count(),
        "active_tests": tests.filter(is_active=True).count(),
        "total_assignments": TestAssignment.objects.count(),
        "total_submitted": TestAttempt.objects.filter(status="Submitted").count(),
    })

# =========================
# ADMIN - TEST RESULTS
# =========================

@login_required
def admin_test_results(request, test_id):
    if not request.user.is_staff:
        return redirect("admin_dashboard")
    try:
        online_test = OnlineTest.objects.select_related("recruiter", "job").get(id=test_id)
    except OnlineTest.DoesNotExist:
        return redirect("manage_online_tests")
    assignments = TestAssignment.objects.filter(test=online_test).select_related("application__student", "application__job").order_by("application__student__name")
    return render(request, "placement_student/admin_test_results.html", {
        "online_test": online_test,
        "assignments": assignments,
        "total_assigned": assignments.count(),
        "total_submitted": assignments.filter(attempt__status="Submitted").count(),
        "total_passed": assignments.filter(attempt__status="Submitted", attempt__passed=True).count(),
        "total_pending": assignments.exclude(attempt__status="Submitted").count(),
    })


# ============================================================
# PLACEMENT ANALYTICS + DEPARTMENT / COURSE / YEAR REPORTS
# ============================================================

@login_required
def placement_analytics(request):

    # Only College Admin can access analytics
    if not request.user.is_staff:
        return redirect("admin_dashboard")

    # --------------------------------------------------------
    # BASIC QUERYSETS
    # --------------------------------------------------------

    students = Student.objects.all()
    recruiters = Recruiter.objects.all()
    jobs = Job.objects.all()

    applications = Application.objects.select_related(
        "student",
        "job",
        "job__recruiter"
    )

    # --------------------------------------------------------
    # OVERALL COUNTS
    # --------------------------------------------------------

    total_students = students.count()

    total_recruiters = recruiters.count()

    approved_recruiters = recruiters.filter(
        verification_status="Approved"
    ).count()

    total_jobs = jobs.count()

    total_applications = applications.count()

    # --------------------------------------------------------
    # APPLICATION STATUS COUNTS
    # --------------------------------------------------------

    applied_count = applications.filter(
        status="Applied"
    ).count()

    shortlisted_count = applications.filter(
        status="Shortlisted"
    ).count()

    interview_count = applications.filter(
        status="Interview"
    ).count()

    selected_applications_count = applications.filter(
        status="Selected"
    ).count()

    rejected_count = applications.filter(
        status="Rejected"
    ).count()

    # --------------------------------------------------------
    # UNIQUE SELECTED STUDENTS
    # --------------------------------------------------------

    selected_students_count = applications.filter(
        status="Selected"
    ).values(
        "student_id"
    ).distinct().count()

    # --------------------------------------------------------
    # STUDENTS WHO HAVE APPLIED AT LEAST ONCE
    # --------------------------------------------------------

    students_applied_count = applications.values(
        "student_id"
    ).distinct().count()

    # --------------------------------------------------------
    # STUDENTS WITH NO APPLICATION
    # --------------------------------------------------------

    students_not_applied_count = (
        total_students - students_applied_count
    )

    # --------------------------------------------------------
    # PLACEMENT PERCENTAGE
    #
    # Unique selected students / total students
    # --------------------------------------------------------

    if total_students > 0:
        placement_percentage = round(
            (
                selected_students_count
                / total_students
            ) * 100,
            2
        )
    else:
        placement_percentage = 0

    # --------------------------------------------------------
    # APPLICATION SUCCESS RATE
    #
    # Selected applications / total applications
    # --------------------------------------------------------

    if total_applications > 0:
        application_success_rate = round(
            (
                selected_applications_count
                / total_applications
            ) * 100,
            2
        )
    else:
        application_success_rate = 0

    # ========================================================
    # DEPARTMENT-WISE REPORT
    # ========================================================

    department_names = (
        students
        .exclude(department="")
        .values_list(
            "department",
            flat=True
        )
        .distinct()
        .order_by("department")
    )

    department_reports = []

    for department in department_names:

        department_students = students.filter(
            department=department
        )

        department_applications = applications.filter(
            student__department=department
        )

        department_total_students = (
            department_students.count()
        )

        department_total_applications = (
            department_applications.count()
        )

        department_selected_students = (
            department_applications
            .filter(status="Selected")
            .values("student_id")
            .distinct()
            .count()
        )

        if department_total_students > 0:
            department_percentage = round(
                (
                    department_selected_students
                    / department_total_students
                ) * 100,
                2
            )
        else:
            department_percentage = 0

        department_reports.append(
            {
                "department": department,

                "total_students":
                    department_total_students,

                "total_applications":
                    department_total_applications,

                "applied":
                    department_applications.filter(
                        status="Applied"
                    ).count(),

                "shortlisted":
                    department_applications.filter(
                        status="Shortlisted"
                    ).count(),

                "interview":
                    department_applications.filter(
                        status="Interview"
                    ).count(),

                "selected":
                    department_selected_students,

                "rejected":
                    department_applications.filter(
                        status="Rejected"
                    ).count(),

                "placement_percentage":
                    department_percentage,
            }
        )

    # ========================================================
    # COURSE-WISE REPORT
    # ========================================================

    course_names = (
        students
        .exclude(course="")
        .values_list(
            "course",
            flat=True
        )
        .distinct()
        .order_by("course")
    )

    course_reports = []

    for course in course_names:

        course_students = students.filter(
            course=course
        )

        course_applications = applications.filter(
            student__course=course
        )

        course_total_students = (
            course_students.count()
        )

        course_total_applications = (
            course_applications.count()
        )

        course_selected_students = (
            course_applications
            .filter(status="Selected")
            .values("student_id")
            .distinct()
            .count()
        )

        if course_total_students > 0:
            course_percentage = round(
                (
                    course_selected_students
                    / course_total_students
                ) * 100,
                2
            )
        else:
            course_percentage = 0

        course_reports.append(
            {
                "course": course,

                "total_students":
                    course_total_students,

                "total_applications":
                    course_total_applications,

                "applied":
                    course_applications.filter(
                        status="Applied"
                    ).count(),

                "shortlisted":
                    course_applications.filter(
                        status="Shortlisted"
                    ).count(),

                "interview":
                    course_applications.filter(
                        status="Interview"
                    ).count(),

                "selected":
                    course_selected_students,

                "rejected":
                    course_applications.filter(
                        status="Rejected"
                    ).count(),

                "placement_percentage":
                    course_percentage,
            }
        )

    # ========================================================
    # GRADUATION YEAR-WISE REPORT
    # ========================================================

    graduation_years = (
        students
        .values_list(
            "graduation_year",
            flat=True
        )
        .distinct()
        .order_by("-graduation_year")
    )

    year_reports = []

    for year in graduation_years:

        year_students = students.filter(
            graduation_year=year
        )

        year_applications = applications.filter(
            student__graduation_year=year
        )

        year_total_students = (
            year_students.count()
        )

        year_total_applications = (
            year_applications.count()
        )

        year_selected_students = (
            year_applications
            .filter(status="Selected")
            .values("student_id")
            .distinct()
            .count()
        )

        if year_total_students > 0:
            year_percentage = round(
                (
                    year_selected_students
                    / year_total_students
                ) * 100,
                2
            )
        else:
            year_percentage = 0

        year_reports.append(
            {
                "graduation_year": year,

                "total_students":
                    year_total_students,

                "total_applications":
                    year_total_applications,

                "applied":
                    year_applications.filter(
                        status="Applied"
                    ).count(),

                "shortlisted":
                    year_applications.filter(
                        status="Shortlisted"
                    ).count(),

                "interview":
                    year_applications.filter(
                        status="Interview"
                    ).count(),

                "selected":
                    year_selected_students,

                "rejected":
                    year_applications.filter(
                        status="Rejected"
                    ).count(),

                "placement_percentage":
                    year_percentage,
            }
        )

    # ========================================================
    # COMPANY-WISE PLACEMENT REPORT
    # ========================================================

    company_names = (
        jobs
        .exclude(company_name="")
        .values_list(
            "company_name",
            flat=True
        )
        .distinct()
        .order_by("company_name")
    )

    company_reports = []

    for company in company_names:

        company_jobs = jobs.filter(
            company_name=company
        )

        company_applications = applications.filter(
            job__company_name=company
        )

        company_selected_students = (
            company_applications
            .filter(status="Selected")
            .values("student_id")
            .distinct()
            .count()
        )

        company_reports.append(
            {
                "company": company,

                "total_jobs":
                    company_jobs.count(),

                "total_applications":
                    company_applications.count(),

                "shortlisted":
                    company_applications.filter(
                        status="Shortlisted"
                    ).count(),

                "interview":
                    company_applications.filter(
                        status="Interview"
                    ).count(),

                "selected":
                    company_selected_students,

                "rejected":
                    company_applications.filter(
                        status="Rejected"
                    ).count(),
            }
        )

    # ========================================================
    # RECENT SELECTIONS
    # ========================================================

    recent_selections = (
        applications
        .filter(status="Selected")
        .select_related(
            "student",
            "job"
        )
        .order_by("-applied_at")[:10]
    )

    # ========================================================
    # TEMPLATE CONTEXT
    # ========================================================

    context = {

        # Overall
        "total_students":
            total_students,

        "total_recruiters":
            total_recruiters,

        "approved_recruiters":
            approved_recruiters,

        "total_jobs":
            total_jobs,

        "total_applications":
            total_applications,

        "students_applied_count":
            students_applied_count,

        "students_not_applied_count":
            students_not_applied_count,

        "selected_students_count":
            selected_students_count,

        "placement_percentage":
            placement_percentage,

        "application_success_rate":
            application_success_rate,

        # Status
        "applied_count":
            applied_count,

        "shortlisted_count":
            shortlisted_count,

        "interview_count":
            interview_count,

        "selected_count":
            selected_applications_count,

        "rejected_count":
            rejected_count,

        # Reports
        "department_reports":
            department_reports,

        "course_reports":
            course_reports,

        "year_reports":
            year_reports,

        "company_reports":
            company_reports,

        "recent_selections":
            recent_selections,
    }

    return render(
        request,
        "placement_student/placement_analytics.html",
        context
    )


# ============================================================
# PLACEMENT HISTORY
# ============================================================

@login_required
def placement_history(request):

    # Only College Admin can access placement history
    if not request.user.is_staff:
        return redirect("admin_dashboard")

    # --------------------------------------------------------
    # BASE QUERY
    # Only selected applications are placement records
    # --------------------------------------------------------

    placements = Application.objects.filter(
        status="Selected"
    ).select_related(
        "student",
        "job",
        "job__recruiter"
    ).order_by(
        "-student__graduation_year",
        "-applied_at"
    )

    # --------------------------------------------------------
    # FILTER / SEARCH VALUES
    # --------------------------------------------------------

    search_query = request.GET.get("search", "").strip()
    selected_department = request.GET.get("department", "").strip()
    selected_course = request.GET.get("course", "").strip()
    selected_year = request.GET.get("year", "").strip()
    selected_company = request.GET.get("company", "").strip()

    # --------------------------------------------------------
    # SEARCH
    # Student Name / PRN / Company / Job Role
    # --------------------------------------------------------

    if search_query:
        from django.db.models import Q

        placements = placements.filter(
            Q(student__name__icontains=search_query)
            | Q(student__prn__icontains=search_query)
            | Q(job__company_name__icontains=search_query)
            | Q(job__job_title__icontains=search_query)
        )

    # --------------------------------------------------------
    # FILTERS
    # --------------------------------------------------------

    if selected_department:
        placements = placements.filter(
            student__department=selected_department
        )

    if selected_course:
        placements = placements.filter(
            student__course=selected_course
        )

    if selected_year:
        placements = placements.filter(
            student__graduation_year=selected_year
        )

    if selected_company:
        placements = placements.filter(
            job__company_name=selected_company
        )

    # --------------------------------------------------------
    # SUMMARY COUNTS
    # These reflect the current filtered result
    # --------------------------------------------------------

    total_placement_records = placements.count()

    total_placed_students = placements.values(
        "student_id"
    ).distinct().count()

    total_companies = placements.values(
        "job__company_name"
    ).distinct().count()

    total_departments = placements.values(
        "student__department"
    ).distinct().count()

    # --------------------------------------------------------
    # FILTER DROPDOWN DATA
    # Use all selected placement records so dropdown choices
    # remain available even after applying a filter.
    # --------------------------------------------------------

    all_placements = Application.objects.filter(
        status="Selected"
    )

    departments = (
        all_placements
        .exclude(student__department="")
        .values_list(
            "student__department",
            flat=True
        )
        .distinct()
        .order_by("student__department")
    )

    courses = (
        all_placements
        .exclude(student__course="")
        .values_list(
            "student__course",
            flat=True
        )
        .distinct()
        .order_by("student__course")
    )

    graduation_years = (
        all_placements
        .values_list(
            "student__graduation_year",
            flat=True
        )
        .distinct()
        .order_by("-student__graduation_year")
    )

    companies = (
        all_placements
        .exclude(job__company_name="")
        .values_list(
            "job__company_name",
            flat=True
        )
        .distinct()
        .order_by("job__company_name")
    )

    # --------------------------------------------------------
    # YEAR-WISE PLACEMENT SUMMARY
    # --------------------------------------------------------

    year_summary = []

    for year in graduation_years:

        year_records = all_placements.filter(
            student__graduation_year=year
        )

        year_summary.append(
            {
                "year": year,

                "placed_students":
                    year_records.values(
                        "student_id"
                    ).distinct().count(),

                "placement_records":
                    year_records.count(),

                "companies":
                    year_records.values(
                        "job__company_name"
                    ).distinct().count(),
            }
        )

    # --------------------------------------------------------
    # DEPARTMENT-WISE PLACEMENT SUMMARY
    # --------------------------------------------------------

    department_summary = []

    for department in departments:

        department_records = all_placements.filter(
            student__department=department
        )

        department_summary.append(
            {
                "department": department,

                "placed_students":
                    department_records.values(
                        "student_id"
                    ).distinct().count(),

                "placement_records":
                    department_records.count(),

                "companies":
                    department_records.values(
                        "job__company_name"
                    ).distinct().count(),
            }
        )

    # --------------------------------------------------------
    # COMPANY-WISE PLACEMENT SUMMARY
    # --------------------------------------------------------

    company_summary = []

    for company in companies:

        company_records = all_placements.filter(
            job__company_name=company
        )

        company_summary.append(
            {
                "company": company,

                "placed_students":
                    company_records.values(
                        "student_id"
                    ).distinct().count(),

                "placement_records":
                    company_records.count(),

                "jobs":
                    company_records.values(
                        "job_id"
                    ).distinct().count(),
            }
        )

    # --------------------------------------------------------
    # CHECK WHETHER ANY FILTER IS ACTIVE
    # --------------------------------------------------------

    filters_active = any(
        [
            search_query,
            selected_department,
            selected_course,
            selected_year,
            selected_company,
        ]
    )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {

        # Main placement records
        "placements": placements,

        # Summary cards
        "total_placement_records": total_placement_records,
        "total_placed_students": total_placed_students,
        "total_companies": total_companies,
        "total_departments": total_departments,

        # Dropdown options
        "departments": departments,
        "courses": courses,
        "graduation_years": graduation_years,
        "companies": companies,

        # Current selected filters
        "search_query": search_query,
        "selected_department": selected_department,
        "selected_course": selected_course,
        "selected_year": selected_year,
        "selected_company": selected_company,

        # Filter state
        "filters_active": filters_active,

        # Historical summaries
        "year_summary": year_summary,
        "department_summary": department_summary,
        "company_summary": company_summary,
    }

    return render(
        request,
        "placement_student/placement_history.html",
        context
    )


# ============================================================
# FEEDBACK MODULE
# ============================================================


# ------------------------------------------------------------
# STUDENT FEEDBACK
# ------------------------------------------------------------

def student_feedback(request):

    student = get_logged_in_student(request)

    if not student:
        return redirect("student_login")

    success = None
    error = None

    if request.method == "POST":

        rating = request.POST.get("rating", "").strip()
        feedback_text = request.POST.get(
            "feedback_text",
            ""
        ).strip()

        # Validate rating
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            rating = 0

        if rating not in [1, 2, 3, 4, 5]:

            error = "Please select a rating from 1 to 5."

        elif not feedback_text:

            error = "Please enter your feedback."

        else:

            Feedback.objects.create(
                user_type="Student",
                student=student,
                rating=rating,
                feedback_text=feedback_text
            )

            success = "Thank you! Your feedback has been submitted successfully."

    feedbacks = Feedback.objects.filter(
        student=student,
        user_type="Student"
    ).order_by("-submitted_at")

    return render(
        request,
        "placement_student/student_feedback.html",
        {
            "student": student,
            "feedbacks": feedbacks,
            "success": success,
            "error": error,
            "unread_notifications_count":
                get_unread_notifications_count(student),
        }
    )


# ------------------------------------------------------------
# RECRUITER FEEDBACK
# ------------------------------------------------------------

def recruiter_feedback(request):

    recruiter = get_logged_in_recruiter(request)

    if not recruiter:
        return redirect("recruiter_login")

    success = None
    error = None

    if request.method == "POST":

        rating = request.POST.get("rating", "").strip()
        feedback_text = request.POST.get(
            "feedback_text",
            ""
        ).strip()

        # Validate rating
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            rating = 0

        if rating not in [1, 2, 3, 4, 5]:

            error = "Please select a rating from 1 to 5."

        elif not feedback_text:

            error = "Please enter your feedback."

        else:

            Feedback.objects.create(
                user_type="Recruiter",
                recruiter=recruiter,
                rating=rating,
                feedback_text=feedback_text
            )

            success = "Thank you! Your feedback has been submitted successfully."

    feedbacks = Feedback.objects.filter(
        recruiter=recruiter,
        user_type="Recruiter"
    ).order_by("-submitted_at")

    return render(
        request,
        "placement_student/recruiter_feedback.html",
        {
            "recruiter": recruiter,
            "feedbacks": feedbacks,
            "success": success,
            "error": error,
        }
    )


# ------------------------------------------------------------
# COLLEGE ADMIN - MANAGE FEEDBACK
# ------------------------------------------------------------

@login_required
def manage_feedback(request):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    feedbacks = Feedback.objects.select_related(
        "student",
        "recruiter"
    ).order_by("-submitted_at")

    # --------------------------------------------------------
    # FILTER VALUES
    # --------------------------------------------------------

    selected_user_type = request.GET.get(
        "user_type",
        ""
    ).strip()

    selected_rating = request.GET.get(
        "rating",
        ""
    ).strip()

    search_query = request.GET.get(
        "search",
        ""
    ).strip()

    # --------------------------------------------------------
    # USER TYPE FILTER
    # --------------------------------------------------------

    if selected_user_type in ["Student", "Recruiter"]:

        feedbacks = feedbacks.filter(
            user_type=selected_user_type
        )

    # --------------------------------------------------------
    # RATING FILTER
    # --------------------------------------------------------

    if selected_rating in ["1", "2", "3", "4", "5"]:

        feedbacks = feedbacks.filter(
            rating=int(selected_rating)
        )

    # --------------------------------------------------------
    # SEARCH
    # Student Name / PRN / Recruiter / Company
    # --------------------------------------------------------

    if search_query:

        from django.db.models import Q

        feedbacks = feedbacks.filter(

            Q(
                student__name__icontains=search_query
            )

            | Q(
                student__prn__icontains=search_query
            )

            | Q(
                recruiter__recruiter_name__icontains=search_query
            )

            | Q(
                recruiter__company_name__icontains=search_query
            )

            | Q(
                feedback_text__icontains=search_query
            )
        )

    # --------------------------------------------------------
    # COUNTS
    # Counts below represent all feedback, not filtered only
    # --------------------------------------------------------

    all_feedbacks = Feedback.objects.all()

    total_feedbacks = all_feedbacks.count()

    student_feedback_count = all_feedbacks.filter(
        user_type="Student"
    ).count()

    recruiter_feedback_count = all_feedbacks.filter(
        user_type="Recruiter"
    ).count()

    reviewed_count = all_feedbacks.filter(
        is_reviewed=True
    ).count()

    pending_review_count = all_feedbacks.filter(
        is_reviewed=False
    ).count()

    # --------------------------------------------------------
    # AVERAGE RATING
    # --------------------------------------------------------

    from django.db.models import Avg

    average_rating = all_feedbacks.aggregate(
        average=Avg("rating")
    )["average"]

    if average_rating is None:
        average_rating = 0
    else:
        average_rating = round(
            average_rating,
            1
        )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    return render(
        request,
        "placement_student/manage_feedback.html",
        {
            "feedbacks": feedbacks,

            "total_feedbacks": total_feedbacks,
            "student_feedback_count":
                student_feedback_count,
            "recruiter_feedback_count":
                recruiter_feedback_count,

            "reviewed_count": reviewed_count,
            "pending_review_count":
                pending_review_count,

            "average_rating": average_rating,

            "selected_user_type":
                selected_user_type,
            "selected_rating":
                selected_rating,
            "search_query":
                search_query,
        }
    )


# ------------------------------------------------------------
# ADMIN - MARK FEEDBACK AS REVIEWED
# ------------------------------------------------------------

@login_required
@require_POST
def mark_feedback_reviewed(request, feedback_id):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    try:

        feedback = Feedback.objects.get(
            id=feedback_id
        )

    except Feedback.DoesNotExist:

        return redirect("manage_feedback")

    feedback.is_reviewed = True

    feedback.save(
        update_fields=["is_reviewed"]
    )

    return redirect("manage_feedback")


# ------------------------------------------------------------
# ADMIN - MARK FEEDBACK AS PENDING
# ------------------------------------------------------------

@login_required
@require_POST
def mark_feedback_pending(request, feedback_id):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    try:

        feedback = Feedback.objects.get(
            id=feedback_id
        )

    except Feedback.DoesNotExist:

        return redirect("manage_feedback")

    feedback.is_reviewed = False

    feedback.save(
        update_fields=["is_reviewed"]
    )

    return redirect("manage_feedback")


# ------------------------------------------------------------
# ADMIN - DELETE FEEDBACK
# ------------------------------------------------------------

@login_required
@require_POST
def delete_feedback(request, feedback_id):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    try:

        feedback = Feedback.objects.get(
            id=feedback_id
        )

    except Feedback.DoesNotExist:

        return redirect("manage_feedback")

    feedback.delete()

    return redirect("manage_feedback")


# ============================================================
# REPORTS & EXPORT
# ============================================================


@login_required
def reports_export(request):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    total_students = Student.objects.count()
    total_jobs = Job.objects.count()
    total_applications = Application.objects.count()

    selected_students = Application.objects.filter(
        status="Selected"
    ).count()

    return render(
        request,
        "placement_student/reports_export.html",
        {
            "total_students": total_students,
            "total_jobs": total_jobs,
            "total_applications": total_applications,
            "selected_students": selected_students,
        }
    )


# ============================================================
# EXPORT STUDENTS CSV
# ============================================================

@login_required
def export_students_csv(request):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        'attachment; filename="students_report.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "PRN",
        "Student Name",
        "Email",
        "Course",
        "Department",
        "Graduation Year",
        "Phone",
        "Skills",
    ])

    students = Student.objects.all().order_by("prn")

    for student in students:

       writer.writerow([
    f'="{student.prn}"',
    student.name,
    student.email,
    student.course,
    student.department,
    student.graduation_year,
    f'="{student.phone}"',
    student.skills,
        ])

    return response


# ============================================================
# EXPORT APPLICATIONS CSV
# ============================================================

@login_required
def export_applications_csv(request):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        'attachment; filename="applications_report.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "PRN",
        "Student Name",
        "Email",
        "Course",
        "Department",
        "Company",
        "Job Title",
        "Location",
        "Salary",
        "Application Status",
        "Applied Date",
    ])

    applications = Application.objects.select_related(
        "student",
        "job"
    ).order_by("-applied_at")

    for application in applications:

        writer.writerow([
    f'="{application.student.prn}"',
    application.student.name,
    application.student.email,
    application.student.course,
    application.student.department,
    application.job.company_name,
    application.job.job_title,
    application.job.location,
    application.job.salary,
    application.status,
    application.applied_at.strftime(
        "%d-%m-%Y %I:%M %p"
    ),
])

    return response


# ============================================================
# EXPORT SELECTED STUDENTS CSV
# ============================================================

@login_required
def export_selected_students_csv(request):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        'attachment; filename="selected_students_report.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "PRN",
        "Student Name",
        "Email",
        "Course",
        "Department",
        "Graduation Year",
        "Company",
        "Job Title",
        "Location",
        "Salary",
        "Status",
    ])

    applications = Application.objects.filter(
        status="Selected"
    ).select_related(
        "student",
        "job"
    ).order_by(
        "student__name"
    )

    for application in applications:

        writer.writerow([
    f'="{application.student.prn}"',
    application.student.name,
    application.student.email,
    application.student.course,
    application.student.department,
    application.student.graduation_year,
    application.job.company_name,
    application.job.job_title,
    application.job.location,
    application.job.salary,
    application.status,
])
    return response


# ============================================================
# EXPORT JOBS CSV
# ============================================================

@login_required
def export_jobs_csv(request):

    if not request.user.is_staff:
        return redirect("admin_dashboard")

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        'attachment; filename="jobs_report.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "Company",
        "Job Title",
        "Recruiter",
        "Location",
        "Salary",
        "Eligible Courses",
        "Eligible Departments",
        "Graduation Year",
        "Required Skills",
        "Application Deadline",
        "Application Status",
    ])

    jobs = Job.objects.select_related(
        "recruiter"
    ).order_by("-id")

    for job in jobs:

        if job.application_deadline:
            deadline = job.application_deadline.strftime(
                "%d-%m-%Y"
            )
        else:
            deadline = "No Deadline"

        if job.is_application_open():
            application_status = "Open"
        else:
            application_status = "Closed"

        writer.writerow([
            job.company_name,
            job.job_title,
            job.recruiter.recruiter_name,
            job.location,
            job.salary,
            job.eligible_courses,
            job.eligible_departments,
            job.graduation_year,
            job.required_skills,
            deadline,
            application_status,
        ])

    return response