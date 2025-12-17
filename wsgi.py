"""
WSGI Configuration for PythonAnywhere Deployment

This file configures the FastAPI application to run on PythonAnywhere using WSGI.

Setup Instructions:
1. Update 'USERNAME' with your PythonAnywhere username
2. Create a .env file in the project root with all environment variables
3. Point PythonAnywhere web app to this file
4. Reload the web app
"""

import os
import sys

# ============================================================================
# PATH CONFIGURATION
# ============================================================================

# IMPORTANT: Replace 'USERNAME' with your actual PythonAnywhere username
USERNAME = "f4i5i"

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
# ENVIRONMENT VARIABLES - Load from .env file
# ============================================================================

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = os.path.join(project_home, '.env')
load_dotenv(env_path)

# Override DATABASE_URL for PythonAnywhere if needed
# (Uncomment if you want to override the .env setting)
# os.environ['DATABASE_URL'] = f'sqlite:////home/{USERNAME}/csf_backend/csf.db'

# Override APP_ENV for production
os.environ['APP_ENV'] = 'production'


# ============================================================================
# APPLICATION IMPORT
# ============================================================================

# Import the FastAPI application
from app.main import app as application

# For debugging - uncomment if you need to see what's happening
# print("Python version:", sys.version)
# print("Python path:", sys.path)
# print("DATABASE_URL:", os.environ.get('DATABASE_URL'))
