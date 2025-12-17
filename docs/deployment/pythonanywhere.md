# PythonAnywhere Deployment Guide

Complete guide for deploying the CSF Backend to PythonAnywhere Free Tier.

---

## Prerequisites

- PythonAnywhere account (Free tier is sufficient for testing)
- Git repository with your code
- PostgreSQL database with existing data (for migration)
- Basic command-line knowledge

---

## Part 1: Account Setup

### 1.1 Create PythonAnywhere Account

1. Go to https://www.pythonanywhere.com
2. Click "Pricing & signup"
3. Choose "Create a Beginner account" (Free)
4. Complete registration with email verification

### 1.2 Understanding Free Tier Limits

- **Web Apps**: 1 web app
- **Python**: Version 3.10
- **Disk Space**: 512MB
- **Daily CPU**: 100 seconds
- **Domain**: `yourusername.pythonanywhere.com`
- **Always-on Tasks**: 0 (web app runs on-demand)
- **Scheduled Tasks**: 1 per day

---

## Part 2: Repository Setup

### 2.1 Clone Your Repository

Open a Bash console in PythonAnywhere:

```bash
# Navigate to home directory
cd ~

# Clone your repository
git clone https://github.com/yourusername/csf_backend.git
cd csf_backend
```

### 2.2 Create Virtual Environment

```bash
# Create virtual environment
python3.10 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 2.3 Install Dependencies

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Verify installation
pip list
```

**Note**: Installation may take 5-10 minutes on free tier.

---

## Part 3: Database Setup

### 3.1 Create SQLite Database

The SQLite database will be created automatically when you run migrations.

```bash
# Ensure DATABASE_URL is set (will be done in wsgi.py)
export DATABASE_URL="sqlite+aiosqlite:///./csf.db"

# Run migrations to create tables
python -m alembic upgrade head
```

### 3.2 Migrate Data from PostgreSQL

If you have existing data in PostgreSQL:

```bash
# Set PostgreSQL source URL
export POSTGRES_URL="postgresql+asyncpg://user:pass@host:5432/dbname"

# Set SQLite target URL
export SQLITE_URL="sqlite+aiosqlite:///./csf.db"

# Run migration script
python scripts/migrate_postgres_to_sqlite.py
```

The script will:
- Connect to both databases
- Copy all tables in correct order (respecting foreign keys)
- Verify data integrity
- Show progress for each table

**Expected Output**:
```
📊 Source: your-postgres-host:5432/dbname
📊 Target: sqlite+aiosqlite:///./csf.db

⚙️  Migration Steps:
  1. Read data from PostgreSQL
  2. Write data to SQLite
  3. Verify data integrity

Continue with migration? (yes/no): yes

📦 Migrating tables...
============================================================
  📋 Migrating organizations... ✓ (1 records)
  📋 Migrating users... ✓ (45 records)
  📋 Migrating programs... ✓ (8 records)
  ...
============================================================

✨ Migration Summary: 15/15 tables migrated successfully

🔍 Verifying migration...
============================================================
  ✓ organizations                Source:     1 | Target:     1
  ✓ users                        Source:    45 | Target:    45
  ...
============================================================

✅ Migration completed successfully!
```

---

## Part 4: WSGI Configuration

### 4.1 Update wsgi.py

Edit the `wsgi.py` file in your project root:

```bash
nano wsgi.py
```

Update the following sections:

**1. Username** (line 21):
```python
USERNAME = "yourusername"  # Replace with your PythonAnywhere username
```

**2. Environment Variables** (lines 35-68):

Required variables:
```python
# Database
os.environ['DATABASE_URL'] = f'sqlite:////home/{USERNAME}/csf_backend/csf.db'

# Application
os.environ['SECRET_KEY'] = 'your-secret-key-min-32-characters'

# Stripe
os.environ['STRIPE_SECRET_KEY'] = 'sk_test_...'
os.environ['STRIPE_PUBLISHABLE_KEY'] = 'pk_test_...'
os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_...'

# SendGrid
os.environ['SENDGRID_API_KEY'] = 'SG...'
os.environ['SENDGRID_FROM_EMAIL'] = 'noreply@yourdomain.com'

# Encryption (generate with the command in the file)
os.environ['ENCRYPTION_KEY'] = 'your-fernet-key'
```

