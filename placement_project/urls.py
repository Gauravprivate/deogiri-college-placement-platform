"""
URL configuration for placement_project project.
"""

from django.contrib import admin
from django.urls import path
from placement_student import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    path('', views.home, name='home'),

    path('admin/', admin.site.urls),


    # =========================
    # COLLEGE ADMIN
    # =========================

    path(
        'college-admin/login/',
        views.college_admin_login,
        name='college_admin_login'
    ),

    path(
        'college-admin/dashboard/',
        views.admin_dashboard,
        name='admin_dashboard'
    ),


    # ---------- Students ----------

    path(
        'college-admin/students/',
        views.manage_students,
        name='manage_students'
    ),

    path(
        'college-admin/students/<int:student_id>/edit/',
        views.edit_student,
        name='edit_student'
    ),

    path(
        'college-admin/students/<int:student_id>/delete/',
        views.delete_student,
        name='delete_student'
    ),

    path(
        'college-admin/students/add/',
        views.add_student,
        name='add_student'
    ),


    # ---------- Recruiters ----------

    path(
        'college-admin/recruiters/',
        views.manage_recruiters,
        name='manage_recruiters'
    ),

    path(
        'college-admin/recruiters/add/',
        views.add_recruiter,
        name='add_recruiter'
    ),

    path(
        'college-admin/recruiters/<int:recruiter_id>/edit/',
        views.edit_recruiter,
        name='edit_recruiter'
    ),

    path(
        'college-admin/recruiters/<int:recruiter_id>/delete/',
        views.delete_recruiter,
        name='delete_recruiter'
    ),

    path(
        'college-admin/recruiters/<int:recruiter_id>/approve/',
        views.approve_recruiter,
        name='approve_recruiter'
    ),

    path(
        'college-admin/recruiters/<int:recruiter_id>/reject/',
        views.reject_recruiter,
        name='reject_recruiter'
    ),


    # ---------- Jobs ----------

    path(
        'college-admin/jobs/',
        views.manage_jobs,
        name='manage_jobs'
    ),

    path(
        'college-admin/jobs/add/',
        views.add_admin_job,
        name='add_admin_job'
    ),

    path(
        'college-admin/jobs/<int:job_id>/edit/',
        views.edit_admin_job,
        name='edit_admin_job'
    ),

    path(
        'college-admin/jobs/<int:job_id>/delete/',
        views.delete_admin_job,
        name='delete_admin_job'
    ),

    path(
        'college-admin/jobs/<int:job_id>/applicants/',
        views.admin_job_applicants,
        name='admin_job_applicants'
    ),


    # ---------- Interviews ----------

    path(
        'college-admin/interviews/',
        views.manage_interviews,
        name='manage_interviews'
    ),

         # ---------- Online Tests ----------

    path(
        'college-admin/tests/',
        views.manage_online_tests,
        name='manage_online_tests'
    ),

    path(
        'college-admin/tests/<int:test_id>/results/',
        views.admin_test_results,
        name='admin_test_results'
    ),

        # ---------- Placement Analytics ----------

    path(
        'college-admin/analytics/',
        views.placement_analytics,
        name='placement_analytics'
    ),

    # ---------- Placement History ----------

path(
    'college-admin/placement-history/',
    views.placement_history,
    name='placement_history'
),

    # ============================================================
    # REPORTS & EXPORT
    # ============================================================

    path(
        'college-admin/reports/',
        views.reports_export,
        name='reports_export'
    ),

    path(
        'college-admin/reports/students/csv/',
        views.export_students_csv,
        name='export_students_csv'
    ),

    path(
        'college-admin/reports/applications/csv/',
        views.export_applications_csv,
        name='export_applications_csv'
    ),

    path(
        'college-admin/reports/selected-students/csv/',
        views.export_selected_students_csv,
        name='export_selected_students_csv'
    ),

    path(
        'college-admin/reports/jobs/csv/',
        views.export_jobs_csv,
        name='export_jobs_csv'
    ),


# ============================================================
# FEEDBACK MODULE
# ============================================================

# ---------- Student Feedback ----------

path(
    'feedback/',
    views.student_feedback,
    name='student_feedback'
),

