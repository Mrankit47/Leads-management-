#!/usr/bin/env python
"""
Test script to simulate Mailgun webhook requests
"""
import requests
import json
import hmac
import hashlib
import time

# Configuration
WEBHOOK_URL = "http://127.0.0.1:9000/webhook/mailgun/"
TEST_URL = "http://127.0.0.1:9000/webhook/mailgun/test/"
WEBHOOK_KEY = "5178b6f3001f7d5384f5bbc857de857c"

def create_signature(timestamp, token, key):
    """Create Mailgun webhook signature"""
    return hmac.new(
        key=key.encode('utf-8'),
        msg=f'{timestamp}{token}'.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

def test_webhook_test_endpoint():
    """Test the test endpoint first"""
    print("=" * 60)
    print("Testing webhook test endpoint...")
    print("=" * 60)
    
    try:
        response = requests.get(TEST_URL)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure Django server is running: python manage.py runserver")
        return False

def test_mailgun_webhook():
    """Test the actual Mailgun webhook with sample data"""
    print("\n" + "=" * 60)
    print("Testing Mailgun webhook with sample email data...")
    print("=" * 60)
    
    # Sample email data (what Mailgun typically sends)
    timestamp = str(int(time.time()))
    token = "test_token_12345"
    signature = create_signature(timestamp, token, WEBHOOK_KEY)
    
    data = {
        'sender': 'test@example.com',
        'From': 'Test User <test@example.com>',
        'subject': 'Product Inquiry - Test Email',  # Contains "Inquiry" - will be processed
        'Subject': 'Product Inquiry - Test Email',
        'body-plain': 'Hello, I am interested in your product. Please contact me.',
        'stripped-text': 'Hello, I am interested in your product. Please contact me.',
        'body-html': '<p>Hello, I am interested in your product. Please contact me.</p>',
        'stripped-html': '<p>Hello, I am interested in your product. Please contact me.</p>',
        'signature': signature,
        'token': token,
        'timestamp': timestamp,
    }
    
    try:
        print(f"\nSending POST request to: {WEBHOOK_URL}")
        print(f"Data being sent:")
        for key, value in data.items():
            if key in ['body-plain', 'body-html', 'stripped-text', 'stripped-html']:
                print(f"  {key}: {value[:50]}...")
            else:
                print(f"  {key}: {value}")
        
        response = requests.post(WEBHOOK_URL, data=data)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! Webhook processed successfully!")
            print("Check your Django console for logs and dashboard for new Lead/Ticket")
        else:
            print(f"\n❌ ERROR: Status code {response.status_code}")
            
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Make sure Django server is running: python manage.py runserver 9000")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

def test_with_different_formats():
    """Test with different Mailgun webhook formats"""
    print("\n" + "=" * 60)
    print("Testing with alternative Mailgun format...")
    print("=" * 60)
    
    timestamp = str(int(time.time()))
    token = "test_token_67890"
    signature = create_signature(timestamp, token, WEBHOOK_KEY)
    
    # Alternative format - just sender, subject, body-plain
    data = {
        'sender': 'customer@example.com',
        'subject': 'Another Test Inquiry',  # Contains "Inquiry" - will be processed
        'body-plain': 'I need help with your service. My phone is +1-555-123-4567',
        'signature': signature,
        'token': token,
        'timestamp': timestamp,
    }
    
    try:
        response = requests.post(WEBHOOK_URL, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_subject_filter():
    """Test that emails without 'Inquiry' in subject are ignored"""
    print("\n" + "=" * 60)
    print("Testing subject filter - email WITHOUT 'Inquiry' should be ignored...")
    print("=" * 60)
    
    timestamp = str(int(time.time()))
    token = "test_token_filter"
    signature = create_signature(timestamp, token, WEBHOOK_KEY)
    
    # Email without "Inquiry" in subject - should be ignored
    data = {
        'sender': 'spam@example.com',
        'subject': 'Regular Email - Not an Inquiry',  # No "Inquiry" - should be ignored
        'body-plain': 'This should be ignored',
        'signature': signature,
        'token': token,
        'timestamp': timestamp,
    }
    
    try:
        response = requests.post(WEBHOOK_URL, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if "ignored" in response.text.lower() or "subject filter" in response.text.lower():
            print("✅ CORRECT: Email was ignored (no 'Inquiry' in subject)")
            print(f"   Response: {response.text}")
            return True
        elif response.text.strip() == "OK":
            print("⚠️  WARNING: Email was processed but should have been ignored")
            print(f"   Response: {response.text}")
            return False
        else:
            print(f"✅ Email filtered correctly. Response: {response.text}")
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MAILGUN WEBHOOK TEST SCRIPT")
    print("=" * 60)
    
    # Test 1: Test endpoint
    if not test_webhook_test_endpoint():
        print("\n⚠️  Test endpoint failed. Check if server is running.")
        exit(1)
    
    # Test 2: Main webhook
    success = test_mailgun_webhook()
    
    # Test 3: Alternative format
    test_with_different_formats()
    
    # Test 4: Subject filter
    test_subject_filter()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Tests completed! Check your dashboard for new leads/tickets.")
        print("📧 Note: Only emails with 'Inquiry' or 'Enquiry' in subject are processed")
    else:
        print("❌ Some tests failed. Check the errors above.")
    print("=" * 60)
