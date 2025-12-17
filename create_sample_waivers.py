"""
Create sample waiver templates for testing the checkout flow
Run this script from the backend directory: python create_sample_waivers.py
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.waiver import WaiverTemplate
from core.config import config


async def create_sample_waivers():
    """Create sample waiver templates in the database"""

    # Create async engine
    engine = create_async_engine(
        config.DATABASE_URL,
        echo=False,  # Set to False to reduce output
        future=True,
    )

    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        print("Creating sample waiver templates...")

        # Waiver 1: General Liability
        waiver1 = await WaiverTemplate.create_template(
            session,
            name="General Liability Waiver",
            waiver_type="liability",
            content=(
                "I, the undersigned parent/guardian of the participant, hereby acknowledge that "
                "participation in soccer activities involves inherent risks including but not limited "
                "to physical injury, sprains, fractures, and other injuries.\n\n"
                "I hereby RELEASE AND HOLD HARMLESS Carolina Soccer Factory, its officers, employees, "
                "coaches, and volunteers from any and all liability, claims, demands, or causes of action "
                "that I or my child may have arising out of or related to participation in the program.\n\n"
                "I understand this waiver is binding and will remain in effect for the duration of my "
                "child's enrollment."
            ),
            is_active=True,
            is_required=True,
            applies_to_program_id=None,
            applies_to_school_id=None,
        )
        print(f"✅ Created: {waiver1.name} (ID: {waiver1.id})")

        # Waiver 2: Medical Authorization
        waiver2 = await WaiverTemplate.create_template(
            session,
            name="Medical Authorization",
            waiver_type="medical",
            content=(
                "I authorize Carolina Soccer Factory staff to obtain necessary medical treatment "
                "for my child in the event of an emergency.\n\n"
                "I understand that every reasonable effort will be made to contact me in case of "
                "injury or illness. However, if I cannot be reached, I hereby consent to emergency "
                "medical treatment including but not limited to:\n"
                "• First aid and CPR\n"
                "• Transportation to a medical facility\n"
                "• Emergency medical procedures deemed necessary by medical professionals\n\n"
                "I agree to be responsible for all costs associated with such medical treatment."
            ),
            is_active=True,
            is_required=True,
            applies_to_program_id=None,
            applies_to_school_id=None,
        )
        print(f"✅ Created: {waiver2.name} (ID: {waiver2.id})")

        # Waiver 3: Photo/Video Release
        waiver3 = await WaiverTemplate.create_template(
            session,
            name="Photo and Video Release",
            waiver_type="media",
            content=(
                "I grant permission to Carolina Soccer Factory to use photographs, videos, or other "
                "media of my child taken during program activities for promotional purposes.\n\n"
                "This includes but is not limited to:\n"
                "• Website and social media posts\n"
                "• Marketing materials and brochures\n"
                "• News articles and press releases\n"
                "• Internal communications\n\n"
                "I understand that no compensation will be provided for such use and that all media "
                "remains the property of Carolina Soccer Factory.\n\n"
                "I may revoke this consent at any time by providing written notice to Carolina Soccer Factory."
            ),
            is_active=True,
            is_required=False,  # Optional waiver
            applies_to_program_id=None,
            applies_to_school_id=None,
        )
        print(f"✅ Created: {waiver3.name} (ID: {waiver3.id})")

        # Commit all changes
        await session.commit()

        print("\n✨ Successfully created 3 sample waiver templates!")
        print("\nThese waivers will now appear in the checkout flow when a parent:")
        print("1. Selects a child for enrollment")
        print("2. Has not yet signed these waivers")
        print("\nTo test:")
        print("- Go to checkout page")
        print("- Select a child")
        print("- The waiver modal should appear")
        print("- Sign the waivers to proceed with checkout")


if __name__ == "__main__":
    asyncio.run(create_sample_waivers())
