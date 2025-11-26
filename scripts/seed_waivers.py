"""Seed script to create default waiver templates."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.models.waiver import WaiverTemplate, WaiverType
from core.db import async_session_maker


DEFAULT_WAIVERS = [
    {
        "name": "Medical Release Authorization",
        "waiver_type": WaiverType.MEDICAL_RELEASE,
        "content": """<h2>Medical Release Authorization</h2>
<p>I hereby authorize California Sports Foundation (CSF) and its staff to secure and consent to any medical treatment, including emergency medical care, for my child that may become necessary during participation in any CSF program or event.</p>

<p>I understand that:</p>
<ul>
<li>CSF staff will attempt to contact me or my designated emergency contacts before seeking medical treatment</li>
<li>In the event of an emergency where I cannot be reached, I authorize CSF staff to make medical decisions on behalf of my child</li>
<li>Any medical expenses incurred will be my responsibility</li>
</ul>

<p>I have disclosed all relevant medical conditions, allergies, and medications for my child in their registration profile.</p>

<p>By accepting this waiver, I confirm that I am the parent or legal guardian of the child registered and have the authority to grant this medical release.</p>""",
        "is_required": True,
    },
    {
        "name": "Liability Waiver and Release",
        "waiver_type": WaiverType.LIABILITY,
        "content": """<h2>Liability Waiver and Release</h2>
<p>In consideration of participation in California Sports Foundation (CSF) programs, I acknowledge and agree to the following:</p>

<p><strong>Assumption of Risk:</strong> I understand that participation in sports and physical activities involves inherent risks, including but not limited to:</p>
<ul>
<li>Physical injuries (sprains, strains, fractures, concussions)</li>
<li>Illness or communicable disease exposure</li>
<li>Property damage or loss</li>
<li>Equipment-related injuries</li>
</ul>

<p><strong>Release of Liability:</strong> I hereby release, discharge, and hold harmless California Sports Foundation, its officers, directors, employees, coaches, volunteers, and agents from any and all liability, claims, demands, or causes of action arising out of or related to my child's participation in CSF programs.</p>

<p><strong>Indemnification:</strong> I agree to indemnify and hold harmless CSF from any claims, damages, or expenses (including attorney fees) arising from my child's participation in CSF activities.</p>

<p>I have read this waiver carefully, understand its contents, and sign it voluntarily.</p>""",
        "is_required": True,
    },
    {
        "name": "Photo/Video Release",
        "waiver_type": WaiverType.PHOTO_RELEASE,
        "content": """<h2>Photo and Video Release</h2>
<p>I hereby grant California Sports Foundation (CSF) permission to use photographs, video recordings, and/or audio recordings of my child taken during CSF programs and events.</p>

<p>I understand that these materials may be used for:</p>
<ul>
<li>CSF website and social media accounts</li>
<li>Marketing and promotional materials</li>
<li>Newsletters and communications</li>
<li>Annual reports and fundraising materials</li>
<li>Media coverage and press releases</li>
</ul>

<p>I understand that:</p>
<ul>
<li>No compensation will be provided for the use of these materials</li>
<li>CSF will not use images in a way that would embarrass or harm my child</li>
<li>I may revoke this permission at any time by submitting a written request</li>
</ul>

<p>By accepting this release, I waive any right to inspect or approve the finished materials or the copy that may accompany them.</p>""",
        "is_required": False,
    },
    {
        "name": "Cancellation and Refund Policy",
        "waiver_type": WaiverType.CANCELLATION_POLICY,
        "content": """<h2>Cancellation and Refund Policy</h2>
<p>I acknowledge and agree to the following cancellation and refund policies of California Sports Foundation (CSF):</p>

<p><strong>Registration Cancellation:</strong></p>
<ul>
<li>Cancellations made 14+ days before the program start date: Full refund minus $25 processing fee</li>
<li>Cancellations made 7-13 days before: 50% refund</li>
<li>Cancellations made less than 7 days before: No refund</li>
</ul>

<p><strong>Program Cancellation by CSF:</strong></p>
<ul>
<li>If CSF cancels a program, a full refund will be issued</li>
<li>CSF reserves the right to cancel programs due to insufficient enrollment or unforeseen circumstances</li>
</ul>

<p><strong>Weather and Emergency Cancellations:</strong></p>
<ul>
<li>Individual sessions cancelled due to weather will be rescheduled when possible</li>
<li>No refunds will be issued for weather-related cancellations if the program continues</li>
</ul>

<p><strong>Transfer Policy:</strong></p>
<ul>
<li>Transfers to another program or session may be requested up to 7 days before the start date</li>
<li>Transfers are subject to availability and may incur a $15 transfer fee</li>
</ul>

<p>By accepting this policy, I confirm that I have read and understand these terms.</p>""",
        "is_required": True,
    },
]


async def seed_waivers():
    """Seed default waiver templates."""
    async with async_session_maker() as session:
        for waiver_data in DEFAULT_WAIVERS:
            # Check if waiver type already exists
            result = await session.execute(
                select(WaiverTemplate).where(
                    WaiverTemplate.waiver_type == waiver_data["waiver_type"]
                )
            )
            existing = result.scalars().first()

            if existing:
                print(f"Waiver '{waiver_data['name']}' already exists, skipping...")
                continue

            template = WaiverTemplate(
                name=waiver_data["name"],
                waiver_type=waiver_data["waiver_type"],
                content=waiver_data["content"],
                version=1,
                is_active=True,
                is_required=waiver_data["is_required"],
            )
            session.add(template)
            print(f"Created waiver: {waiver_data['name']}")

        await session.commit()
        print("\nWaiver seeding completed!")


if __name__ == "__main__":
    asyncio.run(seed_waivers())
