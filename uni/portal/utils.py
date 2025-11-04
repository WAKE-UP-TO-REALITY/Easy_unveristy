import random
from django.conf import settings

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def send_otp_via_sms(mobile_number, otp):
    """
    Send OTP via SMS - Uses console for development
    For production with real SMS, use Indian SMS services like MSG91, Fast2SMS, etc.
    """
    if settings.DEBUG:
        # Development mode - Print OTP to console
        print("\n" + "="*70)
        print(f"📱 OTP MESSAGE")
        print(f"To: {mobile_number}")
        print(f"🔐 Your OTP: {otp}")
        print(f"⏰ Valid for: 5 minutes")
        print(f"Message: Your OTP for University Portal login is: {otp}")
        print("="*70 + "\n")
        return True
    else:
        # Production mode - Use actual SMS service (implement later)
        # For India, use: MSG91, Fast2SMS, Exotel, etc.
        pass

        

def verify_otp(user_otp, stored_otp):
    """Verify if OTP matches"""
    return user_otp == stored_otp

def is_weekend(date):
    """Check if date is Saturday or Sunday"""
    return date.weekday() in [5, 6]  # 5=Saturday, 6=Sunday

 
