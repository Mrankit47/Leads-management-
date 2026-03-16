# Lead Generation Tracker

A Django-based web application for managing customer inquiries and leads through the sales pipeline.

## Features

- **Public Inquiry Form**: Customers can submit product inquiries without authentication
- **WhatsApp-style Chatbot**: Interactive chatbot widget on the inquiry page for conversational lead capture
- **Email Integration**: Mailgun webhook integration to automatically create tickets from incoming emails
- **Ticket System**: Support tickets linked to leads for better tracking
- **Sales Dashboard**: Sales team can view and manage leads assigned to them
- **Lead Management**: Update lead status through the pipeline (Inquiry → Proposal → Negotiation → Closer → Invoice)
- **Activity Tracking**: All lead updates and status changes are logged
- **Manager Dashboard**: Managers can monitor sales team performance and activities
- **Role-Based Access**: Separate permissions for sales team and managers

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. Create synthetic accounts (sales team and manager):
```bash
python manage.py create_users
```

4. Run the development server:
```bash
python manage.py runserver
```

5. Access the application at `http://127.0.0.1:8000/`

## User Accounts

After running `create_users` command, you'll have:

**Manager:**
- Username: `manager`
- Password: `manager123`

**Sales Team:**
- Username: `sales1`, `sales2`, or `sales3`
- Password: `sales123`

## Lead Status Pipeline

1. **Inquiry** - Initial customer inquiry
2. **Proposal** - Proposal sent to customer
3. **Negotiation** - In negotiation phase
4. **Closer** - Deal is closing
5. **Invoice** - Invoice generated

## Project Structure

```
lead_gen_tracker/
├── leadgen/          # Django project settings
├── leads/            # Main application
│   ├── models.py     # Lead and Activity models
│   ├── views.py      # View functions
│   ├── forms.py      # Django forms
│   ├── urls.py       # URL routing
│   └── templates/    # HTML templates
├── static/           # CSS and JavaScript files
│   ├── css/
│   └── js/
└── manage.py         # Django management script
```

## Usage

1. **Public Users**: Visit the homepage to submit an inquiry form or use the chatbot widget
2. **Sales Team**: Login and access the dashboard to view and update leads
3. **Managers**: Login and access both sales dashboard and manager dashboard for monitoring

## Mailgun Email Integration

The application can automatically create tickets from incoming emails via Mailgun webhooks.

### ⚠️ Important: Sandbox Domain Limitation

**Mailgun sandbox domains CANNOT receive emails from external providers (Gmail, Outlook, etc.)**

The sandbox domain is only for:
- ✅ Testing webhooks (already working - see test results)
- ✅ Sending emails via Mailgun API
- ❌ NOT for receiving emails from Gmail/Outlook

**For production, you need to add your own domain to Mailgun.**

### Setup Instructions:

1. **For Testing (Current Setup)**:
   - ✅ Webhook is already working (tested successfully)
   - ✅ Use test scripts: `python test_mailgun.py`
   - ✅ Or use Mailgun API to send test emails (see `test_send_email_mailgun.py`)

2. **For Production (Real Domain)**:
   - Add your domain to Mailgun Dashboard → Sending → Domains
   - Set up DNS records as instructed by Mailgun
   - Create a Route: Receiving → Routes → Forward to `https://yourdomain.com/webhook/mailgun/`
   - Now external emails (Gmail, etc.) can be sent to your domain

3. **How it works**:
   - When an email is received at your Mailgun domain, it triggers the webhook
   - The system automatically:
     - Creates a new Lead (if email doesn't match existing lead)
     - Creates a Ticket linked to the Lead
     - Logs the activity
   - Email subject becomes the ticket subject
   - Email body becomes the ticket description

4. **Current Configuration**:
   - Webhook Key: Configured in `leadgen/settings.py` as `MAILGUN_WEBHOOK_KEY`
   - Domain: Configured as `MAILGUN_DOMAIN` (sandbox - for testing only)
   - Webhook Endpoint: `/webhook/mailgun/`

### Testing Options:

1. **Local Testing**: Use `python test_mailgun.py` (already working ✅)
2. **Mailgun API**: Use `python test_send_email_mailgun.py` (requires API key)
3. **Production**: Add your own domain to Mailgun

See `MAILGUN_SETUP.md` for detailed instructions.

## Technologies Used

- Python 3.x
- Django 4.2
- HTML/CSS/JavaScript
- SQLite (default database)