**Save and exit**: Ctrl+O, Enter, Ctrl+X

### 4.2 Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode('utf-8'))"
```

Copy the output and paste it into the `ENCRYPTION_KEY` variable in wsgi.py.

---

## Part 5: Web App Configuration

### 5.1 Create Web App

1. Go to PythonAnywhere Dashboard
2. Click "Web" tab
3. Click "Add a new web app"
4. Choose "Manual configuration"
5. Select "Python 3.10"

### 5.2 Configure WSGI File

In the Web tab:

1. Scroll to "Code" section
2. Click on the WSGI configuration file link (e.g., `/var/www/yourusername_pythonanywhere_com_wsgi.py`)
3. **Delete all existing content**
4. Add the following:

```python
import sys
import os

# Add your project directory to the path
path = '/home/yourusername/csf_backend'
if path not in sys.path:
    sys.path.insert(0, path)

# Import the WSGI file
from wsgi import application
```

Replace `yourusername` with your actual username.

5. Click "Save"

### 5.3 Configure Virtual Environment

In the Web tab, find "Virtualenv" section:

1. Enter the path: `/home/yourusername/csf_backend/venv`
2. Replace `yourusername` with your actual username

### 5.4 Set Static Files (Optional)

If you have static files:

1. In "Static files" section
2. Add URL: `/static/`
3. Add Directory: `/home/yourusername/csf_backend/static/`

---

## Part 6: Testing & Launch

### 6.1 Reload Web App

1. Scroll to top of Web tab
2. Click green "Reload" button
3. Wait for reload to complete (~10-30 seconds)

### 6.2 Test Your Application

Visit your site:
```
https://yourusername.pythonanywhere.com
```

Test critical endpoints:
- `https://yourusername.pythonanywhere.com/` - Root endpoint
- `https://yourusername.pythonanywhere.com/docs` - API documentation
- `https://yourusername.pythonanywhere.com/api/v1/programs` - List programs

### 6.3 Check Error Logs

If something goes wrong:

1. Go to Web tab
2. Scroll to "Log files" section
3. Click on "Error log" link
4. Check for Python exceptions or errors

Common issues:
- **Import errors**: Check virtual environment path
- **Module not found**: Re-install requirements
- **Database errors**: Check DATABASE_URL in wsgi.py
- **Permission errors**: Check file permissions (chmod 644 for files, 755 for directories)

---

## Part 7: Stripe Webhook Configuration

### 7.1 Setup Stripe Webhooks

1. Go to Stripe Dashboard → Developers → Webhooks
2. Click "Add endpoint"
3. Enter URL: `https://yourusername.pythonanywhere.com/api/v1/webhooks/stripe`
4. Select events to listen for:
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `charge.refunded`

5. Copy the "Signing secret" (starts with `whsec_`)
6. Update `STRIPE_WEBHOOK_SECRET` in wsgi.py
7. Reload web app

### 7.2 Test Webhooks

Use Stripe CLI or trigger test events from Stripe Dashboard:

```bash
# From your local machine with Stripe CLI
stripe trigger payment_intent.succeeded
```

Check logs to verify webhook received:
- PythonAnywhere → Web → Error log
- Look for "Stripe webhook received" messages

---

## Part 8: Environment Variables (Alternative Method)

Instead of hardcoding in wsgi.py, you can use a `.env` file:

### 8.1 Create .env File

```bash
cd ~/csf_backend
nano .env
```

Add your environment variables:
```bash
DATABASE_URL=sqlite:////home/yourusername/csf_backend/csf.db
SECRET_KEY=your-secret-key
STRIPE_SECRET_KEY=sk_test_...
# ... other variables
```

### 8.2 Load in wsgi.py

Update wsgi.py to load from .env:

```python
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(f'/home/{USERNAME}/csf_backend/.env')
```

**Security Note**: Add `.env` to `.gitignore` so secrets aren't committed!

---

## Part 9: Monitoring & Maintenance

### 9.1 Check CPU Usage

Free tier has 100 seconds/day CPU limit.

Monitor usage:
1. Dashboard → Account → CPU usage
2. If exceeding limit, consider:
   - Optimizing slow queries
   - Reducing background tasks
   - Upgrading to paid tier

