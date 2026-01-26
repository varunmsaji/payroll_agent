---
title: Hrms Backend Latest
emoji: 🐠
colorFrom: indigo
colorTo: gray
sdk: docker
pinned: false
short_description: this is for the hrms backend code
---

# 🏢 HRMS Payroll Backend

[![CI Pipeline](https://github.com/varunmsaji/payroll_agent/actions/workflows/ci.yml/badge.svg)](https://github.com/varunmsaji/payroll_agent/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

FastAPI-based HR Management System backend with face recognition attendance, payroll processing, and automated workflows.

## 🚀 Features

- 👤 Face Recognition for Attendance
- 📊 Automated Payroll Processing
- 🔄 Workflow Management
- 📅 Leave Management
- ⏰ Shift Scheduling
- 📈 Dashboard & Analytics
- 🔐 Secure Authentication
- 📝 Comprehensive Logging

## 🛠️ Development Setup

### Prerequisites
- Python 3.9 or higher
- PostgreSQL database
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/varunmsaji/payroll_agent.git
   cd payroll_agent/payroll_backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   uvicorn app.api.main:app --reload
   ```

6. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Alternative Docs: http://localhost:8000/redoc

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api_health.py -v

# Run tests by marker
pytest tests/ -m unit -v
```

### Code Quality
```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
ruff check app/ tests/

# Run all quality checks
black --check app/ && isort --check app/ && ruff check app/
```

### Security Scanning
```bash
# Scan for security issues
bandit -r app/

# Check dependencies for vulnerabilities
safety check
```

## 🐳 Docker

### Build Image
```bash
docker build -t payroll-backend .
```

### Run Container
```bash
docker run -p 7860:7860 --env-file .env payroll-backend
```

### Using Docker Compose
```bash
docker-compose up -d
```

## 📝 CI/CD Pipeline

This project uses GitHub Actions for continuous integration:

- ✅ **Code Quality**: Black, isort, Ruff
- 🔒 **Security**: Bandit, Safety
- 🧪 **Testing**: pytest with coverage
- 🐳 **Docker**: Build verification & Trivy scanning

See [.github/workflows/README.md](.github/workflows/README.md) for details.

## 📖 Documentation

- [Logging Usage Guide](LOGGING_USAGE.md) - How to use the logging system
- [Logging Implementation](LOGGING_IMPLEMENTATION.md) - Logging system details
- [CI/CD Pipeline](.github/workflows/README.md) - CI/CD documentation

## 🏗️ Project Structure

```
payroll_backend/
├── app/
│   ├── api/                 # API endpoints
│   ├── database/            # Database models & connections
│   ├── services/            # Business logic
│   └── utils/               # Utilities & helpers
├── tests/                   # Test suite
├── logs/                    # Application logs
├── .github/workflows/       # CI/CD pipelines
├── Dockerfile              # Docker configuration
├── requirements.txt        # Production dependencies
└── requirements-dev.txt    # Development dependencies
```

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Ensure tests pass: `pytest tests/ -v`
4. Ensure code quality: `black app/ && isort app/ && ruff check app/`
5. Create a pull request

All pull requests must pass CI checks before merging.

## 📄 License

© Varun MS Productions

## 🔗 Links

- [Hugging Face Spaces](https://huggingface.co/spaces/varunmsaji01/hrms_backend_latest)
- [Documentation](https://huggingface.co/docs/hub/spaces-config-reference)

