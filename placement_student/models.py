from django.db import models
from django.utils import timezone


class Student(models.Model):
    prn = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    course = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    graduation_year = models.IntegerField(default=2027)
    phone = models.CharField(max_length=15)

    password = models.CharField(
        max_length=128,
        default=""
    )

    skills = models.CharField(
        max_length=500,
        blank=True,
        default=""
    )

    # Student Profile Photo
    profile_photo = models.ImageField(
        upload_to="student_profile_photos/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name

class Recruiter(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    company_name = models.CharField(max_length=100)
    recruiter_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)

    company_website = models.URLField(blank=True)
    company_description = models.TextField(blank=True)
    company_address = models.TextField(blank=True)
    company_contact = models.CharField(max_length=15, blank=True)

    verification_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class Job(models.Model):

    recruiter = models.ForeignKey(
        Recruiter,
        on_delete=models.CASCADE
    )

    company_name = models.CharField(max_length=100)
    job_title = models.CharField(max_length=100)
    description = models.TextField()

    eligible_courses = models.CharField(
        max_length=300,
        default=""
    )

    eligible_departments = models.CharField(
        max_length=300,
        default=""
    )

    graduation_year = models.IntegerField(default=2027)

    location = models.CharField(max_length=100)
    salary = models.CharField(max_length=100)

    required_skills = models.CharField(
        max_length=500,
        blank=True,
        default=""
    )

    # APPLICATION DEADLINE
    application_deadline = models.DateField(
        blank=True,
        null=True
    )

    def is_application_open(self):

        if not self.application_deadline:
            return True

        return timezone.localdate() <= self.application_deadline

    def __str__(self):
        return self.job_title


class Application(models.Model):

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE
    )

    applied_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=50,
        default="Applied"
    )

    # ==========================================
    # APPLICATION CONSENT / COMPANY QUESTIONS
    # ==========================================

    willing_to_relocate = models.BooleanField(
        default=False
    )

    comfortable_with_location = models.BooleanField(
        default=False
    )

    willing_to_work_shifts = models.BooleanField(
        default=False
    )

    has_active_backlogs = models.BooleanField(
        default=False
    )

    available_to_join = models.BooleanField(
        default=False
    )

    declaration_accepted = models.BooleanField(
        default=False
    )

    consent_submitted_at = models.DateTimeField(
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.student.name} - {self.job.job_title}"

    
class Resume(models.Model):

    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE
    )

    career_objective = models.TextField(blank=True)
    technical_skills = models.TextField(blank=True)
    projects = models.TextField(blank=True)
    certifications = models.TextField(blank=True)
    achievements = models.TextField(blank=True)

    uploaded_resume = models.FileField(
        upload_to="student_resumes/",
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.student.name} Resume"


class Notice(models.Model):

    title = models.CharField(max_length=200)
    description = models.TextField()

    notice_date = models.DateField(
        auto_now_add=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.title


class Notification(models.Model):

    NOTIFICATION_TYPES = [
    ("New Job", "New Job"),
    ("Status Update", "Status Update"),
    ("Deadline", "Deadline"),
    ("Interview", "Interview"),
    ("Online Test", "Online Test"),
    ("General", "General"),

]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(
        max_length=200
    )

    message = models.TextField()

    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default="General"
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.student.name} - {self.title}"

class Interview(models.Model):

    MODE_CHOICES = [
        ("Online", "Online"),
        ("Offline", "Offline"),
    ]

    STATUS_CHOICES = [
        ("Scheduled", "Scheduled"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="interview"
    )

    interview_date = models.DateField()

    interview_time = models.TimeField()

    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES
    )

    venue = models.CharField(
        max_length=300,
        blank=True,
        default=""
    )

    meeting_link = models.URLField(
        blank=True,
        default=""
    )

    instructions = models.TextField(
        blank=True,
        default=""
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Scheduled"
    )

    scheduled_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"{self.application.student.name} - "
            f"{self.application.job.job_title} Interview"
        )


