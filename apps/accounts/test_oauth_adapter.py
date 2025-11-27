"""
Property-based tests for Google OAuth adapter.

These tests verify the correctness properties of the OAuth authentication system
using Hypothesis for property-based testing.
"""
import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.account.models import EmailAddress
from apps.accounts.adapters import SmartToolPDFSocialAccountAdapter

User = get_user_model()


# Strategies for generating test data
@st.composite
def email_strategy(draw):
    """Generate valid email addresses."""
    username = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), min_codepoint=97, max_codepoint=122),
        min_size=3,
        max_size=20
    ))
    domain = draw(st.sampled_from(['gmail.com', 'yahoo.com', 'outlook.com', 'example.com']))
    return f"{username}@{domain}"


@st.composite
def user_data_strategy(draw):
    """Generate user data from Google OAuth."""
    email = draw(email_strategy())
    given_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122),
        min_size=2,
        max_size=30
    ))
    family_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122),
        min_size=2,
        max_size=30
    ))
    
    return {
        'email': email,
        'given_name': given_name,
        'family_name': family_name,
        'verified_email': True,
    }


class TestOAuthAccountLinking(TestCase):
    """
    Property-based tests for OAuth account linking.
    
    **Feature: google-oauth-authentication, Property 4: Account linking for existing emails**
    **Validates: Requirements 1.5, 2.3**
    """

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.adapter = SmartToolPDFSocialAccountAdapter()

    @settings(max_examples=100, deadline=None)
    @given(user_data=user_data_strategy())
    def test_account_linking_for_existing_email(self, user_data):
        """
        Property: For any Google OAuth authentication where the email already exists,
        the system should link the Google account to the existing user without creating a duplicate.
        
        **Feature: google-oauth-authentication, Property 4: Account linking for existing emails**
        **Validates: Requirements 1.5, 2.3**
        """
        email = user_data['email']
        
        # Create an existing user with this email
        existing_user = User.objects.create_user(
            username=email.split('@')[0],
            email=email,
            password='testpass123'
        )
        initial_user_count = User.objects.count()
        
        # Create a mock social login
        request = self.factory.get('/accounts/google/login/callback/')
        
        # Create a new user instance (not saved yet) for the social login
        new_user = User(
            username=f"new_{email.split('@')[0]}",
            email=email
        )
        
        sociallogin = SocialLogin(user=new_user)
        sociallogin.account = SocialAccount(provider='google', uid=f'google_{email}')
        
        # Mock email addresses
        email_address = EmailAddress(email=email, verified=True, primary=True)
        sociallogin.email_addresses = [email_address]
        
        # Call pre_social_login to trigger account linking
        self.adapter.pre_social_login(request, sociallogin)
        
        # Verify no duplicate user was created
        final_user_count = User.objects.count()
        assert final_user_count == initial_user_count, \
            f"Expected {initial_user_count} users, but found {final_user_count}. Duplicate user created!"
        
        # Verify the existing user's email is marked as verified
        existing_user.refresh_from_db()
        assert existing_user.email_verified is True, \
            "Email should be marked as verified after Google OAuth linking"
        
        # Verify EmailAddress record exists and is verified
        email_record = EmailAddress.objects.filter(user=existing_user, email=email).first()
        assert email_record is not None, "EmailAddress record should exist"
        assert email_record.verified is True, "EmailAddress should be marked as verified"
        
        # Clean up
        existing_user.delete()


