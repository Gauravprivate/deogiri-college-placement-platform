import os
import django
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "placement_project.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from placement_student.models import Student, Recruiter, Job, Application


# =========================
# DEMO STUDENT
# =========================

student, _ = Student.objects.update_or_create(
    prn="DEMO001",
    defaults={
        "name": "Demo Student",
        "email": "demo.student@deogiri.edu",
        "course": "MCS",
        "department": "CS",
        "graduation_year": 2027,
        "phone": "9000000001",
        "password": make_password("demo123"),
        "skills": "Python, Django, MySQL, HTML, CSS",
    },
)


# =========================
# DEMO RECRUITER
# =========================

recruiter, _ = Recruiter.objects.update_or_create(
    email="demo@technova.com",
    defaults={
        "company_name": "TechNova",
        "recruiter_name": "Demo Recruiter",
        "password": make_password("demo123"),
        "company_website": "https://example.com",
        "company_description": "Demo company for the Deogiri College Placement Platform.",
        "company_address": "Pune, Maharashtra",
        "company_contact": "9000000002",
        "verification_status": "Approved",
    },
)


# =========================
# DEMO JOB
# =========================

job, _ = Job.objects.update_or_create(
    recruiter=recruiter,
    job_title="Python Developer",
    defaults={
        "company_name": "TechNova",
        "description": "Demo Python Developer opportunity.",
        "eligible_courses": "BCS, MCS",
        "eligible_departments": "CS",
        "graduation_year": 2027,
        "location": "Pune",
        "salary": "5 LPA",
        "required_skills": "Python, Django, MySQL",
        "application_deadline": date(2027, 6, 30),
    },
)


# =========================
# DEMO APPLICATION
# =========================

Application.objects.update_or_create(
    student=student,
    job=job,
    defaults={
        "status": "Applied",
        "willing_to_relocate": True,
        "comfortable_with_location": True,
        "willing_to_work_shifts": False,
        "has_active_backlogs": False,
        "available_to_join": True,
        "declaration_accepted": True,
    },
)


# =========================
# DEMO ADMIN
# =========================

User = get_user_model()

if not User.objects.filter(username="demo_admin").exists():
    User.objects.create_superuser(
        username="demo_admin",
        email="demo.admin@deogiri.edu",
        password="demo123",
    )


print("")
print("======================================")
print("DEMO DATA READY")
print("======================================")
print("Student  : DEMO001 / demo123")
print("Recruiter: demo@technova.com / demo123")
print("Admin    : demo_admin / demo123")
print("======================================")