# ---------- Recruiter Feedback ----------

path(
    'recruiter/feedback/',
    views.recruiter_feedback,
    name='recruiter_feedback'
),

# ---------- College Admin - Manage Feedback ----------

path(
    'college-admin/feedback/',
    views.manage_feedback,
    name='manage_feedback'
),

# ---------- Admin - Mark Feedback Reviewed ----------

path(
    'college-admin/feedback/<int:feedback_id>/reviewed/',
    views.mark_feedback_reviewed,
    name='mark_feedback_reviewed'
),

# ---------- Admin - Mark Feedback Pending ----------

path(
    'college-admin/feedback/<int:feedback_id>/pending/',
    views.mark_feedback_pending,
    name='mark_feedback_pending'
),

# ---------- Admin - Delete Feedback ----------

path(
    'college-admin/feedback/<int:feedback_id>/delete/',
    views.delete_feedback,
    name='delete_feedback'
),
    # ---------- Notices ----------

    path(
        'college-admin/notices/',
        views.manage_notices,
        name='manage_notices'
    ),

    path(
        'college-admin/notices/add/',
        views.add_notice,
        name='add_notice'
    ),

    path(
        'college-admin/notices/<int:notice_id>/edit/',
        views.edit_notice,
        name='edit_notice'
    ),

    path(
        'college-admin/notices/<int:notice_id>/delete/',
        views.delete_notice,
        name='delete_notice'
    ),

    path(
        'college-admin/notices/<int:notice_id>/toggle/',
        views.toggle_notice,
        name='toggle_notice'
    ),


    # ---------- College Admin Logout ----------

    path(
        'college-admin/logout/',
        views.college_admin_logout,
        name='college_admin_logout'
    ),


    # =========================
    # STUDENT
    # =========================

    path(
        'student-login/',
        views.student_login,
        name='student_login'
    ),

    path(
        'dashboard/',
        views.dashboard,
        name='dashboard'
    ),

    path(
        'my-profile/',
        views.my_profile,
        name='my_profile'
    ),

    path(
        'student/profile/skills/update/',
        views.update_student_skills,
        name='update_student_skills'
    ),


    # ---------- Student Profile Photo ----------

    path(
        'student/profile/photo/upload/',
        views.upload_profile_photo,
        name='upload_profile_photo'
    ),

    path(
        'student/profile/photo/remove/',
        views.remove_profile_photo,
        name='remove_profile_photo'
    ),




    path(
        'available-jobs/',
        views.available_jobs,
        name='available_jobs'
    ),

    path(
        'apply-job/<int:job_id>/',
        views.apply_job,
        name='apply_job'
    ),

    path(
        'my-applications/',
        views.my_applications,
        name='my_applications'
    ),

    # ---------- Student Interviews ----------

