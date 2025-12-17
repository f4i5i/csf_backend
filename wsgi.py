"""
WSGI Configuration for PythonAnywhere Deployment

This file configures the FastAPI application to run on Python Anywhere using WSGI.

Setup Instructions:
1. Update 'USERNAME' with your PythonAnywhere username
2. Update paths if you deployed to a different location
3. Configure environment variables in the Environment Variables section
4. Point PythonAnywhere web app to this file
"""

import os
import sys

# ============================================================================
# PATH CONFIGURATION
# ============================================================================

# IMPORTANT: Replace 'USERNAME' with your actual PythonAnywhere username
USERNAME = "YOUR_USERNAME_HERE"

# Project paths
project_home = f'/home/{USERNAME}/csf_backend'
venv_path = f'/home/{USERNAME}/csf_backend/venv'

# Add project directory to Python path
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Add virtual environment site-packages to Python path
site_packages = f'{venv_path}/lib/python3.10/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)


# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================

# Database Configuration
os.environ['DATABASE_URL'] = f'sqlite:////home/{USERNAME}/csf_backend/csf.db'

# Application Settings
os.environ['APP_ENV'] = 'production'
os.environ['DEBUG'] = 'False'
os.environ['SECRET_KEY'] = 'your-secret-key-here-at-least-32-characters-long'

# Stripe Configuration (use test keys for testing, live keys for production)
os.environ['STRIPE_SECRET_KEY'] = 'sk_test_your_stripe_secret_key'
os.environ['STRIPE_PUBLISHABLE_KEY'] = 'pk_test_your_stripe_publishable_key'
os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_your_webhook_secret'

# Email - SendGrid
os.environ['SENDGRID_API_KEY'] = 'your_sendgrid_api_key'
os.environ['SENDGRID_FROM_EMAIL'] = 'noreply@yourdomain.com'

# Email Marketing - Mailchimp (optional)
os.environ['MAILCHIMP_API_KEY'] = ''
os.environ['MAILCHIMP_SERVER_PREFIX'] = ''
os.environ['MAILCHIMP_AUDIENCE_ID'] = ''

# Google OAuth (optional)
os.environ['GOOGLE_CLIENT_ID'] = ''
os.environ['GOOGLE_CLIENT_SECRET'] = ''
os.environ['GOOGLE_REDIRECT_URI'] = 'https://yourusername.pythonanywhere.com/api/v1/auth/google/callback'

# Encryption (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode('utf-8'))")
os.environ['ENCRYPTION_KEY'] = 'your-fernet-encryption-key-here'

# CORS Origins (your frontend URL)
os.environ['CORS_ORIGINS'] = '["https://yourdomain.com"]'

# SMS - Twilio (optional)
os.environ['TWILIO_ACCOUNT_SID'] = ''
os.environ['TWILIO_AUTH_TOKEN'] = ''
os.environ['TWILIO_PHONE_NUMBER'] = ''


# ============================================================================
# APPLICATION IMPORT
# ============================================================================

# Import the FastAPI application
from app.main import app as application

# For debugging - uncomment if you need to see what's happening
# print("Python version:", sys.version)
# print("Python path:", sys.path)
# print("DATABASE_URL:", os.environ.get('DATABASE_URL'))
