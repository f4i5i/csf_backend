#!/usr/bin/env python3
"""Seed waiver templates into the database."""

import asyncio
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.waiver import WaiverTemplate, WaiverType
from core.db import async_session_factory
from core.logging import get_logger, setup_logging, Colors

# Setup logging
setup_logging()
logger = get_logger(__name__)


# Waiver content for each type
WAIVER_CONTENTS = {
    WaiverType.MEDICAL_RELEASE: """
<div class="waiver-content">
    <h2>Medical Release and Authorization</h2>

    <h3>Emergency Medical Treatment</h3>
    <p>
        I hereby authorize the staff of CSF Programs to obtain emergency medical treatment for my child if I cannot be reached.
        I understand that reasonable efforts will be made to contact me before any medical treatment is administered.
    </p>

    <h3>Medical Information</h3>
    <p>
        I authorize CSF Programs to share my child's medical information (including allergies, medications, and medical conditions)
        with emergency medical personnel, coaches, and staff as necessary for my child's safety and well-being.
    </p>

    <h3>Insurance Information</h3>
    <p>
        I understand that I am responsible for all medical expenses incurred as a result of any injury or illness my child
        sustains while participating in CSF Programs activities. I will provide proof of medical insurance coverage upon request.
    </p>

    <h3>Parent/Guardian Responsibilities</h3>
    <ul>
        <li>Ensure all medical information provided is accurate and up-to-date</li>
        <li>Notify CSF Programs immediately of any changes to medical conditions, allergies, or medications</li>
        <li>Provide emergency contact information that is current and reachable</li>
        <li>Ensure my child has necessary medications available (EpiPens, inhalers, etc.)</li>
    </ul>

    <p class="signature-note">
        <strong>By accepting this waiver, I confirm that:</strong>
        <br>• All medical information provided is accurate and complete
        <br>• I authorize emergency medical treatment if I cannot be reached
        <br>• I understand my financial responsibility for medical expenses
    </p>
</div>
""",
    WaiverType.LIABILITY: """
<div class="waiver-content">
    <h2>Release of Liability and Assumption of Risk</h2>

    <h3>Assumption of Risk</h3>
    <p>
        I understand that participation in sports and physical activities involves inherent risks, including but not limited to:
        minor injuries (bruises, cuts, sprains), serious injuries (broken bones, concussions), and in rare cases, catastrophic
        injuries or death. I voluntarily assume all such risks on behalf of my child.
    </p>

    <h3>Release and Waiver</h3>
    <p>
        In consideration of my child being allowed to participate in CSF Programs activities, I hereby release, waive, discharge,
        and covenant not to sue CSF Programs, its owners, directors, employees, coaches, volunteers, and facility owners
        (collectively "Released Parties") from any and all liability, claims, demands, or causes of action arising out of or
        related to any loss, damage, injury, or death that may be sustained by my child or by any property belonging to me or
        my child, whether caused by the negligence of the Released Parties or otherwise, while participating in any CSF Programs
        activities.
    </p>

    <h3>Indemnification</h3>
    <p>
        I agree to indemnify and hold harmless the Released Parties from any loss, liability, damage, or costs that may occur
        as a result of my child's participation in CSF Programs activities, including those caused by the negligent act or
        omission of myself or my child.
    </p>

    <h3>Code of Conduct</h3>
    <p>
        I understand that my child must follow all safety rules and instructions provided by CSF Programs coaches and staff.
        Failure to comply may result in removal from the program without refund. I also understand that:
    </p>
    <ul>
        <li>Participants must wear appropriate athletic attire and footwear</li>
        <li>Bullying, harassment, or violent behavior will not be tolerated</li>
        <li>Parents/guardians must remain on premises during activities for children under 8 years old</li>
        <li>CSF Programs reserves the right to dismiss any participant for conduct violations</li>
    </ul>

    <p class="legal-notice">
        <strong>IMPORTANT:</strong> This waiver affects your legal rights. Please read carefully before accepting.
    </p>

    <p class="signature-note">
        <strong>By accepting this waiver, I confirm that:</strong>
        <br>• I have read and understand this release of liability
        <br>• I voluntarily assume all risks associated with my child's participation
        <br>• I waive my right to sue for injuries or damages
        <br>• This agreement is binding on my heirs, executors, and assigns
    </p>
</div>
""",
    WaiverType.PHOTO_RELEASE: """
<div class="waiver-content">
    <h2>Photo and Video Release Authorization</h2>

    <h3>Media Usage Authorization</h3>
    <p>
        I grant CSF Programs permission to use photographs, video recordings, and other media ("Media") featuring my child
        for promotional and marketing purposes. This includes but is not limited to:
    </p>

    <h3>Permitted Uses</h3>
    <ul>
        <li><strong>Marketing Materials:</strong> Brochures, flyers, posters, advertisements</li>
        <li><strong>Digital Media:</strong> Website, social media platforms (Facebook, Instagram, Twitter, etc.)</li>
        <li><strong>Email Marketing:</strong> Newsletters, promotional emails</li>
        <li><strong>Print Publications:</strong> Local newspapers, magazines, program guides</li>
        <li><strong>Video Content:</strong> Promotional videos, testimonials, class highlights</li>
        <li><strong>Internal Use:</strong> Training materials, presentations, reports</li>
    </ul>

    <h3>Educational and Demonstration Use</h3>
    <p>
        I understand that Media may also be used for educational purposes, including:
    </p>
    <ul>
        <li>Demonstration of proper techniques and form</li>
        <li>Coach training and development</li>
        <li>Program quality improvement</li>
        <li>Student progress documentation (shared only with parents/guardians)</li>
    </ul>

    <h3>Rights and Restrictions</h3>
    <p>
        I understand that:
    </p>
    <ul>
        <li>I will not receive compensation for the use of Media</li>
        <li>CSF Programs owns all rights to the Media</li>
        <li>My child's name may or may not be used in connection with the Media</li>
        <li>I waive any right to inspect or approve the finished product</li>
        <li>Media may be retained indefinitely by CSF Programs</li>
    </ul>

    <h3>Opt-Out Option</h3>
    <p>
        <strong>If you do NOT wish to grant photo/video permission, please email us at privacy@csfprograms.com immediately
        after enrollment.</strong> We will mark your child's account accordingly and ensure they are not included in any Media.
    </p>

    <p class="privacy-note">
        <strong>Privacy Protection:</strong> We never share personal information (name, address, school, etc.) publicly
        alongside Media without explicit written consent. Social media posts will use first names only or no names at all.
    </p>

    <p class="signature-note">
        <strong>By accepting this waiver, I confirm that:</strong>
        <br>• I grant CSF Programs permission to use Media featuring my child
        <br>• I understand the permitted uses outlined above
        <br>• I waive any right to compensation or approval
        <br>• I understand I can opt out by contacting CSF Programs
    </p>
</div>
""",
    WaiverType.CANCELLATION_POLICY: """
<div class="waiver-content">
    <h2>Cancellation and Refund Policy</h2>

    <h3>15-Day Full Refund Period</h3>
    <p>
        CSF Programs offers a <strong>15-day satisfaction guarantee</strong>. If you are not completely satisfied with our
        program, you may cancel within 15 days of your enrollment date for a <strong>full refund</strong> of all fees paid.
    </p>

    <h4>How the 15-Day Period Works:</h4>
    <ul>
        <li>The 15-day period begins on the date you complete enrollment and payment</li>
        <li>You must submit your cancellation request in writing (email acceptable) before the 15-day period expires</li>
        <li>Refunds will be processed within 5-7 business days to your original payment method</li>
        <li><strong>No processing fees or deductions</strong> will be applied to refunds within this period</li>
    </ul>

    <h3>Cancellations After 15 Days</h3>
    <p>
        <strong>After the 15-day period expires, all payments are non-refundable.</strong> This policy applies to:
    </p>
    <ul>
        <li>One-time class payments</li>
        <li>Installment plans (remaining installments will still be due)</li>
        <li>Monthly membership subscriptions</li>
    </ul>

    <h4>Special Circumstances:</h4>
    <p>
        Exceptions to the no-refund policy may be made at CSF Programs' sole discretion in cases of:
    </p>
    <ul>
        <li>Documented medical emergencies preventing participation</li>
        <li>Family relocation outside the service area (proof required)</li>
        <li>Program cancellation or significant schedule changes initiated by CSF Programs</li>
    </ul>

    <h3>Subscription Cancellation</h3>
    <p>
        For monthly recurring subscriptions:
    </p>
    <ul>
        <li>You may cancel at any time after the initial 15-day period</li>
        <li>Cancellation must be submitted at least 3 business days before your next billing date</li>
        <li>You will have access to the program through the end of your current billing cycle</li>
        <li>No refunds will be issued for partial months</li>
        <li>You may re-enroll at any time (subject to class availability)</li>
    </ul>

    <h3>Class Transfers</h3>
    <p>
        Instead of canceling, you may request a transfer to a different class or program:
    </p>
    <ul>
        <li><strong>Within 15 days:</strong> Free transfer to any available class of equal or lesser value</li>
        <li><strong>After 15 days:</strong> One-time transfer allowed with $25 administrative fee</li>
        <li>Transfer requests are subject to availability and age/skill requirements</li>
        <li>Price differences must be paid before transfer is finalized</li>
    </ul>

    <h3>CSF-Initiated Cancellations</h3>
    <p>
        If CSF Programs must cancel a class due to low enrollment, facility issues, or other circumstances:
    </p>
    <ul>
        <li>You will receive <strong>full refund</strong> of all payments made</li>
        <li>Or, you may transfer to another class of equal value at no charge</li>
        <li>We will provide at least 7 days notice when possible</li>
    </ul>

    <h3>Weather and Emergency Closures</h3>
    <ul>
        <li>Classes missed due to weather or emergencies will be rescheduled when possible</li>
        <li>No refunds or credits are provided for emergency closures</li>
        <li>We will communicate closures via email and text as soon as possible</li>
    </ul>

    <h3>How to Submit a Cancellation Request</h3>
    <p>
        To cancel your enrollment or subscription:
    </p>
    <ol>
        <li>Email <strong>support@csfprograms.com</strong> with "Cancellation Request" in the subject line</li>
        <li>Include: Child's name, class name, enrollment date, and reason for cancellation</li>
        <li>You will receive confirmation within 1 business day</li>
        <li>Refunds (if applicable) will be processed within 5-7 business days</li>
    </ol>

    <p class="policy-note">
        <strong>Note:</strong> Failure to attend classes does not constitute cancellation. You must formally submit a
        cancellation request to stop billing and be eligible for any applicable refunds.
    </p>

    <p class="signature-note">
        <strong>By accepting this waiver, I confirm that:</strong>
        <br>• I have read and understand the cancellation and refund policy
        <br>• I understand the 15-day full refund period
        <br>• I understand that payments are non-refundable after 15 days
        <br>• I will submit cancellation requests in writing within required timeframes
    </p>
</div>
""",
}