### 9.2 Database Backups

Backup your SQLite database regularly:

```bash
# Download database file
# Go to Files tab → navigate to csf_backend
# Click on csf.db → Download

# Or use scp from your local machine:
scp yourusername@ssh.pythonanywhere.com:~/csf_backend/csf.db ./backup-$(date +%Y%m%d).db
```

### 9.3 Update Application

When you push code changes:

```bash
cd ~/csf_backend
git pull origin main
source venv/bin/activate
pip install -r requirements.txt  # If dependencies changed
python -m alembic upgrade head   # If migrations added
```

Then reload web app via Web tab.

---

## Part 10: Troubleshooting

### Common Issues

#### "Internal Server Error" (500)
**Check**: Error log for Python exceptions
**Fix**: Usually import errors or missing environment variables

#### "ModuleNotFoundError"
**Check**: Virtual environment configured correctly
**Fix**:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

#### "Database is locked"
**Cause**: SQLite doesn't handle concurrent writes well
**Fix**:
- Reduce concurrent requests
- Consider upgrading to paid tier with PostgreSQL
- Optimize to reduce write operations

#### "Application took too long to respond"
**Cause**: Slow database queries or external API calls
**Fix**:
- Add indexes to frequently queried fields
- Cache expensive operations
- Optimize Stripe/email API calls

#### Stripe Webhooks Not Working
**Check**:
1. Webhook URL is correct
2. SSL certificate valid (PythonAnywhere provides this)
3. Webhook secret matches
4. Check error log for exceptions

**Fix**: Test with Stripe CLI first, then troubleshoot

---

## Part 11: Security Checklist

Before going live:

- [ ] Change SECRET_KEY to a strong random value
- [ ] Use Stripe live keys (not test keys) for production
- [ ] Enable HTTPS only (PythonAnywhere does this automatically)
- [ ] Add your frontend domain to CORS_ORIGINS
- [ ] Backup database regularly
- [ ] Keep dependencies updated (`pip list --outdated`)
- [ ] Monitor error logs weekly
- [ ] Set up Stripe webhook monitoring
- [ ] Test critical user flows (registration, payment, enrollment)

---

## Part 12: Upgrading to Paid Tier

When you outgrow the free tier:

**Consider upgrading if**:
- Exceeding 100 seconds/day CPU
- Need PostgreSQL for better performance
- Need always-on scheduled tasks
- Need more disk space (>512MB)
- Need custom domain

**Paid Tiers**:
- **Hacker** ($5/month): 2 web apps, PostgreSQL, 1GB disk
- **Web Dev** ($12/month): Unlimited web apps, 3GB disk, more CPU

---

## Part 13: Next Steps

After successful deployment:

1. **Frontend Deployment**: Deploy your Next.js frontend (Vercel, Netlify)
2. **Domain Setup**: Configure custom domain (paid tier required)
3. **SSL Certificate**: Auto-provided by PythonAnywhere
4. **Monitoring**: Set up uptime monitoring (UptimeRobot, Pingdom)
5. **Analytics**: Integrate Google Analytics or Plausible
6. **Error Tracking**: Consider Sentry for production error tracking

---

## Support & Resources

- **PythonAnywhere Help**: https://help.pythonanywhere.com/
- **Forums**: https://www.pythonanywhere.com/forums/
- **Email Support**: support@pythonanywhere.com
- **FastAPI Deployment Guide**: https://fastapi.tiangolo.com/deployment/
- **This Project's GitHub**: [Your repository URL]

---

## Appendix: Quick Reference Commands

```bash
# Activate virtual environment
source ~/csf_backend/venv/bin/activate

# Update code from Git
cd ~/csf_backend && git pull

# Install/update dependencies
pip install -r requirements.txt

# Run database migrations
python -m alembic upgrade head

# Check Python version
python --version

# List installed packages
pip list

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode('utf-8'))"

# Backup database
cp csf.db backups/csf-$(date +%Y%m%d).db

# Check database size
du -h csf.db

# View recent error log entries
tail -n 50 /var/log/yourusername.pythonanywhere.com.error.log
```

---

**Last Updated**: December 2025
**Guide Version**: 1.0
**For**: CSF Backend v4.0+

---

Good luck with your deployment! 🚀
