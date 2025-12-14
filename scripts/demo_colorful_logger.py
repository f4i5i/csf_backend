#!/usr/bin/env python3
"""Demo script to showcase the colorful logging system."""

import os
import time
from decimal import Decimal

# Set log level to DEBUG to see all messages
os.environ["LOG_LEVEL"] = "DEBUG"

from core.logging import setup_logging, get_logger, Colors

# Initialize logging
setup_logging()

# Get logger
logger = get_logger("ColorfulLoggerDemo")


def demo_basic_levels():
    """Demonstrate all log levels."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}1. BASIC LOG LEVELS{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}\n")

    logger.debug("🔍 This is a DEBUG message - shows detailed development info")
    time.sleep(0.3)

    logger.info("ℹ️  This is an INFO message - general application flow")
    time.sleep(0.3)

    logger.warning("⚠️  This is a WARNING message - something unexpected")
    time.sleep(0.3)

    logger.error("❌ This is an ERROR message - something went wrong")
    time.sleep(0.3)

    logger.critical("💥 This is a CRITICAL message - severe error!")
    time.sleep(0.5)


def demo_api_requests():
    """Demonstrate API request logging."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}2. API REQUEST LOGGING{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}\n")

    logger.info("📥 Received POST /api/v1/classes request")
    time.sleep(0.2)

    logger.debug("🔍 Validating request data: name='Elite Karate', capacity=20")
    time.sleep(0.2)

    logger.info(
        f"{Colors.BRIGHT_GREEN}✅ Class created:{Colors.RESET} "
        f"id=abc123, name=Elite Karate"
    )
    time.sleep(0.2)

    logger.info("📤 Sending 201 Created response")
    time.sleep(0.5)


def demo_payment_processing():
    """Demonstrate payment processing logs."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}3. PAYMENT PROCESSING{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}\n")

    logger.info("💳 Processing payment for order: order_456")
    time.sleep(0.2)

    logger.debug("🔍 Creating Stripe PaymentIntent: amount=9900, currency=usd")
    time.sleep(0.2)

    logger.info(
        f"{Colors.BRIGHT_GREEN}💰 Payment successful:{Colors.RESET} "
        f"${Decimal('99.00')} charged to card ending in 4242"
    )
    time.sleep(0.2)

    logger.info("📧 Sending payment confirmation email")
    time.sleep(0.5)


def demo_error_handling():
    """Demonstrate error scenarios."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}4. ERROR HANDLING{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}\n")

    logger.warning("⚠️  Rate limit approaching: 85% of quota used")
    time.sleep(0.2)

    logger.warning(
        f"⚠️  Slow query detected: {Colors.BRIGHT_YELLOW}1.2s{Colors.RESET} for class listing"
    )
    time.sleep(0.2)

    logger.error("❌ Payment failed: card declined (insufficient_funds)")
    time.sleep(0.2)

    logger.error(
        f"❌ Database connection lost: {Colors.BRIGHT_RED}Connection timeout{Colors.RESET}"
    )
    time.sleep(0.5)


def demo_user_actions():
    """Demonstrate user action logging."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}5. USER ACTIONS{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}\n")

    logger.info("🔐 User authentication attempt")
    time.sleep(0.2)

    logger.info(
        f"✅ User {Colors.BRIGHT_YELLOW}john@example.com{Colors.RESET} logged in successfully"
    )
    time.sleep(0.2)

    logger.info(
        f"👶 Child registered: {Colors.BRIGHT_CYAN}Emily Smith{Colors.RESET} (age: 8)"
    )
    time.sleep(0.2)

    logger.info(
        f"📝 Enrollment created: {Colors.BRIGHT_GREEN}Emily Smith{Colors.RESET} → Elite Karate"
    )
    time.sleep(0.5)


def demo_stripe_integration():
    """Demonstrate Stripe integration logs."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}6. STRIPE INTEGRATION{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}\n")

    logger.info("🎨 Processing payment_options for class creation")
    time.sleep(0.2)

    logger.debug("🔍 Creating Stripe Product: Elite Karate Program")
    time.sleep(0.2)

    logger.info(
        f"{Colors.BRIGHT_GREEN}✅ Stripe Product created:{Colors.RESET} prod_abc123"
    )
    time.sleep(0.2)

    logger.debug("🔍 Creating Stripe Price: $99.00/month")
    time.sleep(0.2)

    logger.info(
        f"{Colors.BRIGHT_GREEN}✅ Stripe Price created:{Colors.RESET} price_xyz789"
    )
    time.sleep(0.2)

    logger.info("💾 Updated class with stripe_product_id")
    time.sleep(0.5)