async def seed_waivers(db_session: AsyncSession) -> None:
    """Seed waiver templates into the database."""
    logger.info(f"{Colors.BRIGHT_CYAN}🌱 Starting waiver seeding...{Colors.RESET}")

    created_count = 0
    skipped_count = 0

    for waiver_type in WaiverType:
        # Check if waiver already exists for this type
        result = await db_session.execute(
            select(WaiverTemplate).where(
                WaiverTemplate.waiver_type == waiver_type,
                WaiverTemplate.is_active == True
            )
        )
        existing = result.scalars().first()
        
        if existing:
            logger.info(
                f"{Colors.BRIGHT_YELLOW}⚠️  Waiver already exists: {waiver_type.value}{Colors.RESET}"
            )
            skipped_count += 1
            continue

        # Create waiver template
        name = waiver_type.value.replace("_", " ").title()
        content = WAIVER_CONTENTS[waiver_type].strip()

        try:
            waiver = await WaiverTemplate.create_template(
                db_session=db_session,
                name=name,
                waiver_type=waiver_type,
                content=content,
                is_active=True,
                is_required=True,
            )
            logger.info(
                f"{Colors.BRIGHT_GREEN}✅ Created waiver: {waiver.name} (v{waiver.version}){Colors.RESET}"
            )
            created_count += 1

        except Exception as e:
            logger.error(
                f"{Colors.BRIGHT_RED}❌ Failed to create waiver {name}: {e}{Colors.RESET}"
            )
            raise

    logger.info(
        f"\n{Colors.BRIGHT_GREEN}{Colors.BOLD}"
        f"✅ Waiver seeding complete!{Colors.RESET}\n"
        f"   Created: {Colors.BRIGHT_GREEN}{created_count}{Colors.RESET}\n"
        f"   Skipped: {Colors.BRIGHT_YELLOW}{skipped_count}{Colors.RESET}\n"
    )


async def main():
    """Main entry point."""
    try:
        async with async_session_factory() as db_session:
            await seed_waivers(db_session)
    except Exception as e:
        logger.error(f"{Colors.BRIGHT_RED}💥 Seeding failed: {e}{Colors.RESET}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
