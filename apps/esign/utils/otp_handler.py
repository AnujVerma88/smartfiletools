"""
OTP Handler for E-Sign.
Handles OTP generation, verification, and rate limiting.
"""
import random
import hashlib
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class OTPHandler:
    """Handle OTP generation, verification, and rate limiting"""
    
    OTP_LENGTH = 6
    OTP_TTL_MINUTES = getattr(settings, 'ESIGN_OTP_EXPIRY_MINUTES', 5)
    MAX_ATTEMPTS = getattr(settings, 'ESIGN_OTP_MAX_ATTEMPTS', 5)
    RATE_LIMIT_PER_HOUR = getattr(settings, 'ESIGN_OTP_RATE_LIMIT_PER_HOUR', 3)
    
    @staticmethod
    def generate_otp():
        """Generate 6-digit OTP"""
        return ''.join([str(random.randint(0, 9)) for _ in range(OTPHandler.OTP_LENGTH)])
    
    @staticmethod
    def hash_otp(otp_code):
        """Hash OTP for secure storage"""
        return hashlib.sha256(otp_code.encode()).hexdigest()
    
    @staticmethod
    def check_rate_limit(email):
        """
        Check if email has exceeded OTP request rate limit.
        Uses Redis cache for tracking.
        """
        cache_key = f'esign_otp_rate_limit:{email}'
        count = cache.get(cache_key, 0)
        
        if count >= OTPHandler.RATE_LIMIT_PER_HOUR:
            return False, f"Too many OTP requests. Please try again later."
        
        cache.set(cache_key, count + 1, timeout=3600)  # 1 hour
        return True, "OK"
    
    @staticmethod
    def send_otp_email(email, otp_code, session_id):
        """Send OTP via email"""
        subject = 'Your SmartToolPDF e-Sign Verification Code'
        message = f"""
Your verification code for signing the document is:

{otp_code}

This code will expire in {OTPHandler.OTP_TTL_MINUTES} minutes.

If you did not request this code, please ignore this email.

Session ID: {session_id}
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return True, "OTP sent successfully"
        except Exception as e:
            return False, f"Failed to send OTP: {str(e)}"
    
    @staticmethod
    def verify_otp(otp_record, provided_otp):
        """
        Verify provided OTP against stored hash.
        
        Args:
            otp_record: OTP model instance
            provided_otp: OTP code provided by user
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if otp_record.attempts >= otp_record.max_attempts:
            return False, "Maximum attempts exceeded"
        
        if timezone.now() > otp_record.expires_at:
            return False, "OTP expired"
        
        if otp_record.is_verified:
            return False, "OTP already used"
        
        provided_hash = OTPHandler.hash_otp(provided_otp)
        
        if provided_hash == otp_record.otp_hash:
            otp_record.is_verified = True
            otp_record.verified_at = timezone.now()
            otp_record.save()
            return True, "OTP verified successfully"
        else:
            otp_record.attempts += 1
            otp_record.save()
            remaining = otp_record.max_attempts - otp_record.attempts
            return False, f"Invalid OTP. {remaining} attempts remaining"
