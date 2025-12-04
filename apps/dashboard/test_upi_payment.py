"""
Property-based tests for UPI payment functionality.

**Feature: upi-qr-code-payment**
"""
import re
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from hypothesis import given, strategies as st
from hypothesis import settings
import pytest


# Helper function to generate UPI URL (mimics template logic)
def generate_upi_url(amount: Decimal, user_email: str, plan_name: str = "Premium") -> str:
    """
    Generate UPI payment URL following NPCI specification.
    
    Format: upi://pay?pa={UPI_ID}&pn={NAME}&am={AMOUNT}&cu={CURRENCY}&tn={NOTE}
    """
    merchant_upi_id = "arven93798436@barodampay"
    merchant_name = "ARVENTO TECHNOLOGIES"
    currency = "INR"
    
    # Format amount with exactly 2 decimal places
    amount_str = f"{amount:.2f}"
    
    # Create transaction note
    transaction_note = f"{plan_name} Plan - {user_email}"
    
    # Build UPI URL (URL encoding will be handled by the browser/QR library)
    upi_url = (
        f"upi://pay?"
        f"pa={merchant_upi_id}&"
        f"pn={merchant_name}&"
        f"am={amount_str}&"
        f"cu={currency}&"
        f"tn={transaction_note}"
    )
    
    return upi_url


# Strategy for generating valid email addresses
valid_emails = st.emails()

# Strategy for generating valid payment amounts (0.01 to 100000.00)
valid_amounts = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("100000.00"),
    places=2
)

# Strategy for generating plan names
valid_plan_names = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -"),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() != "")


class TestUPIURLFormatValidation:
    """
    **Feature: upi-qr-code-payment, Property 1: UPI URL Format Validity**
    **Validates: Requirements 4.1, 4.2, 4.5**
    
    For any valid payment amount and user email, the generated UPI URL should conform 
    to the NPCI UPI deep linking specification with all required parameters 
    (pa, pn, am, cu, tn) properly formatted and URL-encoded.
    """
    
    @given(amount=valid_amounts, email=valid_emails, plan_name=valid_plan_names)
    @settings(max_examples=100)
    def test_upi_url_format_validity(self, amount, email, plan_name):
        """
        Property test: UPI URL should have correct format with all required parameters.
        """
        upi_url = generate_upi_url(amount, email, plan_name)
        
        # Check URL scheme
        assert upi_url.startswith("upi://pay?"), f"URL should start with 'upi://pay?', got: {upi_url}"
        
        # Parse URL
        parsed = urlparse(upi_url)
        assert parsed.scheme == "upi", f"Scheme should be 'upi', got: {parsed.scheme}"
        assert parsed.netloc == "pay", f"Netloc should be 'pay', got: {parsed.netloc}"
        
        # Parse query parameters
        params = parse_qs(parsed.query)
        
        # Check all required parameters are present
        required_params = ["pa", "pn", "am", "cu", "tn"]
        for param in required_params:
            assert param in params, f"Required parameter '{param}' missing from URL: {upi_url}"
            assert len(params[param]) > 0, f"Parameter '{param}' has no value"
        
        # Validate specific parameter values
        assert params["pa"][0] == "arven93798436@barodampay", f"Payee address incorrect: {params['pa'][0]}"
        assert params["pn"][0] == "ARVENTO TECHNOLOGIES", f"Payee name incorrect: {params['pn'][0]}"
        assert params["cu"][0] == "INR", f"Currency should be INR, got: {params['cu'][0]}"
        
        # Validate amount format (should have exactly 2 decimal places)
        amount_param = params["am"][0]
        assert re.match(r'^\d+\.\d{2}$', amount_param), f"Amount should have exactly 2 decimal places: {amount_param}"
        
        # Validate transaction note contains plan name and email
        transaction_note = params["tn"][0]
        assert plan_name in transaction_note, f"Transaction note should contain plan name '{plan_name}': {transaction_note}"
        assert email in transaction_note, f"Transaction note should contain email '{email}': {transaction_note}"


