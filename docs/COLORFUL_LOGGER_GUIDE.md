# Colorful Logger - User Guide

## Overview

The CSF Backend now features a **colorful logging system** with ANSI colors and emoji icons for better readability and visual distinction between log levels.

---

## Features

✅ **Color-Coded Log Levels**
- DEBUG: 🔍 Cyan
- INFO: ℹ️ Green
- WARNING: ⚠️ Yellow
- ERROR: ❌ Red
- CRITICAL: 💥 Red background

✅ **Enhanced Readability**
- Timestamps in dim gray
- Filenames in cyan
- Line numbers in magenta
- Custom formatting with box-drawing characters

✅ **Smart Color Detection**
- Automatically detects TTY (terminal) environments
- Disables colors in non-interactive environments (CI/CD, logs to file)
- Works in VS Code, PyCharm, Terminal, iTerm2, etc.

✅ **Beautiful Startup Banner**
- Shows when application starts
- Displays current log level
- Eye-catching design

---

## Color Scheme

### Log Levels

| Level | Icon | Color | When to Use |
|-------|------|-------|-------------|
| **DEBUG** | 🔍 | Bright Cyan | Development, detailed troubleshooting |
| **INFO** | ℹ️ | Bright Green | General information, successful operations |
| **WARNING** | ⚠️ | Bright Yellow | Unexpected situations, deprecations |
| **ERROR** | ❌ | Bright Red | Errors that don't crash the app |
| **CRITICAL** | 💥 | White on Red | Severe errors, potential crash |

### Other Elements

| Element | Color | Example |
|---------|-------|---------|
| Timestamp | Dim Gray | `2025-12-14 10:30:45` |
| Separator | Default | `│` |
| Filename | Cyan | `classes.py` |
| Line Number | Magenta | `142` |
| Message | Default | Your log message |

---

## Visual Examples

### Startup Banner

```
╔══════════════════════════════════════════════════════════════╗
║     🚀 CSF Backend - Colorful Logging Initialized 🎨       ║
║     Log Level: INFO                                          ║
╚══════════════════════════════════════════════════════════════╝
```

### Log Output Format

```
2025-12-14 10:30:45 │ ℹ️  INFO     │ classes.py:142 │ Class created successfully
2025-12-14 10:30:46 │ ⚠️  WARNING  │ auth.py:58     │ Rate limit approaching
2025-12-14 10:30:47 │ ❌ ERROR    │ payments.py:91 │ Payment failed: card declined
```

---

## Usage

### Basic Logging

```python
from core.logging import get_logger

logger = get_logger(__name__)

# Different log levels
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error!")
```

### With Context Information

```python
logger.info(f"User {user_id} logged in successfully")
logger.warning(f"Rate limit at {usage}% for user {user_id}")
logger.error(f"Failed to create class {class_id}: {error_message}")
```

### Adding Custom Colors in Messages

```python
from core.logging import get_logger, Colors

logger = get_logger(__name__)

# Highlight important information
logger.info(
    f"User {Colors.BRIGHT_YELLOW}{user.email}{Colors.RESET} logged in"
)

# Emphasize errors
logger.error(
    f"Payment failed: {Colors.BRIGHT_RED}{error.code}{Colors.RESET}"
)

# Success messages
logger.info(
    f"{Colors.BRIGHT_GREEN}✅ Payment processed successfully!{Colors.RESET}"
)
```

---

## Configuration

### Log Levels

Set the log level via environment variable:

```bash
# Development - see everything
export LOG_LEVEL=DEBUG

# Production - info and above
export LOG_LEVEL=INFO

# Quiet - warnings and errors only
export LOG_LEVEL=WARNING
```

### Enable/Disable SQL Logging

SQL logging is automatically enabled when `LOG_LEVEL=DEBUG`:

```bash
# Enable SQL logging
export LOG_LEVEL=DEBUG

# Disable SQL logging
export LOG_LEVEL=INFO
```

---

## Color Class Reference

### Foreground Colors

