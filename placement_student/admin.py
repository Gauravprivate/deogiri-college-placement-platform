from django.contrib import admin
from .models import Student, Job, Application, Recruiter, Notice


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "prn",
        "name",
        "email",
        "course",
        "department",
        "phone",
    )

    search_fields = (
        "prn",
        "name",
        "email",
        "course",
        "department",
    )

    list_filter = (
        "course",
        "department",
    )

    ordering = ("name",)

    fieldsets = (
        (
            "Student Information",
            {
                "fields": (
                    "prn",
                    "name",
                    "email",
                    "phone",
                )
            },
        ),
        (
            "Academic Information",
            {
                "fields": (
                    "course",
                    "department",
                )
            },
        ),
    )


@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "recruiter_name",
        "email",
    )

    search_fields = (
        "company_name",
        "recruiter_name",
        "email",
    )

    ordering = ("company_name",)

    fieldsets = (
        (
            "Company Information",
            {
                "fields": (
                    "company_name",
                )
            },
        ),
        (
            "Recruiter Information",
            {
                "fields": (
                    "recruiter_name",
                    "email",
                    "password",
                )
            },
        ),
    )


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):

    list_display = (
        "job_title",
        "company_name",
        "recruiter",
        "eligible_courses",
        "eligible_departments",
        "graduation_year",
        "location",
        "salary",
    )

    search_fields = (
        "job_title",
        "company_name",
        "eligible_courses",
        "eligible_departments",
    )

    list_filter = (
        "graduation_year",
        "location",
    )

    ordering = (
        "company_name",
        "job_title",
    )

    fieldsets = (
        (
            "Job Information",
            {
                "fields": (
                    "company_name",
                    "job_title",
                    "description",
                )
            },
        ),
        (
            "Eligibility & Compensation",
            {
                "fields": (
                    "eligibility",
                    "location",
                    "salary",
                )
            },
        ),
        (
            "Recruiter",
            {
                "fields": (
                    "recruiter",
                )
            },
        ),
    )


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "job",
        "status",
        "applied_at",
    )

    search_fields = (
        "student__name",
        "student__prn",
        "student__email",
        "job__job_title",
        "job__company_name",
    )

    list_filter = (
        "status",
        "applied_at",
    )

    ordering = ("-applied_at",)

    fieldsets = (
        (
            "Application Information",
            {
                "fields": (
                    "student",
                    "job",
                    "applied_at",
                )
            },
        ),
        (
            "Application Status",
            {
                "fields": (
                    "status",
                )
            },
        ),
    )

    readonly_fields = ("applied_at",)


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "notice_date",
        "is_active",
    )

    search_fields = (
        "title",
        "description",
    )

    list_filter = (
        "is_active",
        "notice_date",
    )

    ordering = ("-notice_date",)

    fieldsets = (
        (
            "Notice Information",
            {
                "fields": (
                    "title",
                    "description",
                )
            },
        ),
        (
            "Publication",
            {
                "fields": (
                    "is_active",
                    "notice_date",
                )
            },
        ),
    )

    readonly_fields = ("notice_date",)


# Django Admin Branding
admin.site.site_header = "Deogiri College Placement Administration"
admin.site.site_title = "College Placement Admin"
admin.site.index_title = "College Placement Management"