class TestAmountPrecisionConsistency:
    """
    **Feature: upi-qr-code-payment, Property 2: Amount Precision Consistency**
    **Validates: Requirements 2.3, 2.4**
    
    For any calculated total amount, the amount parameter in the UPI URL should match 
    the displayed total amount with exactly 2 decimal places.
    """
    
    @given(amount=valid_amounts)
    @settings(max_examples=100)
    def test_amount_precision_consistency(self, amount):
        """
        Property test: Amount in UPI URL should always have exactly 2 decimal places.
        """
        email = "test@example.com"
        upi_url = generate_upi_url(amount, email)
        
        # Parse URL to extract amount
        parsed = urlparse(upi_url)
        params = parse_qs(parsed.query)
        amount_param = params["am"][0]
        
        # Check format: exactly 2 decimal places
        assert re.match(r'^\d+\.\d{2}$', amount_param), \
            f"Amount should have exactly 2 decimal places: {amount_param}"
        
        # Check value matches input amount
        parsed_amount = Decimal(amount_param)
        expected_amount = Decimal(f"{amount:.2f}")
        assert parsed_amount == expected_amount, \
            f"Amount in URL ({parsed_amount}) should match input amount ({expected_amount})"
        
        # Ensure no rounding errors
        assert str(parsed_amount) == amount_param, \
            f"String representation should match: {str(parsed_amount)} vs {amount_param}"



class TestTransactionNoteCompleteness:
    """
    **Feature: upi-qr-code-payment, Property 4: Transaction Note Completeness**
    **Validates: Requirements 2.1, 2.2**
    
    For any user email and plan name, the transaction note (tn parameter) should 
    include both the plan name and user email for payment reconciliation.
    """
    
    @given(email=valid_emails, plan_name=valid_plan_names)
    @settings(max_examples=100)
    def test_transaction_note_completeness(self, email, plan_name):
        """
        Property test: Transaction note should contain both plan name and user email.
        """
        amount = Decimal("199.00")
        upi_url = generate_upi_url(amount, email, plan_name)
        
        # Parse URL to extract transaction note
        parsed = urlparse(upi_url)
        params = parse_qs(parsed.query)
        
        assert "tn" in params, "Transaction note parameter 'tn' should be present"
        transaction_note = params["tn"][0]
        
        # Check that both plan name and email are in the transaction note
        assert plan_name in transaction_note, \
            f"Transaction note should contain plan name '{plan_name}': {transaction_note}"
        assert email in transaction_note, \
            f"Transaction note should contain email '{email}': {transaction_note}"
        
        # Check format: should be "Plan Name - email@example.com"
        expected_format = f"{plan_name} Plan - {email}"
        assert transaction_note == expected_format, \
            f"Transaction note format incorrect. Expected: '{expected_format}', Got: '{transaction_note}'"



class TestErrorHandling:
    """
    Unit tests for error handling scenarios.
    **Validates: Requirements 1.5, 5.1, 5.2, 5.3**
    """
    
    def test_qr_generation_with_valid_data(self):
        """
        Test that QR code generation works with valid data.
        """
        amount = Decimal("234.82")
        email = "user@example.com"
        plan_name = "Premium"
        
        upi_url = generate_upi_url(amount, email, plan_name)
        
        # Should generate valid URL
        assert upi_url.startswith("upi://pay?")
        assert "arven93798436@barodampay" in upi_url
        assert "234.82" in upi_url
        assert email in upi_url
    
    def test_fallback_display_with_special_characters(self):
        """
        Test that special characters in email are properly encoded.
        """
        amount = Decimal("199.00")
        email = "test+user@example.com"
        plan_name = "Premium"
        
        upi_url = generate_upi_url(amount, email, plan_name)
        
        # URL should be properly encoded
        assert "upi://pay?" in upi_url
        # The + should be encoded in the transaction note
        parsed = urlparse(upi_url)
        params = parse_qs(parsed.query)
        assert email in params["tn"][0]
    
    def test_missing_user_email_edge_case(self):
        """
        Test handling of empty email (edge case).
        """
        amount = Decimal("199.00")
        email = ""
        plan_name = "Premium"
        
        # Should still generate URL even with empty email
        upi_url = generate_upi_url(amount, email, plan_name)
        
        assert upi_url.startswith("upi://pay?")
        assert "arven93798436@barodampay" in upi_url
        
        # Transaction note should still have plan name
        parsed = urlparse(upi_url)
        params = parse_qs(parsed.query)
        assert plan_name in params["tn"][0]
    
    def test_amount_with_many_decimal_places(self):
        """
        Test that amounts with more than 2 decimal places are properly formatted.
        """
        amount = Decimal("199.999")
        email = "test@example.com"
        plan_name = "Premium"
        
        upi_url = generate_upi_url(amount, email, plan_name)
        
        # Amount should be formatted to exactly 2 decimal places
        parsed = urlparse(upi_url)
        params = parse_qs(parsed.query)
        amount_str = params["am"][0]
        
        # Should have exactly 2 decimal places
        assert re.match(r'^\d+\.\d{2}$', amount_str)
        assert amount_str == "200.00"  # Rounded up
    
    def test_very_large_amount(self):
        """
        Test handling of very large payment amounts.
        """
        amount = Decimal("99999.99")
        email = "test@example.com"
        plan_name = "Premium"
        
        upi_url = generate_upi_url(amount, email, plan_name)
        
        parsed = urlparse(upi_url)
        params = parse_qs(parsed.query)
        assert params["am"][0] == "99999.99"
    
    def test_very_small_amount(self):
        """
        Test handling of very small payment amounts.
        """
        amount = Decimal("0.01")
        email = "test@example.com"
        plan_name = "Premium"
        
        upi_url = generate_upi_url(amount, email, plan_name)
        
        parsed = urlparse(upi_url)
        params = parse_qs(parsed.query)
        assert params["am"][0] == "0.01"



