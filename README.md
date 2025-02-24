# GigSniper - Job Posting Monitor

GigSniper is a powerful tool that monitors career pages for new job postings and notifies users when new opportunities become available.

## Features

- Monitor multiple career pages simultaneously
- Intelligent change detection to identify new job postings
- Web interface for managing monitored pages
- Real-time notifications for new job opportunities
- Efficient scheduling system to periodically check for updates

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```
4. Initialize the database:
   ```bash
   python scripts/init_db.py
   ```
5. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Project Structure

```
gigsniper/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── models/              # Database models
│   ├── services/            # Business logic
│   │   ├── scraper.py      # Web scraping logic
│   │   ├── scheduler.py    # Job scheduling
│   │   ├── comparator.py   # Content comparison
│   │   └── notifier.py     # Notification system
│   ├── templates/          # HTML templates
│   └── static/             # Static files (CSS, JS)
├── scripts/                # Utility scripts
├── tests/                  # Test cases
├── requirements.txt        # Project dependencies
└── .env                    # Environment variables
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 