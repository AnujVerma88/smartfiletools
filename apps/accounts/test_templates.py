"""
Unit tests for authentication templates.

These tests verify that templates are correctly updated for Google OAuth
and that Facebook authentication has been removed.
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class TestLoginTemplate(TestCase):
    """
    Unit tests for login template.
    
    **Feature: google-oauth-authentication, Property 6: Facebook UI removal**
    **Validates: Requirements 3.1, 3.3**
    """

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.login_url = reverse('accounts:login')

    def test_facebook_button_removed_from_login(self):
        """
        Test that Facebook authentication button is removed from login page.
        
        **Feature: google-oauth-authentication, Property 6: Facebook UI removal**
        **Validates: Requirements 3.1, 3.3**
        """
        response = self.client.get(self.login_url)
        
        # Verify page loads successfully
        assert response.status_code == 200, \
            f"Login page should return 200, got {response.status_code}"
        
        content = response.content.decode('utf-8')
        
        # Verify Facebook authentication button is NOT present
        assert 'btn-facebook' not in content, \
            "Facebook button class should not be present in login template"
        
        assert 'Continue with Facebook' not in content, \
            "Facebook authentication button text should not be present in login template"

    def test_google_button_present_in_login(self):
        """
        Test that Google button is present and functional in login page.
        
        **Feature: google-oauth-authentication, Property 6: Facebook UI removal**
        **Validates: Requirements 2.1, 3.1**
        """
        response = self.client.get(self.login_url)
        
        # Verify page loads successfully
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Verify Google button is present
        assert 'btn-google' in content, \
            "Google button class should be present in login template"
        
        assert 'Continue with Google' in content, \
            "Google button text should be present in login template"
        
        assert 'fab fa-google' in content, \
            "Google icon should be present in login template"
        
        # Verify Google OAuth URL is present
        assert '/accounts/google/login/' in content, \
            "Google OAuth URL should be present in login template"

    def test_socialaccount_template_tag_loaded(self):
        """
        Test that socialaccount template tag is loaded.
        
        **Feature: google-oauth-authentication, Property 6: Facebook UI removal**
        **Validates: Requirements 2.1**
        """
        response = self.client.get(self.login_url)
        
        # Verify page loads without template errors
        assert response.status_code == 200
        
        # If socialaccount tag is not loaded, the template would fail to render
        # The fact that we get a 200 response means the tag is loaded correctly


class TestRegisterTemplate(TestCase):
    """
    Unit tests for register template.
    
    **Feature: google-oauth-authentication, Property 6: Facebook UI removal**
    **Validates: Requirements 3.2, 3.3**
    """

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.register_url = reverse('accounts:register')

    def test_facebook_button_removed_from_register(self):
        """
        Test that Facebook authentication button is removed from register page.
        
        **Feature: google-oauth-authentication, Property 6: Facebook UI removal**
        **Validates: Requirements 3.2, 3.3**
        """
        response = self.client.get(self.register_url)
        
        # Verify page loads successfully
        assert response.status_code == 200, \
            f"Register page should return 200, got {response.status_code}"
        
        content = response.content.decode('utf-8')
        
        # Verify Facebook authentication button is NOT present
        assert 'btn-facebook' not in content, \
            "Facebook button class should not be present in register template"
        
        assert 'Continue with Facebook' not in content and 'Sign up with Facebook' not in content, \
            "Facebook authentication button text should not be present in register template"

    def test_google_button_present_in_register(self):
        """
        Test that Google button is present and functional in register page.
        
        **Feature: google-oauth-authentication, Property 6: Facebook UI removal**
        **Validates: Requirements 1.1, 3.2**
        """
        response = self.client.get(self.register_url)
        
        # Verify page loads successfully
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Verify Google button is present
        assert 'btn-google' in content, \
            "Google button class should be present in register template"
        
        assert 'Google' in content, \
            "Google text should be present in register template"
        
        assert 'fab fa-google' in content, \
            "Google icon should be present in register template"
        
        # Verify Google OAuth URL is present
        assert '/accounts/google/login/' in content, \
            "Google OAuth URL should be present in register template"