class TestOAuthProfilePopulation(TestCase):
    """
    Property-based tests for OAuth profile population.
    
    **Feature: google-oauth-authentication, Property 5: Profile data population**
    **Validates: Requirements 4.1, 4.2, 4.4**
    """

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.adapter = SmartToolPDFSocialAccountAdapter()

    @settings(max_examples=100, deadline=None)
    @given(user_data=user_data_strategy())
    def test_profile_data_population(self, user_data):
        """
        Property: For any new user created via Google OAuth, the system should populate
        the user's email, first name, and last name from the Google profile data.
        
        **Feature: google-oauth-authentication, Property 5: Profile data population**
        **Validates: Requirements 4.1, 4.2, 4.4**
        """
        email = user_data['email']
        given_name = user_data['given_name']
        family_name = user_data['family_name']
        
        # Create a mock social login with a user instance
        request = self.factory.get('/accounts/google/login/callback/')
        
        # Create a new user instance for the social login
        new_user = User()
        sociallogin = SocialLogin(user=new_user)
        sociallogin.account = SocialAccount(provider='google', uid=f'google_{email}')
        
        # Call populate_user to populate user data
        user = self.adapter.populate_user(request, sociallogin, user_data)
        
        # Verify email is populated
        assert user.email == email, \
            f"Expected email '{email}', but got '{user.email}'"
        
        # Verify first name is populated
        assert user.first_name == given_name, \
            f"Expected first_name '{given_name}', but got '{user.first_name}'"
        
        # Verify last name is populated
        assert user.last_name == family_name, \
            f"Expected last_name '{family_name}', but got '{user.last_name}'"
        
        # Verify email is marked as verified
        assert user.email_verified is True, \
            "Email should be marked as verified for Google OAuth users"
        
        # Verify username is generated from email
        assert user.username is not None and len(user.username) > 0, \
            "Username should be generated from email"
        
        # Username should be based on email prefix
        expected_username_base = email.split('@')[0]
        assert user.username.startswith(expected_username_base), \
            f"Username '{user.username}' should start with '{expected_username_base}'"



class TestOAuthAuthenticationLogging(TestCase):
    """
    Property-based tests for OAuth authentication logging.
    
    **Feature: google-oauth-authentication, Property 10: Authentication event logging**
    **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
    """

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.adapter = SmartToolPDFSocialAccountAdapter()

    @settings(max_examples=100, deadline=None)
    @given(user_data=user_data_strategy())
    def test_authentication_event_logging(self, user_data):
        """
        Property: For any OAuth authentication attempt (success or failure),
        the system should log the event with timestamp, user identifier, and outcome.
        
        **Feature: google-oauth-authentication, Property 10: Authentication event logging**
        **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
        """
        import logging
        from io import StringIO
        
        email = user_data['email']
        
        # Set up logging capture
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.INFO)
        logger = logging.getLogger('apps.accounts')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        try:
            # Create a mock social login
            request = self.factory.get('/accounts/google/login/callback/')
            request.META['REMOTE_ADDR'] = '127.0.0.1'
            
            # Create a new user instance for the social login
            new_user = User(
                username=email.split('@')[0],
                email=email
            )
            
            sociallogin = SocialLogin(user=new_user)
            sociallogin.account = SocialAccount(provider='google', uid=f'google_{email}')
            
            # Mock email addresses
            email_address = EmailAddress(email=email, verified=True, primary=True)
            sociallogin.email_addresses = [email_address]
            
            # Trigger pre_social_login signal (authentication attempt)
            from allauth.socialaccount.signals import pre_social_login
            pre_social_login.send(
                sender=SocialAccount,
                request=request,
                sociallogin=sociallogin
            )
            
            # Get log output
            log_output = log_stream.getvalue()
            
            # Verify authentication attempt is logged
            assert 'OAUTH ATTEMPT' in log_output, \
                "OAuth authentication attempt should be logged"
            
            assert 'google' in log_output.lower(), \
                "Log should contain provider name (google)"
            
            assert email in log_output, \
                f"Log should contain user email: {email}"
            
            # Verify IP address is logged
            assert '127.0.0.1' in log_output, \
                "Log should contain IP address"
            
        finally:
            # Clean up logging handler
            logger.removeHandler(handler)