path(
    'student/interviews/',
    views.student_interviews,
    name='student_interviews'
),
         # ---------- Student Online Tests ----------

    path(
        'student/tests/',
        views.student_tests,
        name='student_tests'
    ),

    path(
        'student/tests/<int:assignment_id>/instructions/',
        views.student_test_instructions,
        name='student_test_instructions'
    ),

    path(
        'student/tests/<int:assignment_id>/start/',
        views.start_online_test,
        name='start_online_test'
    ),

    path(
        'student/test-attempt/<int:attempt_id>/',
        views.take_online_test,
        name='take_online_test'
    ),

    path(
        'student/test-attempt/<int:attempt_id>/submit/',
        views.submit_online_test,
        name='submit_online_test'
    ),

    path(
        'student/test-attempt/<int:attempt_id>/result/',
        views.student_test_result,
        name='student_test_result'
    ),

    # ---------- Student Notifications ----------

    path(
        'student/notifications/',
        views.student_notifications,
        name='student_notifications'
    ),

    path(
        'student/notifications/<int:notification_id>/read/',
        views.mark_notification_read,
        name='mark_notification_read'
    ),

    path(
        'student/notifications/read-all/',
        views.mark_all_notifications_read,
        name='mark_all_notifications_read'
    ),


    # ---------- Student Resume ----------

    path(
        'resume/',
        views.resume,
        name='resume'
    ),

    path(
        'resume/edit/',
        views.edit_resume,
        name='edit_resume'
    ),

    path(
        'student/resume/upload/',
        views.upload_resume,
        name='upload_resume'
    ),

    path(
        'logout/',
        views.logout_student,
        name='logout_student'
    ),


    # =========================
    # RECRUITER
    # =========================

    path(
        'recruiter-register/',
        views.recruiter_register,
        name='recruiter_register'
    ),

    path(
        'recruiter-login/',
        views.recruiter_login,
        name='recruiter_login'
    ),

    path(
        'recruiter/dashboard/',
        views.recruiter_dashboard,
        name='recruiter_dashboard'
    ),

    path(
        'recruiter/post-job/',
        views.post_job,
        name='post_job'
    ),

    path(
        'recruiter/my-jobs/',
        views.my_jobs,
        name='my_jobs'
    ),

    path(
        'recruiter/job/<int:job_id>/edit/',
        views.edit_job,
        name='edit_job'
    ),

    path(
        'recruiter/job/<int:job_id>/delete/',
        views.delete_job,
        name='delete_job'
    ),

    path(
        'recruiter/job/<int:job_id>/applicants/',
        views.view_applicants,
        name='view_applicants'
    ),

    path(
        'recruiter/application/<int:application_id>/profile/',
        views.applicant_profile,
        name='applicant_profile'
    ),

    path(
        'recruiter/application/<int:application_id>/resume/',
        views.applicant_resume,
        name='applicant_resume'
    ),

    path(
        'recruiter/application/<int:application_id>/status/',
        views.update_application_status,
        name='update_application_status'
    ),

        # ---------- Online Tests ----------

    path(
        'recruiter/tests/',
        views.recruiter_tests,
        name='recruiter_tests'
    ),

    path(
        'recruiter/tests/create/',
        views.create_online_test,
        name='create_online_test'
    ),

    path(
        'recruiter/tests/<int:test_id>/edit/',
        views.edit_online_test,
        name='edit_online_test'
    ),

    path(
        'recruiter/tests/<int:test_id>/delete/',
        views.delete_online_test,
        name='delete_online_test'
    ),

    path(
        'recruiter/tests/<int:test_id>/questions/',
        views.manage_test_questions,
        name='manage_test_questions'
    ),

    path(
        'recruiter/tests/<int:test_id>/questions/add/',
        views.add_test_question,
        name='add_test_question'
    ),

    path(
        'recruiter/test-question/<int:question_id>/edit/',
        views.edit_test_question,
        name='edit_test_question'
    ),

    path(
        'recruiter/test-question/<int:question_id>/delete/',
        views.delete_test_question,
        name='delete_test_question'
    ),

    path(
        'recruiter/tests/<int:test_id>/assign/',
        views.assign_online_test,
        name='assign_online_test'
    ),

    path(
        'recruiter/tests/<int:test_id>/assignments/',
        views.test_assignments,
        name='test_assignments'
    ),

    path(
        'recruiter/test-assignment/<int:assignment_id>/remove/',
        views.remove_test_assignment,
        name='remove_test_assignment'
    ),

    path(
        'recruiter/tests/<int:test_id>/results/',
        views.recruiter_test_results,
        name='recruiter_test_results'
    ),


    # ---------- Interview Scheduling ----------

    path(
        'recruiter/application/<int:application_id>/interview/schedule/',
        views.schedule_interview,
        name='schedule_interview'
    ),

    path(
        'recruiter/interview/<int:interview_id>/edit/',
        views.edit_interview,
        name='edit_interview'
    ),

    path(
        'recruiter/interview/<int:interview_id>/cancel/',
        views.cancel_interview,
        name='cancel_interview'
    ),

    path(
        'recruiter/interview/<int:interview_id>/complete/',
        views.complete_interview,
        name='complete_interview'
    ),

    path(
        'recruiter/interviews/',
        views.recruiter_interviews,
        name='recruiter_interviews'
    ),


    # ---------- Recruiter Logout ----------

    path(
        'recruiter/logout/',
        views.recruiter_logout,
        name='recruiter_logout'
    ),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )