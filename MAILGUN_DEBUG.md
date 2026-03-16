# Mailgun Webhook Debugging Guide

## Testing the Webhook

### 1. Test Endpoint
First, test if the webhook endpoint is accessible:
- URL: `http://yourdomain.com/webhook/mailgun/test/`
- This endpoint shows you exactly what Mailgun is sending

### 2. Check Logs
When the webhook is called, check your Django console/logs for:
- POST keys received
- Extracted email data
- Any errors

### 3. Common Issues

#### Issue: Webhook not being called
- Check Mailgun dashboard → Routes → Your route
- Verify the webhook URL is correct: `https://yourdomain.com/webhook/mailgun/`
- Make sure your server is accessible from the internet (use ngrok for local testing)

#### Issue: Signature verification failing
- The webhook now logs warnings but doesn't fail
- Check that `MAILGUN_WEBHOOK_KEY` in settings.py matches your Mailgun webhook signing key

#### Issue: No sender email found
- Check the test endpoint to see what fields Mailgun is sending
- The webhook tries multiple field names: `sender`, `From`, `message-headers`

### 4. Mailgun Route Setup

In Mailgun Dashboard:
1. Go to **Receiving** → **Routes**
2. Create a new route or edit existing
3. Set **Expression**: `match_recipient(".*@yourdomain.com")`
4. Set **Action**: `forward("https://yourdomain.com/webhook/mailgun/")`
5. Save

### 5. Testing Locally

If testing locally, use ngrok:
```bash
# Terminal 1: Run Django
python manage.py runserver

# Terminal 2: Run ngrok
ngrok http 8000

# Use the ngrok URL in Mailgun: https://xxxxx.ngrok.io/webhook/mailgun/
```

### 6. Manual Test

You can manually test the webhook using curl:
```bash
curl -X POST http://localhost:8000/webhook/mailgun/ \
  -d "sender=test@example.com" \
  -d "subject=Test Email" \
  -d "body-plain=This is a test email body" \
  -d "signature=test" \
  -d "token=test" \
  -d "timestamp=1234567890"
```

## Expected Behavior

When an email is received:
1. Mailgun sends POST request to `/webhook/mailgun/`
2. System extracts: sender, subject, body
3. Creates or finds Lead with that email
4. Creates Ticket linked to Lead
5. Logs activity
6. Returns "OK" status

Check your dashboard to see the new Lead and Ticket!