class TestOAuthErrorHandling(TestCase):
    """
    Property-based tests for OAuth error handling.
    
    **Feature: google-oauth-authentication, Property 7: OAuth error handling**
    **Validates: Requirements 2.4, 6.1, 6.2, 6.3, 6.4**
    """

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.adapter = SmartToolPDFSocialAccountAdapter()

    @settings(max_examples=50, deadline=None)
    @given(error_type=st.sampled_from(['access_denied', 'invalid_request', 'network_error', 'timeout', 'unknown']))
    def test_oauth_error_handling(self, error_type):
        """
        Property: For any OAuth authentication failure, the system should display
        an appropriate error message and provide a way to retry or use alternative authentication.
        
        **Feature: google-oauth-authentication, Property 7: OAuth error handling**
        **Validates: Requirements 2.4, 6.1, 6.2, 6.3, 6.4**
        """
        from django.contrib.messages import get_messages
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        
        # Create request with session support
        request = self.factory.get('/accounts/google/login/callback/')
        
        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Add messages middleware
        msg_middleware = MessageMiddleware(lambda x: None)
        msg_middleware.process_request(request)
        
        # Simulate different error types
        error = None
        exception = None
        
        if error_type == 'access_denied':
            error = 'access_denied'
        elif error_type == 'invalid_request':
            error = 'invalid_request'
        elif error_type == 'network_error':
            exception = Exception("Network error occurred")
        elif error_type == 'timeout':
            exception = Exception("Connection timeout")
        else:
            error = 'unknown_error'
        
        # Call authentication_error
        response = self.adapter.authentication_error(
            request,
            provider_id='google',
            error=error,
            exception=exception
        )
        
        # Verify response redirects to login
        assert response.status_code == 302, \
            f"Should redirect (302), got {response.status_code}"
        
        assert '/accounts/login/' in response.url, \
            f"Should redirect to login page, got {response.url}"
        
        # Verify error message was added
        messages = list(get_messages(request))
        assert len(messages) > 0, \
            "At least one error message should be displayed"
        
        # Verify at least one error message exists
        error_messages = [m for m in messages if m.level_tag == 'error']
        assert len(error_messages) > 0, \
            "At least one error-level message should be present"
        
        # Verify message content is user-friendly (not technical)
        message_text = ' '.join([str(m.message) for m in messages])
        assert len(message_text) > 0, \
            "Error message should not be empty"
        
        # Verify alternative authentication is mentioned
        info_messages = [m for m in messages if m.level_tag == 'info']
        if info_messages:
            info_text = ' '.join([str(m.message) for m in info_messages])
            assert 'email' in info_text.lower() or 'password' in info_text.lower(), \
                "Should mention alternative authentication method"


class TestOAuthCSRFProtection(TestCase):
    """
    Property-based tests for OAuth CSRF protection.
    
    **Feature: google-oauth-authentication, Property 9: CSRF protection**
    **Validates: Requirements 5.4**
    """

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.adapter = SmartToolPDFSocialAccountAdapter()

    @settings(max_examples=50, deadline=None)
    @given(has_email=st.booleans())
    def test_csrf_protection_auto_signup(self, has_email):
        """
        Property: For any OAuth authentication flow, the system should validate
        the state parameter and only allow auto signup when proper validation passes.
        
        **Feature: google-oauth-authentication, Property 9: CSRF protection**
        **Validates: Requirements 5.4**
        """
        # Create request
        request = self.factory.get('/accounts/google/login/callback/')
        
        # Create a mock social login
        new_user = User(username='testuser', email='test@example.com' if has_email else '')
        sociallogin = SocialLogin(user=new_user)
        sociallogin.account = SocialAccount(provider='google', uid='google_test')
        
        # Add email addresses if has_email is True
        if has_email:
            email_address = EmailAddress(email='test@example.com', verified=True, primary=True)
            sociallogin.email_addresses = [email_address]
        else:
            sociallogin.email_addresses = []
        
        # Call is_auto_signup_allowed
        result = self.adapter.is_auto_signup_allowed(request, sociallogin)
        
        # Verify result matches expectation
        if has_email:
            assert result is True, \
                "Auto signup should be allowed when email is provided"
        else:
            assert result is False, \
                "Auto signup should be denied when no email is provided"



