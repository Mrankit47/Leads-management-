# Mailgun Subject Filter Configuration

## ✅ Configuration Complete

The system is now configured to **only process emails with "Inquiry" or "Enquiry" in the subject line**.

## How It Works

1. **Email Received**: Mailgun sends webhook when email arrives
2. **Subject Check**: System checks if subject contains "Inquiry" or "Enquiry" (case-insensitive)
3. **Filtered**: If subject doesn't match → Email is ignored (returns OK but doesn't create Lead/Ticket)
4. **Processed**: If subject matches → Creates Lead and Ticket

## Configuration

The filter keywords are configured in `leadgen/settings.py`:

```python
MAILGUN_SUBJECT_FILTER = ['inquiry', 'enquiry']
```

You can modify this list to add more keywords or change them.

## Examples

### ✅ Will Be Processed (Creates Lead/Ticket):
- "Product Inquiry"
- "INQUIRY about your service"
- "Customer Enquiry Form"
- "New Inquiry: Product Information"

### ❌ Will Be Ignored (No Lead/Ticket Created):
- "Regular Email"
- "Newsletter"
- "Spam Message"
- "General Question"

## Testing

Test the filter:

```bash
# This will be IGNORED (no "Inquiry" in subject)
curl -X POST http://127.0.0.1:9000/webhook/mailgun/ \
  -d "sender=test@example.com" \
  -d "subject=Regular Email" \
  -d "body-plain=Test"

# Response: "OK - Email ignored (subject filter)"

# This will be PROCESSED (contains "Inquiry")
curl -X POST http://127.0.0.1:9000/webhook/mailgun/ \
  -d "sender=test@example.com" \
  -d "subject=Product Inquiry" \
  -d "body-plain=Test"

# Response: "OK" (Lead and Ticket created)
```

Or use the test script:
```bash
python test_mailgun.py
```

## Mailgun Route Setup

To ensure only inquiry emails are processed, you can also set up a Mailgun Route filter:

1. Go to Mailgun Dashboard → Receiving → Routes
2. Create route with expression: `match_header("subject", ".*[Ii]nquiry.*")`
3. Action: Forward to `https://yourdomain.com/webhook/mailgun/`

This provides double filtering (Mailgun + application level).

## Logs

Check Django console logs to see:
- Which emails were processed
- Which emails were ignored
- Subject lines of all received emails

Example log output:
```
INFO: Email ignored - subject doesn't contain any of ['inquiry', 'enquiry']. Subject: Regular Email
INFO: Email passed subject filter - processing lead/ticket creation
```

## Customization

To change the filter keywords, edit `leadgen/settings.py`:

```python
# Only process emails with these keywords
MAILGUN_SUBJECT_FILTER = ['inquiry', 'enquiry', 'question', 'help']
```

The filter is case-insensitive, so "INQUIRY", "Inquiry", and "inquiry" all work.