```python
from core.logging import Colors

Colors.BLACK
Colors.RED
Colors.GREEN
Colors.YELLOW
Colors.BLUE
Colors.MAGENTA
Colors.CYAN
Colors.WHITE

# Bright variants
Colors.BRIGHT_BLACK
Colors.BRIGHT_RED
Colors.BRIGHT_GREEN
Colors.BRIGHT_YELLOW
Colors.BRIGHT_BLUE
Colors.BRIGHT_MAGENTA
Colors.BRIGHT_CYAN
Colors.BRIGHT_WHITE
```

### Background Colors

```python
Colors.BG_BLACK
Colors.BG_RED
Colors.BG_GREEN
Colors.BG_YELLOW
Colors.BG_BLUE
Colors.BG_MAGENTA
Colors.BG_CYAN
Colors.BG_WHITE
```

### Text Styles

```python
Colors.BOLD      # Bold text
Colors.DIM       # Dimmed text
Colors.RESET     # Reset to default
```

---

## Examples

### Example 1: API Request Logging

```python
from core.logging import get_logger, Colors

logger = get_logger(__name__)

@router.post("/classes")
async def create_class(data: ClassCreate):
    logger.info(f"📥 Received class creation request: {data.name}")

    try:
        class_obj = await Class.create_class(db_session, **data.dict())
        logger.info(
            f"{Colors.BRIGHT_GREEN}✅ Class created successfully:{Colors.RESET} "
            f"id={class_obj.id}, name={class_obj.name}"
        )
        return class_obj
    except Exception as e:
        logger.error(
            f"{Colors.BRIGHT_RED}❌ Failed to create class:{Colors.RESET} {str(e)}"
        )
        raise
```

**Output:**
```
2025-12-14 10:30:45 │ ℹ️  INFO  │ classes.py:87  │ 📥 Received class creation request: Elite Karate
2025-12-14 10:30:46 │ ℹ️  INFO  │ classes.py:92  │ ✅ Class created successfully: id=abc123, name=Elite Karate
```

### Example 2: Payment Processing

```python
from core.logging import get_logger, Colors

logger = get_logger(__name__)

async def process_payment(order: Order, payment_method_id: str):
    logger.info(f"💳 Processing payment for order {order.id}")

    try:
        payment = await stripe_service.create_payment(
            amount=order.total_amount,
            payment_method_id=payment_method_id
        )

        logger.info(
            f"{Colors.BRIGHT_GREEN}💰 Payment successful:{Colors.RESET} "
            f"${payment.amount} charged"
        )

        return payment

    except stripe.CardError as e:
        logger.error(
            f"{Colors.BRIGHT_RED}💳 Card declined:{Colors.RESET} {e.code}"
        )
        raise
    except Exception as e:
        logger.critical(
            f"{Colors.BG_RED}{Colors.WHITE}💥 Payment system error:{Colors.RESET} {str(e)}"
        )
        raise
```

**Output:**
```
2025-12-14 10:30:45 │ ℹ️  INFO     │ payments.py:45  │ 💳 Processing payment for order order_123
2025-12-14 10:30:46 │ ℹ️  INFO     │ payments.py:53  │ 💰 Payment successful: $99.00 charged
```

### Example 3: Error Handling

```python
from core.logging import get_logger, Colors

logger = get_logger(__name__)

try:
    result = await dangerous_operation()
except ValueError as e:
    logger.warning(f"⚠️  Invalid input: {e}")
except PermissionError as e:
    logger.error(f"🔒 Permission denied: {e}")
except Exception as e:
    logger.critical(
        f"{Colors.BOLD}{Colors.BG_RED}💥 Unexpected error:{Colors.RESET} {e}"
    )
    raise
```

---

## Best Practices

### 1. Use Appropriate Log Levels

```python
# ✅ Good
logger.debug("SQL query: SELECT * FROM users WHERE id = 123")
logger.info("User logged in successfully")
logger.warning("Rate limit at 90%")
logger.error("Database connection failed, retrying...")
logger.critical("Database unreachable, shutting down")

# ❌ Bad
logger.info("SELECT * FROM users WHERE id = 123")  # Too detailed for INFO
logger.error("User logged in")  # Not an error
```

### 2. Add Context

```python
# ✅ Good
logger.info(f"Class {class_id} created by user {user_id}")
logger.error(f"Payment {payment_id} failed: {error_code}")

# ❌ Bad
logger.info("Class created")
logger.error("Payment failed")
```

