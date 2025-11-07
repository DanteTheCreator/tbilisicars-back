# Email Parser Templates

Drop your broker email templates here. Each template should be a sample email showing the format that the parser needs to handle.

## Template Format

Save templates as `.txt` files with descriptive names:
- `booking-com-reservation.txt`
- `expedia-confirmation.txt`
- `kayak-booking.txt`
- etc.

## Example Template Structure

```
Subject: Booking Confirmation #12345
From: noreply@broker.com

Dear Partner,

New reservation details:

Customer: John Doe
Email: john@example.com
Phone: +1234567890

Pickup: 2025-11-01 10:00 at Airport Location
Dropoff: 2025-11-05 10:00 at Airport Location

Vehicle: Toyota Camry (Midsize)
Total: $250.00

Reference: BR123456
```

These templates will help in developing and testing the parsers.
