"""
Comprehensive seed script for CSF Backend.
Populates database with all necessary test data.
"""

import asyncio
import sys
from pathlib import Path
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import models
from app.models.organization import Organization
from app.models.user import User, Role
from app.models.program import Area, School, Program
from app.models.class_ import Class, ClassType, BillingModel, Weekday
from app.models.waiver import WaiverTemplate, WaiverType
from app.models.discount import DiscountCode, DiscountType
from app.models.child import Child, JerseySize, Grade
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.order import Order, OrderStatus
from core.config import config
from app.utils.security import hash_password


class DataSeeder:
    """Seed data generator."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.organization = None
        self.users = {}
        self.areas = {}
        self.schools = {}
        self.programs = {}
        self.classes = {}
        self.waivers = {}
        self.discounts = {}
        self.children = {}

    async def seed_all(self):
        """Seed all data."""
        print("🌱 Starting database seeding...")
        try:
            await self.seed_organization()
            await self.seed_users()
            await self.seed_areas()
            await self.seed_schools()
            await self.seed_programs()
            await self.seed_waivers()
            await self.seed_classes()
            await self.seed_discounts()
            await self.seed_children()
            await self.seed_enrollments()
            print("\n✅ Database seeding completed successfully!")
        except Exception as e:
            print(f"\n❌ Error during seeding: {e}")
            raise

    async def seed_organization(self):
        """Create or get default organization."""
        print("🏢 Seeding organization...")
        result = await self.session.execute(
            select(Organization).where(Organization.slug == "csf-sports")
        )
        organization = result.scalar_one_or_none()

        if organization:
            print(f"  Using existing organization: {organization.name}")
        else:
            organization = Organization(
                name="CSF Sports",
                slug="csf-sports",
                description="Community Sports Facility - Youth Sports Programs",
                email="info@csfsports.com",
                phone="+1-555-1000",
                is_active=True,
            )
            self.session.add(organization)
            await self.session.commit()
            await self.session.refresh(organization)
            print(f"  Created organization: {organization.name}")

        self.organization = organization

    async def seed_users(self):
        """Create users with all roles."""
        print("👥 Seeding users...")

        users_data = [
            {
                "email": "owner@csf.com",
                "password": "Owner123!",
                "first_name": "Sarah",
                "last_name": "Johnson",
                "role": Role.OWNER,
                "phone": "+1-555-0001",
            },
            {
                "email": "admin@csf.com",
                "password": "Admin123!",
                "first_name": "Michael",
                "last_name": "Smith",
                "role": Role.ADMIN,
                "phone": "+1-555-0002",
            },
            {
                "email": "coach@csf.com",
                "password": "Coach123!",
                "first_name": "Emily",
                "last_name": "Davis",
                "role": Role.COACH,
                "phone": "+1-555-0003",
            },
            {
                "email": "parent@csf.com",
                "password": "Parent123!",
                "first_name": "John",
                "last_name": "Williams",
                "role": Role.PARENT,
                "phone": "+1-555-0004",
            },
            {
                "email": "parent2@csf.com",
                "password": "Parent123!",
                "first_name": "Jennifer",
                "last_name": "Brown",
                "role": Role.PARENT,
                "phone": "+1-555-0005",
            },
        ]

        created = 0
        for user_data in users_data:
            # Check if user already exists
            result = await self.session.execute(
                select(User).where(
                    User.email == user_data["email"],
                    User.organization_id == self.organization.id
                )
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"  User {user_data['email']} already exists, skipping")
                self.users[user_data["email"]] = existing_user
            else:
                password = user_data.pop("password")
                user = User(
                    **user_data,
                    hashed_password=hash_password(password),
                    organization_id=self.organization.id,
                    is_active=True,
                    is_verified=True,
                )
                self.session.add(user)
                self.users[user_data["email"]] = user
                created += 1

        await self.session.commit()
        print(f"  Created {created} new users, {len(users_data) - created} already existed")

    async def seed_areas(self):
        """Create geographic areas."""
        print("🗺️  Seeding areas...")

        areas_data = [
            {"name": "Charlotte", "description": "North side locations"},
            {"name": "Greensboro", "description": "South side locations"},
            {"name": "Triangle", "description": "East side locations"},
        ]

        created = 0
        for area_data in areas_data:
            # Check if area already exists
            result = await self.session.execute(
                select(Area).where(
                    Area.name == area_data["name"],
                    Area.organization_id == self.organization.id
                )
            )
            existing_area = result.scalar_one_or_none()

            if existing_area:
                print(f"  Area '{area_data['name']}' already exists, skipping")
                self.areas[area_data["name"]] = existing_area
            else:
                area = Area(
                    **area_data,
                    organization_id=self.organization.id,
                    is_active=True
                )
                self.session.add(area)
                self.areas[area_data["name"]] = area
                created += 1

        await self.session.commit()
        print(f"  Created {created} new areas, {len(areas_data) - created} already existed")

    async def seed_schools(self):
        """Create school locations."""
        print("🏫 Seeding schools...")

        schools_data = [
            {
                "name": "Lincoln Elementary",
                "area": "Charlotte",
                "address": "100 Lincoln Ave",
                "city": "Charlotte",
                "state": "NC",
                "zip_code": "28201",
            },
            {
                "name": "Washington Middle School",
                "area": "Charlotte",
                "address": "200 Washington Blvd",
                "city": "Charlotte",
                "state": "NC",
                "zip_code": "28202",
            },
            {
                "name": "Roosevelt High School",
                "area": "Greensboro",
                "address": "300 Roosevelt Dr",
                "city": "Greensboro",
                "state": "NC",
                "zip_code": "27401",
            },
            {
                "name": "Community Sports Center",
                "area": "Greensboro",
                "address": "400 Sports Way",
                "city": "Greensboro",
                "state": "NC",
                "zip_code": "27402",
            },
            {
                "name": "Triangle Youth Center",
                "area": "Triangle",
                "address": "500 Youth Blvd",
                "city": "Raleigh",
                "state": "NC",
                "zip_code": "27601",
            },
        ]

        created = 0
        for school_data in schools_data:
            area_name = school_data.pop("area")

            # Check if school already exists
            result = await self.session.execute(
                select(School).where(
                    School.name == school_data["name"],
                    School.organization_id == self.organization.id
                )
            )
            existing_school = result.scalar_one_or_none()

            if existing_school:
                print(f"  School '{school_data['name']}' already exists, skipping")
                self.schools[school_data["name"]] = existing_school
            else:
                school = School(
                    **school_data,
                    area_id=self.areas[area_name].id,
                    organization_id=self.organization.id,
                    is_active=True
                )
                self.session.add(school)
                self.schools[school_data["name"]] = school
                created += 1

        await self.session.commit()
        print(f"  Created {created} new schools, {len(schools_data) - created} already existed")

    async def seed_programs(self):
        """Create sports/activity programs."""
        print("⚽ Seeding programs...")

        programs_data = [
            {
                "name": "Preschool",
                "description": "Activities for preschool-aged children (ages 5-12)",
            },
            {
                "name": "Elementary",
                "description": "Programs for elementary school children (ages 8-15)",
            },
            {
                "name": "TDC",
                "description": "Therapeutic Developmental Classes (ages 4-16)",
            },
            {
                "name": "Camps",
                "description": "Seasonal sports camps (ages 6-14)",
            },
            {
                "name": "Leagues",
                "description": "Competitive sports leagues (ages 6-14)",
            },
        ]

        created = 0
        for program_data in programs_data:
            # Check if program already exists
            result = await self.session.execute(
                select(Program).where(
                    Program.name == program_data["name"],
                    Program.organization_id == self.organization.id
                )
            )
            existing_program = result.scalar_one_or_none()

            if existing_program:
                print(f"  Program '{program_data['name']}' already exists, skipping")
                self.programs[program_data["name"]] = existing_program
            else:
                program = Program(
                    **program_data,
                    organization_id=self.organization.id,
                    is_active=True
                )
                self.session.add(program)
                self.programs[program_data["name"]] = program
                created += 1

        await self.session.commit()
        print(f"  Created {created} new programs, {len(programs_data) - created} already existed")

    async def seed_waivers(self):
        """Create waiver templates."""
        print("📋 Seeding waivers...")

        waivers_data = [
            {
                "name": "General Liability Waiver",
                "waiver_type": WaiverType.LIABILITY,
                "content": "<h2>Liability Waiver</h2><p>I understand and agree that participation in sports activities involves risks including but not limited to personal injury, property damage, and other potential hazards. I hereby release CSF Sports and its staff from all liability.</p>",
            },
            {
                "name": "Medical Release Form",
                "waiver_type": WaiverType.MEDICAL_RELEASE,
                "content": "<h2>Medical Release</h2><p>I authorize CSF Sports staff to seek emergency medical treatment for my child if needed. I agree to be responsible for all costs associated with such treatment.</p>",
            },
            {
                "name": "Photo Release Authorization",
                "waiver_type": WaiverType.PHOTO_RELEASE,
                "content": "<h2>Photo Release</h2><p>I grant permission for CSF Sports to use photographs and videos of my child for promotional and marketing purposes.</p>",
            },
            {
                "name": "Cancellation Policy Agreement",
                "waiver_type": WaiverType.CANCELLATION_POLICY,
                "content": "<h2>Cancellation Policy</h2><p>I understand that refunds are only available within 15 days of enrollment. After 15 days, no refunds will be issued. I agree to this cancellation policy.</p>",
            },
        ]

        created = 0
        for waiver_data in waivers_data:
            # Check if waiver already exists
            result = await self.session.execute(
                select(WaiverTemplate).where(
                    WaiverTemplate.name == waiver_data["name"],
                    WaiverTemplate.organization_id == self.organization.id
                )
            )
            existing_waiver = result.scalar_one_or_none()

            if existing_waiver:
                print(f"  Waiver '{waiver_data['name']}' already exists, skipping")
                self.waivers[waiver_data["name"]] = existing_waiver
            else:
                waiver = WaiverTemplate(
                    **waiver_data,
                    organization_id=self.organization.id,
                    version=1,
                    is_active=True,
                    is_required=True
                )
                self.session.add(waiver)
                self.waivers[waiver_data["name"]] = waiver
                created += 1

        await self.session.commit()
        print(f"  Created {created} new waivers, {len(waivers_data) - created} already existed")

    async def seed_classes(self):
        """Create class offerings."""
        print("📚 Seeding classes...")

        start_date = date.today() + timedelta(days=7)
        end_date = start_date + timedelta(days=90)

        classes_data = [
            {
                "name": "Preschool Soccer - Spring Session",
                "description": "Beginner soccer for young children focusing on fundamentals and fun",
                "program": "Preschool",
                "school": "Lincoln Elementary",
                "coach": "coach@csf.com",
                "class_type": ClassType.SHORT_TERM,
                "billing_model": BillingModel.ONE_TIME,
                "start_date": start_date,
                "end_date": end_date,
                "weekdays": [Weekday.MONDAY.value, Weekday.WEDNESDAY.value],
                "start_time": time(16, 0),
                "end_time": time(17, 30),
                "min_age": 5,
                "max_age": 8,
                "capacity": 20,
                "price": Decimal("150.00"),
            },
            {
                "name": "Elementary Soccer Training",
                "description": "Advanced soccer training for elementary age students",
                "program": "Elementary",
                "school": "Community Sports Center",
                "coach": "coach@csf.com",
                "class_type": ClassType.SHORT_TERM,
                "billing_model": BillingModel.ONE_TIME,
                "start_date": start_date,
                "end_date": end_date,
                "weekdays": [Weekday.TUESDAY.value, Weekday.THURSDAY.value],
                "start_time": time(17, 30),
                "end_time": time(19, 0),
                "min_age": 9,
                "max_age": 12,
                "capacity": 16,
                "price": Decimal("300.00"),
                "installments_enabled": True,
            },
            {
                "name": "Basketball League - Monthly Membership",
                "description": "Ongoing basketball league with monthly membership",
                "program": "Leagues",
                "school": "Washington Middle School",
                "coach": "coach@csf.com",
                "class_type": ClassType.MEMBERSHIP,
                "billing_model": BillingModel.MONTHLY,
                "start_date": start_date,
                "end_date": start_date + timedelta(days=365),
                "weekdays": [Weekday.MONDAY.value, Weekday.WEDNESDAY.value, Weekday.FRIDAY.value],
                "start_time": time(18, 0),
                "end_time": time(19, 30),
                "min_age": 10,
                "max_age": 15,
                "capacity": 24,
                "price": Decimal("80.00"),
                "monthly_price": Decimal("80.00"),
            },
            {
                "name": "TDC Swimming - Level 1",
                "description": "Therapeutic swimming lessons for special needs children",
                "program": "TDC",
                "school": "Community Sports Center",
                "coach": "coach@csf.com",
                "class_type": ClassType.SHORT_TERM,
                "billing_model": BillingModel.ONE_TIME,
                "start_date": start_date,
                "end_date": start_date + timedelta(days=30),
                "weekdays": [Weekday.SATURDAY.value],
                "start_time": time(10, 0),
                "end_time": time(11, 0),
                "min_age": 4,
                "max_age": 7,
                "capacity": 12,
                "price": Decimal("200.00"),
            },
            {
                "name": "Summer Sports Camp",
                "description": "Multi-sport summer camp for kids",
                "program": "Camps",
                "school": "Triangle Youth Center",
                "coach": "coach@csf.com",
                "class_type": ClassType.SHORT_TERM,
                "billing_model": BillingModel.ONE_TIME,
                "start_date": start_date,
                "end_date": end_date,
                "weekdays": [Weekday.MONDAY.value, Weekday.TUESDAY.value, Weekday.WEDNESDAY.value, Weekday.THURSDAY.value],
                "start_time": time(9, 0),
                "end_time": time(15, 0),
                "min_age": 6,
                "max_age": 14,
                "capacity": 30,
                "price": Decimal("450.00"),
            },
        ]

        created = 0
        for class_data in classes_data:
            program_name = class_data.pop("program")
            school_name = class_data.pop("school")
            coach_email = class_data.pop("coach")

            # Check if class already exists
            result = await self.session.execute(
                select(Class).where(
                    Class.name == class_data["name"],
                    Class.organization_id == self.organization.id
                )
            )
            existing_class = result.scalar_one_or_none()

            if existing_class:
                print(f"  Class '{class_data['name']}' already exists, skipping")
                self.classes[class_data["name"]] = existing_class
            else:
                class_obj = Class(
                    **class_data,
                    program_id=self.programs[program_name].id,
                    school_id=self.schools[school_name].id,
                    coach_id=self.users[coach_email].id,
                    organization_id=self.organization.id,
                    current_enrollment=0,
                    waitlist_enabled=True
                )
                self.session.add(class_obj)
                self.classes[class_data["name"]] = class_obj
                created += 1

        await self.session.commit()
        print(f"  Created {created} new classes, {len(classes_data) - created} already existed")

    async def seed_discounts(self):
        """Create discount codes."""
        print("💰 Seeding discount codes...")

        admin_user = self.users["admin@csf.com"]
        now = datetime.now()

        discounts_data = [
            {
                "code": "WELCOME25",
                "description": "25% off for new customers",
                "discount_type": DiscountType.PERCENTAGE,
                "discount_value": Decimal("25.00"),
                "valid_from": now,
                "valid_until": now + timedelta(days=90),
                "max_uses": 100,
                "is_active": True,
            },
            {
                "code": "SUMMER50",
                "description": "$50 off summer camp",
                "discount_type": DiscountType.FIXED_AMOUNT,
                "discount_value": Decimal("50.00"),
                "valid_from": now,
                "valid_until": now + timedelta(days=60),
                "min_order_amount": Decimal("200.00"),
                "is_active": True,
            },
            {
                "code": "EARLYBIRD",
                "description": "Early registration discount",
                "discount_type": DiscountType.PERCENTAGE,
                "discount_value": Decimal("15.00"),
                "valid_from": now,
                "valid_until": now + timedelta(days=30),
                "is_active": True,
            },
        ]

        created = 0
        for discount_data in discounts_data:
            # Check if discount code already exists
            result = await self.session.execute(
                select(DiscountCode).where(
                    DiscountCode.code == discount_data["code"],
                    DiscountCode.organization_id == self.organization.id
                )
            )
            existing_discount = result.scalar_one_or_none()

            if existing_discount:
                print(f"  Discount code '{discount_data['code']}' already exists, skipping")
                self.discounts[discount_data["code"]] = existing_discount
            else:
                discount = DiscountCode(
                    **discount_data,
                    created_by_id=admin_user.id,
                    organization_id=self.organization.id,
                    current_uses=0
                )
                self.session.add(discount)
                self.discounts[discount_data["code"]] = discount
                created += 1

        await self.session.commit()
        print(f"  Created {created} new discount codes, {len(discounts_data) - created} already existed")

    async def seed_children(self):
        """Create children for parent users."""
        print("👶 Seeding children...")

        parent1 = self.users["parent@csf.com"]
        parent2 = self.users["parent2@csf.com"]

        children_data = [
            {
                "user": parent1,
                "first_name": "Emma",
                "last_name": "Williams",
                "date_of_birth": date.today() - timedelta(days=2555),  # ~7 years old
                "jersey_size": JerseySize.M,
                "grade": Grade.GRADE_2,
            },
            {
                "user": parent1,
                "first_name": "Liam",
                "last_name": "Williams",
                "date_of_birth": date.today() - timedelta(days=3650),  # ~10 years old
                "jersey_size": JerseySize.L,
                "grade": Grade.GRADE_5,
            },
            {
                "user": parent2,
                "first_name": "Sophia",
                "last_name": "Brown",
                "date_of_birth": date.today() - timedelta(days=2190),  # ~6 years old
                "jersey_size": JerseySize.S,
                "grade": Grade.GRADE_1,
            },
        ]

        created = 0
        for child_data in children_data:
            user = child_data.pop("user")

            # Check if child already exists
            result = await self.session.execute(
                select(Child).where(
                    Child.first_name == child_data["first_name"],
                    Child.last_name == child_data["last_name"],
                    Child.user_id == user.id
                )
            )
            existing_child = result.scalar_one_or_none()

            if existing_child:
                print(f"  Child {child_data['first_name']} {child_data['last_name']} already exists, skipping")
                self.children[f"{child_data['first_name']} {child_data['last_name']}"] = existing_child
            else:
                child = Child(
                    **child_data,
                    user_id=user.id,
                    organization_id=self.organization.id,
                    is_active=True,
                    has_no_medical_conditions=True,
                    has_medical_alert=False,
                    after_school_attendance=False
                )
                self.session.add(child)
                self.children[f"{child_data['first_name']} {child_data['last_name']}"] = child
                created += 1

        await self.session.commit()
        print(f"  Created {created} new children, {len(children_data) - created} already existed")

    async def seed_enrollments(self):
        """Create sample enrollments."""
        print("📝 Seeding enrollments...")

        if not self.children or not self.classes:
            print("  No children or classes available, skipping enrollments")
            return

        # Get first child and first class
        child = list(self.children.values())[0]
        class_obj = list(self.classes.values())[0]

        # Check if enrollment already exists
        result = await self.session.execute(
            select(Enrollment).where(
                Enrollment.child_id == child.id,
                Enrollment.class_id == class_obj.id
            )
        )
        existing_enrollment = result.scalar_one_or_none()

        if existing_enrollment:
            print(f"  Enrollment for {child.first_name} {child.last_name} in {class_obj.name} already exists, skipping")
            return

        # Create order
        order = Order(
            user_id=child.user_id,
            organization_id=self.organization.id,
            status=OrderStatus.PAID,
            subtotal=class_obj.price,
            discount_total=Decimal("0.00"),
            total=class_obj.price,
            paid_at=datetime.now(),
        )
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)

        # Create enrollment
        enrollment = Enrollment(
            child_id=child.id,
            class_id=class_obj.id,
            user_id=child.user_id,
            organization_id=self.organization.id,
            status=EnrollmentStatus.ACTIVE,
            enrolled_at=datetime.now(),
            base_price=class_obj.price,
            discount_amount=Decimal("0.00"),
            final_price=class_obj.price,
        )
        self.session.add(enrollment)

        # Update class enrollment count
        class_obj.current_enrollment += 1

        await self.session.commit()
        print(f"  Created 1 sample enrollment")


async def main():
    """Main seeding function."""
    # Create async engine
    engine = create_async_engine(config.DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        seeder = DataSeeder(session)
        await seeder.seed_all()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