### 3. Use Emojis Consistently

```python
# Common emoji conventions
logger.info("📥 Received request")
logger.info("📤 Sending response")
logger.info("💾 Saving to database")
logger.info("🔍 Searching for records")
logger.info("✅ Operation successful")
logger.error("❌ Operation failed")
logger.warning("⚠️  Warning condition")
logger.info("💳 Processing payment")
logger.info("💰 Payment received")
logger.info("📧 Sending email")
logger.info("🔐 Authenticating user")
```

### 4. Highlight Important Data

```python
# Use colors to emphasize key information
logger.info(
    f"User {Colors.BRIGHT_YELLOW}{user.email}{Colors.RESET} "
    f"created {Colors.BRIGHT_CYAN}{class_count}{Colors.RESET} classes"
)
```

### 5. Avoid Logging Sensitive Data

```python
# ❌ Bad - logs PII
logger.info(f"User credit card: {card_number}")
logger.debug(f"Password: {password}")

# ✅ Good - safe logging
logger.info(f"User payment method: {card_brand} ending in {last_four}")
logger.debug("User authenticated successfully")
```

---

## Troubleshooting

### Colors Not Showing

**Problem:** Colors appear as codes like `[92m` instead of colors.

**Solution:**
1. Ensure running in a terminal (TTY)
2. Check terminal supports ANSI colors
3. Try setting: `export TERM=xterm-256color`

### Too Verbose Logs

**Problem:** Too many log messages.

**Solution:**
```bash
# Set higher log level
export LOG_LEVEL=WARNING

# Or in production
export LOG_LEVEL=ERROR
```

### SQL Logs Showing Sensitive Data

**Problem:** SQL logs contain PII.

**Solution:**
```bash
# Never use DEBUG in production
export LOG_LEVEL=INFO
```

---

## Production Considerations

### 1. Log Level

Use `INFO` or `WARNING` in production:

```bash
export LOG_LEVEL=INFO
```

### 2. Log Aggregation

Colors work best in terminals. For log aggregation services:
- Colors are automatically disabled in non-TTY environments
- Plain text logs are sent to services like DataDog, Sentry, etc.

### 3. Performance

The colorful logger has minimal overhead:
- Color formatting only applied when outputting
- ANSI codes are lightweight
- No performance impact on business logic

---

## Advanced Usage

### Custom Color Schemes

Create your own color schemes:

```python
from core.logging import Colors

# Define custom colors for your domain
class AppColors:
    SUCCESS = Colors.BRIGHT_GREEN
    FAILURE = Colors.BRIGHT_RED
    PAYMENT = Colors.BRIGHT_YELLOW
    USER_ACTION = Colors.BRIGHT_CYAN

logger.info(f"{AppColors.SUCCESS}✅ Registration complete{Colors.RESET}")
logger.info(f"{AppColors.PAYMENT}💳 Processing payment{Colors.RESET}")
```

### Conditional Coloring

```python
from core.logging import Colors

def format_status(status: str) -> str:
    colors = {
        "success": Colors.BRIGHT_GREEN,
        "pending": Colors.BRIGHT_YELLOW,
        "failed": Colors.BRIGHT_RED,
    }
    color = colors.get(status, Colors.WHITE)
    return f"{color}{status.upper()}{Colors.RESET}"

logger.info(f"Payment status: {format_status('success')}")
```

---

## Testing

### Test All Log Levels

```python
# Run the demo
uv run python -c "
import os
os.environ['LOG_LEVEL'] = 'DEBUG'

from core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger('test')

logger.debug('Debug message')
logger.info('Info message')
logger.warning('Warning message')
logger.error('Error message')
logger.critical('Critical message')
"
```

---

## Summary

✅ **Beautiful** - Color-coded logs with emojis
✅ **Smart** - Auto-detects terminal capabilities
✅ **Flexible** - Customizable colors and formats
✅ **Safe** - Disables in non-TTY environments
✅ **Fast** - Minimal performance overhead
✅ **Production-Ready** - Works in all environments

The colorful logger makes development more enjoyable and production debugging more efficient! 🎨

---

**Last Updated:** 2025-12-14
**Version:** 1.0
**Status:** ✅ Production Ready
