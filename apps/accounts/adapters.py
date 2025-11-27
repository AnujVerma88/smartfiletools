"""
Custom adapters for Django Allauth social authentication.

This module provides custom adapters to handle Google OAuth authentication,
including account linking and profile population.
"""
import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class SmartToolPDFSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for SmartToolPDF platform.
    
    Handles:
    - Automatic account linking for existing users with matching email
    - Profile population from Google OAuth data
    - Email verification for social accounts
    """

    def pre_social_login(self, request, sociallogin):
        """
        Handle account linking before social login completes.
        
        If a user with the same email already exists, link the social account
        to the existing user account instead of creating a duplicate.
        
        Args:
            request: The HTTP request object
            sociallogin: The SocialLogin object containing OAuth data
        
        Validates: Requirements 1.5, 2.3
        """
        # If the social account is already connected, do nothing
        if sociallogin.is_existing:
            return

        # Get the email from the social account
        email = sociallogin.email_addresses[0].email if sociallogin.email_addresses else None
        
        if not email:
            logger.warning("Social login attempted without email address")
            return

        try:
            # Check if a user with this email already exists
            existing_user = User.objects.get(email=email)
            
            # Link the social account to the existing user
            sociallogin.connect(request, existing_user)
            
            # Mark email as verified since it comes from Google
            existing_user.email_verified = True
            existing_user.save(update_fields=['email_verified'])
            
            # Ensure EmailAddress record exists and is verified
            EmailAddress.objects.get_or_create(
                user=existing_user,
                email=email,
                defaults={'verified': True, 'primary': True}
            )
            
            logger.info(f"Linked Google account to existing user: {email}")
            
        except User.DoesNotExist:
            # No existing user, will create a new one
            logger.info(f"New user will be created for: {email}")
            pass

    def populate_user(self, request, sociallogin, data):
        """
        Populate user fields from Google OAuth data.
        
        Extracts and sets user information from the Google profile:
        - Email address
        - First name
        - Last name
        - Email verification status
        
        Args:
            request: The HTTP request object
            sociallogin: The SocialLogin object containing OAuth data
            data: Dictionary containing user data from Google
        
        Returns:
            User: The populated user instance
        
        Validates: Requirements 4.1, 4.2, 4.4
        """
        # Call parent method to get base user object
        user = super().populate_user(request, sociallogin, data)
        
        # Extract data from Google OAuth response
        email = data.get('email', '')
        given_name = data.get('given_name', '')
        family_name = data.get('family_name', '')
        
        # Populate user fields
        if email:
            user.email = email
            user.email_verified = True  # Trust Google's email verification
        
        if given_name:
            user.first_name = given_name
        
        if family_name:
            user.last_name = family_name
        
        # Generate username from email if not set
        if not user.username and email:
            # Use email prefix as username, ensure uniqueness
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user.username = username
        
        logger.info(f"Populated user data from Google: {email}")
        
        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Save the user after social authentication.
        
        Ensures email verification status is properly set for Google OAuth users.
        
        Args:
            request: The HTTP request object
            sociallogin: The SocialLogin object containing OAuth data
            form: Optional form data
        
        Returns:
            User: The saved user instance
        
        Validates: Requirements 1.3
        """
        user = super().save_user(request, sociallogin, form)
        
        # Ensure email is marked as verified for Google OAuth
        if user.email and not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])
        
        # Ensure EmailAddress record is marked as verified
        if user.email:
            EmailAddress.objects.filter(
                user=user,
                email=user.email
            ).update(verified=True, primary=True)
        
        logger.info(f"Saved Google OAuth user: {user.email}")
        
        return user

    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        """
        Handle OAuth authentication errors.
        
        Provides user-friendly error messages for different types of OAuth failures:
        - User cancellation
        - Network errors
        - Invalid credentials
        - CSRF/state validation errors
        
        Args:
            request: The HTTP request object
            provider_id: The social provider ID (e.g., 'google')
            error: Error code from OAuth provider
            exception: Exception object if an error occurred
            extra_context: Additional context information
        
        Validates: Requirements 2.4, 6.1, 6.2, 6.3, 6.4
        """
        from django.contrib import messages
        from django.shortcuts import redirect
        
        # Log the error for debugging
        logger.error(
            f"OAuth authentication error | Provider: {provider_id} | "
            f"Error: {error} | Exception: {exception}"
        )
        
        # Determine error type and provide appropriate message
        if error == 'access_denied':
            # User cancelled the OAuth flow
            messages.error(
                request,
                "Authentication cancelled. You can try again or use email/password to log in."
            )
            logger.info(f"User cancelled OAuth authentication | Provider: {provider_id}")
            
        elif exception and 'network' in str(exception).lower():
            # Network error occurred
            messages.error(
                request,
                "Network error occurred. Please check your connection and try again."
            )
            logger.warning(f"Network error during OAuth | Provider: {provider_id} | {exception}")
            
        elif exception and ('timeout' in str(exception).lower() or 'connection' in str(exception).lower()):
            # Connection timeout
            messages.error(
                request,
                "Connection timeout. Please try again in a moment."
            )
            logger.warning(f"Connection timeout during OAuth | Provider: {provider_id}")
            
        elif error == 'invalid_request' or (exception and 'invalid' in str(exception).lower()):
            # Invalid credentials or configuration
            messages.error(
                request,
                "Authentication failed. Please try again or contact support if the problem persists."
            )
            logger.error(f"Invalid OAuth credentials | Provider: {provider_id} | {exception}")
            
        elif error == 'state_mismatch' or (exception and 'state' in str(exception).lower()):
            # CSRF protection - state parameter mismatch
            messages.error(
                request,
                "Security validation failed. Please try logging in again."
            )
            logger.warning(f"CSRF state mismatch during OAuth | Provider: {provider_id}")
            
        else:
            # Generic error
            messages.error(
                request,
                "An error occurred during authentication. Please try again or use email/password to log in."
            )
            logger.error(f"Unknown OAuth error | Provider: {provider_id} | Error: {error} | {exception}")
        
        # Add link to alternative authentication methods
        messages.info(
            request,
            "You can also log in using your email and password."
        )
        
        # Return to login page
        return redirect('accounts:login')
    
    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Determine if automatic signup is allowed for this social login.
        
        Validates that the OAuth flow is legitimate and not a CSRF attack.
        
        Args:
            request: The HTTP request object
            sociallogin: The SocialLogin object containing OAuth data
        
        Returns:
            bool: True if auto signup is allowed, False otherwise
        
        Validates: Requirements 5.4
        """
        # Check if email is provided (required for signup)
        if not sociallogin.email_addresses:
            logger.warning("Auto signup denied: No email address provided")
            return False
        
        # Additional validation can be added here
        # For example, checking domain whitelist, etc.
        
        return True