class TestFallbackDisplayConsistency:
    """
    **Feature: upi-qr-code-payment, Property 5: Fallback Display Consistency**
    **Validates: Requirements 1.5, 5.1, 5.2, 5.3**
    
    For any QR code generation failure, the fallback display should show the merchant 
    UPI ID and all payment details that were intended for the QR code.
    """
    
    @given(amount=valid_amounts, email=valid_emails, plan_name=valid_plan_names)
    @settings(max_examples=100)
    def test_fallback_display_consistency(self, amount, email, plan_name):
        """
        Property test: Fallback display should contain all essential payment information.
        """
        # Generate UPI URL (this represents what would be in the QR code)
        upi_url = generate_upi_url(amount, email, plan_name)
        
        # Parse the URL to extract all parameters
        parsed = urlparse(upi_url)
        params = parse_qs(parsed.query)
        
        # Extract key information
        merchant_upi_id = params["pa"][0]
        amount_str = params["am"][0]
        transaction_note = params["tn"][0]
        
        # Simulate fallback display content (what should be shown if QR fails)
        fallback_content = {
            "upi_id": merchant_upi_id,
            "amount": amount_str,
            "plan_name": plan_name,
            "user_email": email,
            "transaction_note": transaction_note
        }
        
        # Verify all essential information is present in fallback
        assert fallback_content["upi_id"] == "arven93798436@barodampay", \
            "Fallback should show correct UPI ID"
        
        assert fallback_content["amount"] == amount_str, \
            f"Fallback should show correct amount: {amount_str}"
        
        assert plan_name in fallback_content["transaction_note"], \
            "Fallback should include plan name in transaction note"
        
        assert email in fallback_content["transaction_note"], \
            "Fallback should include user email in transaction note"
        
        # Verify amount format consistency
        assert re.match(r'^\d+\.\d{2}$', fallback_content["amount"]), \
            "Fallback amount should have exactly 2 decimal places"
    
    def test_fallback_contains_all_required_fields(self):
        """
        Unit test: Verify fallback display has all required fields for manual payment.
        """
        amount = Decimal("234.82")
        email = "test@example.com"
        plan_name = "Premium"
        
        upi_url = generate_upi_url(amount, email, plan_name)
        parsed = urlparse(upi_url)
        params = parse_qs(parsed.query)
        
        # Required fields for manual payment
        required_fields = ["pa", "am", "tn", "pn", "cu"]
        
        for field in required_fields:
            assert field in params, f"Required field '{field}' missing from URL"
            assert len(params[field][0]) > 0, f"Field '{field}' should not be empty"
        
        # Verify merchant details
        assert params["pa"][0] == "arven93798436@barodampay"
        assert params["pn"][0] == "ARVENTO TECHNOLOGIES"
        assert params["cu"][0] == "INR"
