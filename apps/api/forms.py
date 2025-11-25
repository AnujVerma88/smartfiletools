"""
Forms for API access requests and merchant management.
"""
from django import forms
from .models import APIAccessRequest


class APIAccessRequestForm(forms.ModelForm):
    """
    Form for requesting API access.
    Used by potential merchants to apply for API credentials.
    """
    
    class Meta:
        model = APIAccessRequest
        fields = [
            'full_name',
            'email',
            'company_name',
            'company_website',
            'phone_number',
            'use_case',
            'estimated_monthly_volume',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'John Doe',
                'required': True,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'john@company.com',
                'required': True,
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Company Name',
                'required': True,
            }),
            'company_website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.yourcompany.com',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 123-4567',
            }),
            'use_case': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Please describe how you plan to use our API...',
                'rows': 5,
                'required': True,
            }),
            'estimated_monthly_volume': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '1000',
                'min': '0',
            }),
        }
        labels = {
            'full_name': 'Full Name',
            'email': 'Email Address',
            'company_name': 'Company Name',
            'company_website': 'Company Website (Optional)',
            'phone_number': 'Phone Number (Optional)',
            'use_case': 'Use Case Description',
            'estimated_monthly_volume': 'Estimated Monthly API Requests',
        }
        help_texts = {
            'use_case': 'Tell us about your project and how you plan to integrate our API.',
            'estimated_monthly_volume': 'Approximate number of API requests you expect to make per month.',
        }
    
    def clean_email(self):
        """Validate email is not already used in a pending or approved request."""
        email = self.cleaned_data.get('email')
        if email:
            # Check for existing pending or approved requests
            existing = APIAccessRequest.objects.filter(
                email=email,
                status__in=['pending', 'approved']
            ).exists()
            
            if existing:
                raise forms.ValidationError(
                    'An API access request with this email already exists. '
                    'Please contact support if you need assistance.'
                )
        
        return email
    
    def clean_estimated_monthly_volume(self):
        """Ensure estimated volume is reasonable."""
        volume = self.cleaned_data.get('estimated_monthly_volume')
        if volume is not None and volume < 0:
            raise forms.ValidationError('Volume cannot be negative.')
        return volume
