#!/bin/bash
# Simple curl test for Mailgun webhook

echo "=========================================="
echo "Testing Mailgun Webhook"
echo "=========================================="

# Test endpoint
echo ""
echo "1. Testing test endpoint..."
curl -X GET http://127.0.0.1:9000/webhook/mailgun/test/ 2>/dev/null | python3 -m json.tool || echo "Server not running or endpoint not accessible"

echo ""
echo "=========================================="
echo "2. Testing webhook with sample email data..."
echo "=========================================="

# Create a simple POST request simulating Mailgun
curl -X POST http://127.0.0.1:9000/webhook/mailgun/ \
  -d "sender=test@example.com" \
  -d "From=Test User <test@example.com>" \
  -d "subject=Test Product Inquiry" \
  -d "body-plain=Hello, I am interested in your product. Please contact me at +1-555-123-4567" \
  -d "body-html=<p>Hello, I am interested in your product.</p>" \
  -d "signature=test_signature" \
  -d "token=test_token" \
  -d "timestamp=$(date +%s)" \
  -v

echo ""
echo ""
echo "=========================================="
echo "Check Django console for logs"
echo "Check dashboard for new Lead/Ticket"
echo "=========================================="
