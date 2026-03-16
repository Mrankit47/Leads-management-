from django.contrib import admin
from .models import Plan, CompanySubscription

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'billing_cycle', 'max_users', 'max_leads', 'is_active')
    list_filter = ('billing_cycle', 'is_active')
    search_fields = ('name',)

@admin.register(CompanySubscription)
class CompanySubscriptionAdmin(admin.ModelAdmin):
    list_display = ('company', 'plan', 'status', 'start_date', 'end_date', 'is_active_status')
    list_filter = ('status', 'plan')
    search_fields = ('company__name',)

    def is_active_status(self, obj):
        return obj.is_active()
    is_active_status.boolean = True
    is_active_status.short_description = 'Is Active'
