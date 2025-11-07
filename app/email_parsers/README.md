# Email Booking System

Automated booking creation from broker reservation emails via Gmail API.

## Structure

```
email_parsers/
├── __init__.py           # Package exports
├── base.py               # BaseEmailParser & ParsedBookingData
├── registry.py           # Parser registry
├── gmail_client.py       # Gmail API client
├── processor.py          # Email processing & booking creation
├── example_broker.py     # Example parser template
└── templates/            # Drop email templates here
    └── README.md
```

## Setup Gmail API

1. **Get Gmail API Credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create/select project
   - Enable Gmail API
   - Create OAuth 2.0 Client ID (Desktop app)
   - Download `credentials.json`
   - Place in `/root/backend/credentials.json`

2. **First Authentication:**
   ```bash
   # Will open browser for OAuth consent
   curl -X POST http://localhost:8000/api/email-bookings/process
   ```
   - Token saved to `/root/backend/token.json`
   - Subsequent calls use saved token

## Creating a New Parser

1. **Copy template:**
   ```bash
   cp app/email_parsers/example_broker.py app/email_parsers/discover_cars.py
   ```

2. **Implement methods:**
   - `get_broker_name()` - Return broker name
   - `can_parse()` - Check if email is from this broker
   - `parse()` - Extract booking data

3. **Register parser:**
   ```python
   # In app/email_parsers/__init__.py or startup
   from .discover_cars import DiscoverCarsParser
   from .registry import registry
   
   registry.register(DiscoverCarsParser())
   ```

## API Endpoints

**Process Emails:**
```
POST /api/email-bookings/process?max_emails=10
```

**List Brokers:**
```
GET /api/email-bookings/brokers
```

## Environment Variables

```bash
GMAIL_CREDENTIALS_PATH=/root/backend/credentials.json
GMAIL_TOKEN_PATH=/root/backend/token.json
```

## Testing

Drop email samples in `templates/` folder for parser development.
