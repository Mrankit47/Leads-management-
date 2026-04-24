from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing_page, name='home'),
    path('inquiry-form/', views.inquiry_form, name='inquiry_form'),
    path('chatbot/submit/', views.chatbot_submit, name='chatbot_submit'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('lead/<int:lead_id>/', views.lead_detail, name='lead_detail'),
    path('lead/<int:lead_id>/delete/', views.delete_lead, name='delete_lead'),
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/fetch-emails/', views.fetch_email_inquiries, name='manager_fetch_emails'),
    #path('login/', auth_views.LoginView.as_view(template_name='leads/login.html'), name='login'),
    path("login/", views.employee_login, name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('superadmin/login/', views.superadmin_login, name='superadmin_login'),
    path('superadmin/dashboard/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path("superadmin/create-company/", views.create_company, name="create_company"),
    path("superadmin/delete-company/<int:company_id>/", views.delete_company, name="delete_company"),
    path("company-admin/", views.company_admin_dashboard, name="company_admin_dashboard"),
    path("company-admin/users/", views.users_list, name="users_list"),
    path("company-admin/create-user/", views.create_user, name="create_user"),
    path("company-admin/delete-user/<int:user_id>/", views.delete_user, name="delete_user"),
    path("company-admin/edit-user/<int:user_id>/", views.edit_user, name="edit_user"),

    #Tickets
    path("tickets/", views.tickets_list, name="tickets_list"),
    path("tickets/create/", views.create_ticket, name="create_ticket"),
    path("tickets/<int:id>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:id>/delete/", views.delete_ticket, name="delete_ticket"),

    path(
    "superadmin/company-toggle/<int:company_id>/",
    views.toggle_company_status,
    name="toggle_company_status"),

    path(
    "superadmin/company/<int:company_id>/",
    views.company_detail_view,
    name="company_detail_view"
),

    path("editor/dashboard/", views.editor_dashboard, name="editor_dashboard"),
    path("hybrid/dashboard/", views.hybrid_dashboard, name="hybrid_dashboard"),
    path("employee/dashboard/", views.employee_dashboard, name="employee_dashboard"),

    # Sales Dashboards
    path("company-admin/sales-dashboard/", views.adashboard, name="adashboard"),
    path("manager/sales-dashboard/", views.mdashboard, name="mdashboard"),

    # Integration Settings
    path("api/settings/whatsapp/", views.update_whatsapp_settings, name="update_whatsapp_settings"),
    path("api/settings/gmail/", views.update_gmail_settings, name="update_gmail_settings"),
    path("api/user/update-role/", views.update_user_role, name="update_user_role"),
    path("profile/", views.employee_profile, name="employee_profile"),
]

