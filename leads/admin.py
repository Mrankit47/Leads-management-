from django.contrib import admin
from .models import Lead, LeadActivity, Ticket, Department, Company


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'product_name', 'status', 'assigned_to', 'created_at']
    list_filter = ['status', 'created_at', 'assigned_to']
    search_fields = ['name', 'email', 'product_name', 'company']


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ['lead', 'user', 'action', 'timestamp']
    list_filter = ['timestamp', 'user']
    readonly_fields = ['timestamp']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'status', 'source', 'lead', 'created_at']
    list_filter = ['status', 'source', 'created_at']
    search_fields = ['subject', 'description', 'customer_name', 'customer_email', 'customer_phone']

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'company']
    list_filter = ['company']
    search_fields = ['name', 'company__name']
