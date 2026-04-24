#!/usr/bin/env python
"""
Test script to send email via Mailgun API
This will trigger the webhook and create a Lead/Ticket
"""
import requests
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - Get these from Mailgun Dashboard
MAILGUN_API_KEY = input("Enter your Mailgun API Key (or press Enter to skip): ").strip()
MAILGUN_DOMAIN = "sandbox573cc16dae2146519628c84818af3fe4.mailgun.org"

if not MAILGUN_API_KEY:
    logger.info("\n⚠️  No API key provided. Skipping email send test.")
    logger.info("\nTo get your API key:")
    logger.info("1. Go to https://app.mailgun.com/")
    logger.info("2. Navigate to Settings → API Keys")
    logger.info("3. Copy your Private API key")
    logger.info("\nAlternatively, use the test scripts we already created:")
    logger.info("  - python test_mailgun.py")
    logger.info("  - ./test_mailgun_simple.sh")
    sys.exit(0)

def send_test_email():
    """Send a test email via Mailgun API"""
    logger.info("\n" + "=" * 60)
    logger.info("Sending test email via Mailgun API...")
    logger.info("=" * 60)
    
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
        logger.info(f"\nSending email to: inquiry@{MAILGUN_DOMAIN}")
        logger.info(f"Subject: {data['subject']}")
        
        response = requests.post(
            url,
            auth=("api", MAILGUN_API_KEY),
            data=data,
            timeout=10
        )
        
        logger.info(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ Email sent successfully!")
            logger.info(f"Response: {response.text}")
            logger.info("\n📧 Mailgun will now forward this email to your webhook")
            logger.info("📊 Check your dashboard for the new Lead/Ticket")
        else:
            logger.info(f"❌ Error: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        logger.info(f"\n❌ Error sending email: {e}")
        return False

if __name__ == "__main__":
    logger.info("\n" + "=" * 60)
    logger.info("MAILGUN EMAIL SEND TEST")
    logger.info("=" * 60)
    logger.info("\nThis script sends a real email via Mailgun API")
    logger.info("which will trigger your webhook and create a Lead/Ticket.")
    logger.info("\nNote: You need a Mailgun API key for this to work.")
    logger.info("=" * 60)
    
    send_test_email()
    
    logger.info("\n" + "=" * 60)
    logger.info("Test completed!")
    logger.info("=" * 60)