class OnlineTest(models.Model):

    TEST_TYPE_CHOICES = [
        ("Aptitude", "Aptitude"),
        ("Technical", "Technical"),
        ("Mixed", "Mixed"),
    ]

    recruiter = models.ForeignKey(
        Recruiter,
        on_delete=models.CASCADE,
        related_name="online_tests"
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="online_tests"
    )

    title = models.CharField(
        max_length=200
    )

    test_type = models.CharField(
        max_length=20,
        choices=TEST_TYPE_CHOICES,
        default="Aptitude"
    )

    description = models.TextField(
        blank=True,
        default=""
    )

    instructions = models.TextField(
        blank=True,
        default=""
    )

    duration_minutes = models.PositiveIntegerField(
        default=30
    )

    passing_percentage = models.PositiveIntegerField(
        default=40
    )

    test_deadline = models.DateTimeField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def is_test_open(self):
        if not self.is_active:
            return False

        if self.test_deadline:
            return timezone.now() <= self.test_deadline

        return True

    def __str__(self):
        return f"{self.title} - {self.job.job_title}"


class TestQuestion(models.Model):

    test = models.ForeignKey(
        OnlineTest,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    question_text = models.TextField()

    option_a = models.CharField(
        max_length=500
    )

    option_b = models.CharField(
        max_length=500
    )

    option_c = models.CharField(
        max_length=500
    )

    option_d = models.CharField(
        max_length=500
    )

    CORRECT_ANSWER_CHOICES = [
        ("A", "Option A"),
        ("B", "Option B"),
        ("C", "Option C"),
        ("D", "Option D"),
    ]

    correct_answer = models.CharField(
        max_length=1,
        choices=CORRECT_ANSWER_CHOICES
    )

    marks = models.PositiveIntegerField(
        default=1
    )

    def __str__(self):
        return self.question_text[:60]


class TestAssignment(models.Model):

    test = models.ForeignKey(
        OnlineTest,
        on_delete=models.CASCADE,
        related_name="assignments"
    )

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="test_assignments"
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["test", "application"],
                name="unique_test_application_assignment"
            )
        ]

    def __str__(self):
        return (
            f"{self.application.student.name} - "
            f"{self.test.title}"
        )


class TestAttempt(models.Model):

    STATUS_CHOICES = [
        ("In Progress", "In Progress"),
        ("Submitted", "Submitted"),
    ]

    assignment = models.OneToOneField(
        TestAssignment,
        on_delete=models.CASCADE,
        related_name="attempt"
    )

    started_at = models.DateTimeField(
        auto_now_add=True
    )

    submitted_at = models.DateTimeField(
        blank=True,
        null=True
    )

    score = models.PositiveIntegerField(
        default=0
    )

    total_marks = models.PositiveIntegerField(
        default=0
    )

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    passed = models.BooleanField(
        default=False
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="In Progress"
    )

    def __str__(self):
        return (
            f"{self.assignment.application.student.name} - "
            f"{self.assignment.test.title}"
        )


class TestAnswer(models.Model):

    attempt = models.ForeignKey(
        TestAttempt,
        on_delete=models.CASCADE,
        related_name="answers"
    )

    question = models.ForeignKey(
        TestQuestion,
        on_delete=models.CASCADE
    )

    selected_answer = models.CharField(
        max_length=1,
        blank=True,
        default=""
    )

    is_correct = models.BooleanField(
        default=False
    )

    marks_awarded = models.PositiveIntegerField(
        default=0
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="unique_attempt_question_answer"
            )
        ]

    def __str__(self):
        return (
            f"{self.attempt.assignment.application.student.name} - "
            f"Question {self.question_id}"
        )


# ============================================================
# FEEDBACK
# ============================================================

class Feedback(models.Model):

    USER_TYPE_CHOICES = [
        ("Student", "Student"),
        ("Recruiter", "Recruiter"),
    ]

    RATING_CHOICES = [
        (1, "1 - Poor"),
        (2, "2 - Fair"),
        (3, "3 - Good"),
        (4, "4 - Very Good"),
        (5, "5 - Excellent"),
    ]

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="feedbacks",
        blank=True,
        null=True
    )

    recruiter = models.ForeignKey(
        Recruiter,
        on_delete=models.CASCADE,
        related_name="feedbacks",
        blank=True,
        null=True
    )

    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES
    )

    feedback_text = models.TextField()

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    is_reviewed = models.BooleanField(
        default=False
    )

    def __str__(self):

        if self.user_type == "Student" and self.student:
            return f"Student Feedback - {self.student.name}"

        if self.user_type == "Recruiter" and self.recruiter:
            return f"Recruiter Feedback - {self.recruiter.company_name}"

        return "Feedback"