from django import forms
from django.contrib.auth.models import User
from .models import Lead, Company


class InquiryForm(forms.ModelForm):
    """Public form for customers to submit inquiries"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show all active companies in the dropdown
        self.fields['company'].queryset = Company.objects.filter(is_active=True)
        self.fields['company'].empty_label = "-- Search and select a company --"
        self.fields['company'].required = True

    class Meta:
        model = Lead
        fields = ['name', 'email', 'phone', 'company', 'product_name', 'product_description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Full Name', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your.email@example.com', 'required': True}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 234 567 8900', 'required': True}),
            'company': forms.Select(attrs={'class': 'form-control company-select', 'id': 'company-select'}),
            'product_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product/Service Name', 'required': True}),
            'product_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe your inquiry or requirements...', 'required': True}),
        }


class LeadUpdateForm(forms.ModelForm):
    """Form for sales team to update lead status and notes"""
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Filter assigned_to to only show users in the same company
        if company:
            self.fields['assigned_to'].queryset = User.objects.filter(
                userprofile__company=company
            ).distinct()
        else:
            self.fields['assigned_to'].queryset = User.objects.none()
            
        self.fields['assigned_to'].required = False
        self.fields['assigned_to'].empty_label = "Unassigned"
    
    class Meta:
        model = Lead
        fields = ['status', 'notes', 'assigned_to']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Add notes about this lead...'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
        }