def demo_subscription_management():
    """Demonstrate subscription management logs."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}7. SUBSCRIPTION MANAGEMENT{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}\n")

    logger.info("🔄 Creating subscription for enrollment: enroll_123")
    time.sleep(0.2)

    logger.debug("🔍 Attaching payment method: pm_card_visa")
    time.sleep(0.2)

    logger.info(
        f"{Colors.BRIGHT_GREEN}✅ Subscription created:{Colors.RESET} "
        f"sub_abc123 (status: active)"
    )
    time.sleep(0.2)

    logger.info("📅 Next billing date: 2025-01-14")
    time.sleep(0.5)


def demo_background_tasks():
    """Demonstrate background task logs."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}8. BACKGROUND TASKS{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}\n")

    logger.info("🔄 Starting installment payment task")
    time.sleep(0.2)

    logger.debug("🔍 Found 15 installments due today")
    time.sleep(0.2)

    logger.info("💳 Processing installment 1/15")
    time.sleep(0.2)

    logger.info(
        f"{Colors.BRIGHT_GREEN}✅ Installment processed:{Colors.RESET} $50.00 charged"
    )
    time.sleep(0.2)

    logger.info(f"📊 Task completed: {Colors.BRIGHT_GREEN}15/15 successful{Colors.RESET}")
    time.sleep(0.5)


def demo_critical_scenarios():
    """Demonstrate critical error scenarios."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}9. CRITICAL SCENARIOS{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'=' * 70}{Colors.RESET}\n")

    logger.warning("⚠️  Database connection pool at 90% capacity")
    time.sleep(0.2)

    logger.error("❌ Failed to connect to Stripe API (attempt 1/3)")
    time.sleep(0.2)

    logger.error("❌ Failed to connect to Stripe API (attempt 2/3)")
    time.sleep(0.2)

    logger.critical(
        f"{Colors.BG_RED}{Colors.WHITE}💥 All connection attempts failed - entering maintenance mode{Colors.RESET}"
    )
    time.sleep(0.5)


def demo_success_summary():
    """Show final success summary."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}DEMO COMPLETE!{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}{'=' * 70}{Colors.RESET}\n")

    logger.info(
        f"{Colors.BOLD}{Colors.BRIGHT_GREEN}✅ Colorful Logging System Working Perfectly!{Colors.RESET}"
    )

    print(f"\n{Colors.BRIGHT_CYAN}Key Features Demonstrated:{Colors.RESET}")
    print(f"  {Colors.BRIGHT_GREEN}✓{Colors.RESET} Color-coded log levels")
    print(f"  {Colors.BRIGHT_GREEN}✓{Colors.RESET} Emoji icons for visual clarity")
    print(f"  {Colors.BRIGHT_GREEN}✓{Colors.RESET} Context highlighting with colors")
    print(f"  {Colors.BRIGHT_GREEN}✓{Colors.RESET} File and line number tracking")
    print(f"  {Colors.BRIGHT_GREEN}✓{Colors.RESET} Timestamp formatting")
    print(f"  {Colors.BRIGHT_GREEN}✓{Colors.RESET} Custom color support\n")


def main():
    """Run the complete demo."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_MAGENTA}")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                                                                  ║")
    print("║           🎨 COLORFUL LOGGER DEMONSTRATION 🎨                    ║")
    print("║                                                                  ║")
    print("║     Showcasing all features of the enhanced logging system      ║")
    print("║                                                                  ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")

    time.sleep(1)

    # Run all demos
    demo_basic_levels()
    demo_api_requests()
    demo_payment_processing()
    demo_error_handling()
    demo_user_actions()
    demo_stripe_integration()
    demo_subscription_management()
    demo_background_tasks()
    demo_critical_scenarios()
    demo_success_summary()

    print(
        f"{Colors.BRIGHT_CYAN}💡 Tip:{Colors.RESET} Check {Colors.BRIGHT_YELLOW}docs/COLORFUL_LOGGER_GUIDE.md{Colors.RESET} for usage examples\n"
    )


if __name__ == "__main__":
    main()
