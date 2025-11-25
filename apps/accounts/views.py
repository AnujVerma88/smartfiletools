"""
Views for user authentication and profile management.
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    CustomPasswordResetForm,
    UserProfileForm,
    UserUpdateForm,
)
from .models import User, UserProfile
from apps.common.rate_limiting import rate_limit_login, rate_limit_password_reset

logger = logging.getLogger('apps.accounts')


class UserRegistrationView(CreateView):
    """
    User registration view with email and password validation.
    """
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        """Save user and log registration."""
        response = super().form_valid(form)
        user = form.instance
        logger.info(f"New user registered: {user.username} ({user.email})")
        messages.success(
            self.request,
            'Registration successful! You can now log in.'
        )
        return response

    def form_invalid(self, form):
        """Log registration errors."""
        logger.warning(f"Registration failed: {form.errors}")
        return super().form_invalid(form)


@rate_limit_login
def user_login_view(request):
    """
    User login view with session creation and rate limiting.
    Rate limited to 5 attempts per 5 minutes to prevent brute force attacks.
    Authenticates using email address.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            
            # Find user by email
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
                logger.warning(f"Failed login attempt - email not found: {email}")
            
            if user is not None:
                login(request, user)
                logger.info(f"User logged in successfully: {user.username} ({user.email})")
                messages.success(request, f'Welcome back!')
                
                # Redirect to next parameter or dashboard
                next_url = request.GET.get('next', 'dashboard:home')
                return redirect(next_url)
            else:
                logger.warning(f"Failed login attempt for email: {email}")
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please enter a valid email and password.')
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def user_logout_view(request):
    """
    User logout view with session cleanup.
    """
    username = request.user.username
    logout(request)
    messages.success(request, f'Goodbye, {username}! You have been logged out.')
    return redirect('accounts:login')


class CustomPasswordResetView(PasswordResetView):
    """
    Password reset request view with email sending and rate limiting.
    Rate limited to 3 attempts per 10 minutes to prevent abuse.
    """
    form_class = CustomPasswordResetForm
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')
    
    @classmethod
    def as_view(cls, **initkwargs):
        """Apply rate limiting decorator to the view."""
        view = super().as_view(**initkwargs)
        return rate_limit_password_reset(view)

    def form_valid(self, form):
        """Log password reset request."""
        email = form.cleaned_data.get('email')
        logger.info(f"Password reset requested for email: {email}")
        messages.success(
            self.request,
            'Password reset email has been sent. Please check your inbox.'
        )
        return super().form_valid(form)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Password reset confirmation view.
    """
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')

    def form_valid(self, form):
        """Log successful password reset."""
        logger.info(f"Password reset completed for user")
        messages.success(
            self.request,
            'Your password has been reset successfully. You can now log in.'
        )
        return super().form_valid(form)


class UserProfileView(LoginRequiredMixin, DetailView):
    """
    User profile view displaying user information and statistics.
    """
    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'

    def get_object(self):
        """Get current user."""
        return self.request.user

    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        context['profile'] = profile
        
        # Get usage statistics
        context['total_conversions'] = user.conversions.count()
        context['completed_conversions'] = user.conversions.filter(status='completed').count()
        from django.conf import settings
        context['daily_usage'] = user.daily_usage_count
        context['daily_limit'] = settings.DAILY_CONVERSION_LIMIT_FREE if not user.is_premium else 'Unlimited'
        context['remaining_conversions'] = max(0, settings.DAILY_CONVERSION_LIMIT_FREE - user.daily_usage_count) if not user.is_premium else 'Unlimited'
        
        # Get recent conversions
        context['recent_conversions'] = user.conversions.order_by('-created_at')[:5]
        
        return context


class UserProfileEditView(LoginRequiredMixin, UpdateView):
    """
    User profile edit view for updating profile information.
    """
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        """Get or create user profile."""
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        """Add user update form to context."""
        context = super().get_context_data(**kwargs)
        if 'user_form' not in context:
            context['user_form'] = UserUpdateForm(instance=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        """Handle both profile and user form submission."""
        self.object = self.get_object()
        profile_form = self.get_form()
        user_form = UserUpdateForm(request.POST, request.FILES, instance=request.user)

        if profile_form.is_valid() and user_form.is_valid():
            profile_form.save()
            user_form.save()
            messages.success(request, 'Profile updated successfully!')
            logger.info(f"Profile updated for user: {request.user.username}")
            return redirect(self.success_url)
        else:
            return self.render_to_response(
                self.get_context_data(form=profile_form, user_form=user_form)
            )
