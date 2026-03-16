#!/usr/bin/env python
"""
Test script to send email via Mailgun API
This will trigger the webhook and create a Lead/Ticket
"""
import requests
import sys

# Configuration - Get these from Mailgun Dashboard
MAILGUN_API_KEY = input("Enter your Mailgun API Key (or press Enter to skip): ").strip()
MAILGUN_DOMAIN = "sandbox573cc16dae2146519628c84818af3fe4.mailgun.org"

if not MAILGUN_API_KEY:
    print("\n⚠️  No API key provided. Skipping email send test.")
    print("\nTo get your API key:")
    print("1. Go to https://app.mailgun.com/")
    print("2. Navigate to Settings → API Keys")
    print("3. Copy your Private API key")
    print("\nAlternatively, use the test scripts we already created:")
    print("  - python test_mailgun.py")
    print("  - ./test_mailgun_simple.sh")
    sys.exit(0)

def send_test_email():
    """Send a test email via Mailgun API"""
    print("\n" + "=" * 60)
    print("Sending test email via Mailgun API...")
    print("=" * 60)
    
    url = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"
    
    data = {
        "from": "Test Customer <test@example.com>",
        "to": f"inquiry@{MAILGUN_DOMAIN}",  # This will trigger webhook
        "subject": "Product Inquiry - Test Email",
        "text": """Hello,

I am interested in learning more about your product. 
Please contact me at your earliest convenience.

Best regards,
Test Customer
Phone: +1-555-123-4567
"""
    }
    
    try:
        print(f"\nSending email to: inquiry@{MAILGUN_DOMAIN}")
        print(f"Subject: {data['subject']}")
        
        response = requests.post(
            url,
            auth=("api", MAILGUN_API_KEY),
            data=data,
            timeout=10
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Email sent successfully!")
            print(f"Response: {response.text}")
            print("\n📧 Mailgun will now forward this email to your webhook")
            print("📊 Check your dashboard for the new Lead/Ticket")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error sending email: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MAILGUN EMAIL SEND TEST")
    print("=" * 60)
    print("\nThis script sends a real email via Mailgun API")
    print("which will trigger your webhook and create a Lead/Ticket.")
    print("\nNote: You need a Mailgun API key for this to work.")
    print("=" * 60)
    
    send_test_email()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
