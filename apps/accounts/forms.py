"""
Forms for user authentication and profile management.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, UserProfile


class UserRegistrationForm(UserCreationForm):
    """
    User registration form with email and password validation.
    Username is auto-generated from email.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2']

    def clean_email(self):
        """Validate that email is unique."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email

    def clean_password1(self):
        """Validate password strength."""
        password = self.cleaned_data.get('password1')
        validate_password(password)
        return password

    def save(self, commit=True):
        """Save user and create profile. Auto-generate username from email."""
        user = super().save(commit=False)
        email = self.cleaned_data['email']
        user.email = email
        # Generate username from email (part before @)
        base_username = email.split('@')[0]
        username = base_username
        # Ensure username is unique
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username
        if commit:
            user.save()
            # Create user profile
            UserProfile.objects.create(user=user)
        return user


class UserLoginForm(forms.Form):
    """
    User login form with email-based authentication.
    """
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )


class CustomPasswordResetForm(PasswordResetForm):
    """
    Password reset form with styled email field.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )


class UserProfileForm(forms.ModelForm):
    """
    Form for updating user profile information.
    """
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'bio', 'email_notifications', 'marketing_emails']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Tell us about yourself',
                'rows': 4
            }),
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'marketing_emails': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class UserUpdateForm(forms.ModelForm):
    """
    Form for updating user basic information.
    """
    class Meta:
        model = User
        fields = ['username', 'email', 'avatar']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }

    def clean_email(self):
        """Validate that email is unique (excluding current user)."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A user with this email already exists.')
        return email
