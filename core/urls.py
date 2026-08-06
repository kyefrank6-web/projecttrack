from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_school, name="register_school"),
    path("account/settings/", views.account_settings, name="account_settings"),
    path("account/password-change/", views.school_password_change, name="password_change"),
    path("account/password-change/done/", views.school_password_change_done, name="password_change_done"),
    path("registration/pending/", views.registration_pending, name="registration_pending"),
    path("registration/rejected/", views.registration_rejected, name="registration_rejected"),
    path("superadmin/", views.superadmin_dashboard, name="superadmin_dashboard"),
    path("superadmin/school/<int:school_id>/", views.superadmin_school_detail, name="superadmin_school_detail"),
    path(
        "superadmin/school/<int:school_id>/approve/",
        views.superadmin_approve_school,
        name="superadmin_approve_school",
    ),
    path(
        "superadmin/school/<int:school_id>/reject/",
        views.superadmin_reject_school,
        name="superadmin_reject_school",
    ),
    path(
        "superadmin/school/<int:school_id>/delete/",
        views.superadmin_delete_school,
        name="superadmin_delete_school",
    ),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("password-reset/", views.password_reset_request, name="password_reset_request"),
    path("password-reset/done/", views.password_reset_done, name="password_reset_done"),
    path(
        "password-reset/confirm/<str:signed_membership_id>/<str:token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    path("password-reset/complete/", views.password_reset_complete, name="password_reset_complete"),
    path("overall/", views.overall_dashboard, name="overall_dashboard"),
    path("overall/supervisors/", views.overall_supervisors, name="overall_supervisors"),
    path(
        "overall/supervisors/delete-all/",
        views.overall_delete_all_supervisors,
        name="overall_delete_all_supervisors",
    ),
    path(
        "overall/supervisors/<int:supervisor_id>/delete/",
        views.overall_delete_supervisor,
        name="overall_delete_supervisor",
    ),
    path(
        "overall/supervisors/<int:supervisor_id>/reset-password/",
        views.overall_reset_supervisor_password,
        name="overall_reset_supervisor_password",
    ),
    path(
        "overall/supervisors/reset-password/done/",
        views.overall_supervisor_password_reset_done,
        name="overall_supervisor_password_reset_done",
    ),
    path(
        "overall/supervisors/<int:supervisor_id>/students/",
        views.overall_supervisor_students,
        name="overall_supervisor_students",
    ),
    path("overall/students/", views.overall_students, name="overall_students"),
    path("overall/students/promote/", views.overall_promote_students, name="overall_promote_students"),
    path(
        "overall/students/unassigned/",
        views.overall_students_unassigned,
        name="overall_students_unassigned",
    ),
    path(
        "overall/students/delete-all/",
        views.overall_delete_all_students,
        name="overall_delete_all_students",
    ),
    path(
        "overall/students/<int:student_id>/delete/",
        views.overall_delete_student,
        name="overall_delete_student",
    ),
    path(
        "overall/students/<int:student_id>/assign-supervisor/",
        views.overall_assign_student_supervisor,
        name="overall_assign_student_supervisor",
    ),
    path("overall/upload-supervisors/", views.upload_supervisors, name="upload_supervisors"),
    path("overall/add-supervisor/", views.overall_add_supervisor, name="overall_add_supervisor"),
    path("overall/upload-students/", views.upload_students, name="upload_students"),
    path("overall/add-student/", views.overall_add_student, name="overall_add_student"),
    path("overall/school-logo/", views.overall_upload_logo, name="overall_upload_logo"),
    path("overall/observation-checklists/", views.overall_observation_checklists, name="overall_observation_checklists"),
    path(
        "overall/class-project-themes/",
        views.overall_class_project_themes,
        name="overall_class_project_themes",
    ),
    path(
        "overall/observation-checklists/structure-template/",
        views.download_observation_structure_template,
        name="download_observation_structure_template",
    ),
    path(
        "observation-checklist/<int:checklist_id>/download/",
        views.download_observation_checklist,
        name="download_observation_checklist",
    ),
    path(
        "overall/observation-checklists/<int:checklist_id>/delete/",
        views.delete_observation_checklist,
        name="delete_observation_checklist",
    ),
    path(
        "supervisor/observation-checklists/",
        views.supervisor_observation_checklists,
        name="supervisor_observation_checklists",
    ),
    path("overall/evidence/", views.overall_evidence_index, name="overall_evidence_index"),
    path("overall/student/<int:student_id>/evidence/", views.overall_student_evidence, name="overall_student_evidence"),
    path(
        "overall/student/<int:student_id>/edit-scores/",
        views.overall_edit_student_scores,
        name="overall_edit_student_scores",
    ),
    path(
        "overall/student/<int:student_id>/observation-checklist-pdf/",
        views.export_student_observation_checklist_pdf,
        name="export_student_observation_checklist_pdf",
    ),
    path(
        "overall/student/<int:student_id>/edit/",
        views.overall_edit_student,
        name="overall_edit_student",
    ),
    path("supervisor/evidence/", views.supervisor_evidence_index, name="supervisor_evidence_index"),
    path("overall/class/<str:class_level>/", views.class_scores, name="class_scores"),
    path("overall/class/<str:class_level>/export/", views.export_class_scores, name="export_class_scores"),
    path(
        "overall/class/<str:class_level>/export-with-evidence/",
        views.export_class_with_evidence,
        name="export_class_with_evidence",
    ),
    path(
        "overall/class/<str:class_level>/export-pdf/",
        views.export_class_scores_pdf,
        name="export_class_scores_pdf",
    ),
    path(
        "overall/class/<str:class_level>/export-project-titles/",
        views.export_class_project_titles,
        name="export_class_project_titles",
    ),
    path(
        "overall/class/<str:class_level>/export-project-titles-pdf/",
        views.export_class_project_titles_pdf,
        name="export_class_project_titles_pdf",
    ),
    path(
        "overall/class/<str:class_level>/export-evidence-pdf/",
        views.export_class_evidence_pdf,
        name="export_class_evidence_pdf",
    ),
    path(
        "overall/class/<str:class_level>/export-observation-checklists-zip/",
        views.export_class_observation_checklists_zip,
        name="export_class_observation_checklists_zip",
    ),
    path("supervisor/", views.supervisor_dashboard, name="supervisor_dashboard"),
    path("supervisor/student/<int:student_id>/score/", views.score_student, name="score_student"),
    path("supervisor/student/<int:student_id>/evidence/", views.upload_evidence, name="upload_evidence"),
    path("evidence/<int:evidence_id>/download/", views.download_evidence, name="download_evidence"),
]