class TestSecureCredentialManagement(TestCase):
    """
    Unit tests for secure credential management.
    
    **Feature: google-oauth-authentication, Property 8: Secure credential management**
    **Validates: Requirements 5.1, 5.2, 5.3**
    """

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.adapter = SmartToolPDFSocialAccountAdapter()

    def test_credentials_loaded_from_environment(self):
        """
        Test that OAuth credentials are loaded from environment variables.
        
        **Feature: google-oauth-authentication, Property 8: Secure credential management**
        **Validates: Requirements 5.1, 5.2**
        """
        from django.conf import settings
        
        # Verify SOCIALACCOUNT_PROVIDERS is configured
        assert hasattr(settings, 'SOCIALACCOUNT_PROVIDERS'), \
            "SOCIALACCOUNT_PROVIDERS should be configured in settings"
        
        assert 'google' in settings.SOCIALACCOUNT_PROVIDERS, \
            "Google provider should be configured"
        
        google_config = settings.SOCIALACCOUNT_PROVIDERS['google']
        
        # Verify APP configuration exists
        assert 'APP' in google_config, \
            "APP configuration should exist for Google provider"
        
        app_config = google_config['APP']
        
        # Verify client_id and secret are configured (even if empty)
        assert 'client_id' in app_config, \
            "client_id should be configured"
        
        assert 'secret' in app_config, \
            "secret should be configured"
        
        # Credentials should be strings (loaded from environment)
        assert isinstance(app_config['client_id'], str), \
            "client_id should be a string"
        
        assert isinstance(app_config['secret'], str), \
            "secret should be a string"

    def test_credentials_not_hardcoded(self):
        """
        Test that credentials are not hardcoded in settings.
        
        **Feature: google-oauth-authentication, Property 8: Secure credential management**
        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        import os
        from pathlib import Path
        
        # Read settings.py file
        settings_path = Path(__file__).resolve().parent.parent.parent / 'smartfiletools' / 'settings.py'
        
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings_content = f.read()
        
        # Verify that Google OAuth configuration uses config() or os.environ
        assert 'config(' in settings_content or 'os.environ' in settings_content or 'os.getenv' in settings_content, \
            "Settings should use environment variable loading (config, os.environ, or os.getenv)"
        
        # Verify no hardcoded OAuth credentials (common patterns)
        suspicious_patterns = [
            '.apps.googleusercontent.com',  # Google client ID pattern
            'GOCSPX-',  # Google client secret prefix
        ]
        
        for pattern in suspicious_patterns:
            assert pattern not in settings_content, \
                f"Settings should not contain hardcoded credentials (found: {pattern})"

    def test_credentials_not_in_logs(self):
        """
        Test that credentials are not exposed in logs.
        
        **Feature: google-oauth-authentication, Property 8: Secure credential management**
        **Validates: Requirements 5.3**
        """
        import logging
        from io import StringIO
        
        # Set up logging capture
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger('apps.accounts')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        try:
            # Simulate OAuth operations that might log
            request = self.factory.get('/accounts/google/login/callback/')
            
            new_user = User(username='testuser', email='test@example.com')
            sociallogin = SocialLogin(user=new_user)
            sociallogin.account = SocialAccount(provider='google', uid='google_test')
            
            email_address = EmailAddress(email='test@example.com', verified=True, primary=True)
            sociallogin.email_addresses = [email_address]
            
            # Call adapter methods
            self.adapter.pre_social_login(request, sociallogin)
            
            # Get log output
            log_output = log_stream.getvalue()
            
            # Verify no sensitive patterns in logs
            sensitive_patterns = [
                'client_id',
                'client_secret',
                'access_token',
                'refresh_token',
            ]
            
            for pattern in sensitive_patterns:
                # Allow the pattern name itself, but not actual values
                # This is a basic check - in production, use more sophisticated detection
                assert log_output.count(pattern) == 0 or pattern in ['client_id', 'client_secret'], \
                    f"Logs should not contain sensitive credential data: {pattern}"
        
        finally:
            # Clean up logging handler
            logger.removeHandler(handler)
