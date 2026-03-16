# Mailgun Email Setup Guide

## ⚠️ Important: Sandbox Domain Limitation

**Mailgun sandbox domains CANNOT receive emails from external providers like Gmail.**

The sandbox domain (`sandbox573cc16dae2146519628c84818af3fe4.mailgun.org`) is only for:
- ✅ Testing webhooks (what we've already done)
- ✅ Sending emails via Mailgun API
- ❌ NOT for receiving emails from Gmail/Outlook/etc.

## Solutions for Testing Email Reception

### Option 1: Use Mailgun API to Send Test Emails (Recommended)

Create a script that uses Mailgun API to send emails, which will trigger your webhook:

```python
# test_send_email.py
import requests

MAILGUN_API_KEY = "YOUR_API_KEY"  # Get from Mailgun Dashboard → Settings → API Keys
MAILGUN_DOMAIN = "sandbox573cc16dae2146519628c84818af3fe4.mailgun.org"

def send_test_email():
    return requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": "test@example.com",
            "to": f"anything@{MAILGUN_DOMAIN}",  # This will trigger webhook
            "subject": "Test Product Inquiry",
            "text": "Hello, I am interested in your product. Please contact me."
        }
    )

response = send_test_email()
print(response.status_code)
print(response.text)
```

### Option 2: Use a Real Domain (Production)

1. **Add your domain to Mailgun**:
   - Go to Mailgun Dashboard → Sending → Domains
   - Click "Add New Domain"
   - Follow DNS setup instructions

2. **Set up Route**:
   - Go to Receiving → Routes
   - Create route: `match_recipient(".*@yourdomain.com")`
   - Action: Forward to `https://yourdomain.com/webhook/mailgun/`

3. **Send emails to your domain**:
   - Now Gmail can send to `anything@yourdomain.com`
   - Mailgun will forward to your webhook

### Option 3: Use Mailgun's Testing Features

Mailgun provides a way to test webhooks without sending real emails:

1. Go to Mailgun Dashboard → Webhooks
2. Use "Send Test Webhook" feature
3. This sends a test POST request to your webhook URL

## Current Status

✅ **Your webhook is working!** (We tested it successfully)
✅ **Leads and Tickets are being created**
✅ **The integration code is correct**

The only limitation is that sandbox domains can't receive external emails.

## Quick Test Using Mailgun API

If you have your Mailgun API key, you can test right now:

```bash
curl -s --user 'api:YOUR_API_KEY' \
    https://api.mailgun.net/v3/sandbox573cc16dae2146519628c84818af3fe4.mailgun.org/messages \
    -F from='test@example.com' \
    -F to='test@sandbox573cc16dae2146519628c84818af3fe4.mailgun.org' \
    -F subject='Test Inquiry' \
    -F text='This is a test email'
```

This will trigger your webhook and create a Lead/Ticket!

## Next Steps

1. **For Development/Testing**: Use the test scripts we created (`test_mailgun.py`)
2. **For Production**: Set up a real domain in Mailgun
3. **For API Testing**: Use Mailgun API to send test emails
