"""
Database seeding script to populate tables with realistic test data.

Usage:
    uv run python scripts/seed_database.py
"""

import asyncio
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4
import random

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child, EmergencyContact, Grade, HowHeardAboutUs, JerseySize
from app.models.class_ import Class, ClassType, Weekday
from app.models.discount import DiscountCode, DiscountType, Scholarship
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.order import Order, OrderLineItem, OrderStatus
from app.models.password_history import PasswordHistory
from app.models.payment import (
    InstallmentFrequency,
    InstallmentPayment,
    InstallmentPaymentStatus,
    InstallmentPlan,
    InstallmentPlanStatus,
    Payment,
    PaymentStatus,
    PaymentType,
)
from app.models.program import Area, Program, School
from app.models.user import Role, User
from app.models.waiver import WaiverAcceptance, WaiverTemplate, WaiverType
from app.utils.encryption import encrypt_pii
from app.utils.security import hash_password
from core.db import async_session_factory
from core.logging import get_logger

logger = get_logger(__name__)


class DatabaseSeeder:
    """Database seeding utility."""

    def __init__(self):
        self.users = []
        self.children = []
        self.programs = []
        self.areas = []
        self.schools = []
        self.classes = []
        self.waivers = []
        self.orders = []
        self.enrollments = []

    async def clear_database(self, session: AsyncSession):
        """Clear all tables in reverse dependency order."""
        logger.info("Clearing existing data...")

        # Truncate tables in reverse dependency order
        tables = [
            "password_history",
            "waiver_acceptances",
            "installment_payments",
            "installment_plans",
            "payments",
            "order_line_items",
            "enrollments",
            "orders",
            "scholarships",
            "discount_codes",
            "classes",
            "waiver_templates",
            "emergency_contacts",
            "children",
            "schools",
            "programs",
            "areas",
            "users",
        ]

        for table in tables:
            try:
                await session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
                await session.commit()
            except Exception as e:
                # Skip tables that don't exist and rollback failed transaction
                logger.debug(f"Skipping table {table}: {str(e)[:100]}")
                await session.rollback()

        logger.info("Database cleared successfully")

    async def seed_all(self):
        """Seed all tables with test data."""
        async with async_session_factory() as session:
            logger.info("Starting database seeding...")

            # Clear existing data first
            await self.clear_database(session)

            await self.seed_users(session)
            await self.seed_areas(session)
            await self.seed_schools(session)
            await self.seed_programs(session)
            await self.seed_children(session)
            await self.seed_emergency_contacts(session)
            await self.seed_waivers(session)
            await self.seed_classes(session)
            await self.seed_discount_codes(session)
            await self.seed_scholarships(session)
            await self.seed_orders_and_enrollments(session)
            await self.seed_payments(session)
            await self.seed_installment_plans(session)
            await self.seed_waiver_acceptances(session)
            await self.seed_password_history(session)

            await session.commit()
            logger.info("Database seeding completed successfully!")

    async def seed_users(self, session: AsyncSession):
        """Seed users with different roles."""
        logger.info("Seeding users...")

        # Owner
        owner = User(
            id=str(uuid4()),
            email="owner@csf.com",
            hashed_password=hash_password("Owner123"),
            first_name="Sarah",
            last_name="Williams",
            phone="555-0001",
            role=Role.OWNER,
            is_active=True,
            is_verified=True,
        )
        session.add(owner)
        self.users.append(owner)

        # Admins (2)
        admins = [
            ("admin1@csf.com", "Michael", "Johnson", "555-0002"),
            ("admin2@csf.com", "Emily", "Davis", "555-0003"),
        ]
        for email, first, last, phone in admins:
            admin = User(
                id=str(uuid4()),
                email=email,
                hashed_password=hash_password("Admin123"),
                first_name=first,
                last_name=last,
                phone=phone,
                role=Role.ADMIN,
                is_active=True,
                is_verified=True,
            )
            session.add(admin)
            self.users.append(admin)

        # Coaches (3)
        coaches = [
            ("coach1@csf.com", "David", "Martinez", "555-0004"),
            ("coach2@csf.com", "Lisa", "Anderson", "555-0005"),
            ("coach3@csf.com", "James", "Taylor", "555-0006"),
        ]
        for email, first, last, phone in coaches:
            coach = User(
                id=str(uuid4()),
                email=email,
                hashed_password=hash_password("Coach123"),
                first_name=first,
                last_name=last,
                phone=phone,
                role=Role.COACH,
                is_active=True,
                is_verified=True,
            )
            session.add(coach)
            self.users.append(coach)

        # Parents (15)
        parent_names = [
            ("john.smith@email.com", "John", "Smith", "555-1001"),
            ("mary.jones@email.com", "Mary", "Jones", "555-1002"),
            ("robert.brown@email.com", "Robert", "Brown", "555-1003"),
            ("jennifer.garcia@email.com", "Jennifer", "Garcia", "555-1004"),
            ("william.miller@email.com", "William", "Miller", "555-1005"),
            ("linda.wilson@email.com", "Linda", "Wilson", "555-1006"),
            ("richard.moore@email.com", "Richard", "Moore", "555-1007"),
            ("patricia.taylor@email.com", "Patricia", "Taylor", "555-1008"),
            ("charles.thomas@email.com", "Charles", "Thomas", "555-1009"),
            ("barbara.jackson@email.com", "Barbara", "Jackson", "555-1010"),
            ("joseph.white@email.com", "Joseph", "White", "555-1011"),
            ("susan.harris@email.com", "Susan", "Harris", "555-1012"),
            ("thomas.martin@email.com", "Thomas", "Martin", "555-1013"),
            ("jessica.thompson@email.com", "Jessica", "Thompson", "555-1014"),
            ("daniel.lee@email.com", "Daniel", "Lee", "555-1015"),
        ]
        for email, first, last, phone in parent_names:
            parent = User(
                id=str(uuid4()),
                email=email,
                hashed_password=hash_password("Parent123"),
                first_name=first,
                last_name=last,
                phone=phone,
                role=Role.PARENT,
                is_active=True,
                is_verified=True,
            )
            session.add(parent)
            self.users.append(parent)

        await session.flush()
        logger.info(f"Created {len(self.users)} users")

    async def seed_areas(self, session: AsyncSession):
        """Seed geographic areas."""
        logger.info("Seeding areas...")

        area_names = [
            ("North District", "Northern area of the city"),
            ("South District", "Southern area of the city"),
            ("East District", "Eastern area of the city"),
            ("West District", "Western area of the city"),
            ("Central District", "Downtown central area"),
            ("Suburban North", "Northern suburbs"),
            ("Suburban South", "Southern suburbs"),
            ("Suburban East", "Eastern suburbs"),
            ("Suburban West", "Western suburbs"),
            ("Metro Area", "Greater metropolitan area"),
        ]

        for name, desc in area_names:
            area = Area(id=str(uuid4()), name=name, description=desc, is_active=True)
            session.add(area)
            self.areas.append(area)

        await session.flush()
        logger.info(f"Created {len(self.areas)} areas")

    async def seed_schools(self, session: AsyncSession):
        """Seed schools/locations."""
        logger.info("Seeding schools...")

        school_data = [
            ("Lincoln Elementary", "123 Oak Street", "Springfield", "IL", "62701"),
            ("Washington Middle School", "456 Maple Avenue", "Madison", "WI", "53703"),
            ("Jefferson High School", "789 Pine Road", "Portland", "OR", "97201"),
            ("Roosevelt Community Center", "321 Elm Street", "Austin", "TX", "78701"),
            ("Kennedy Sports Complex", "654 Cedar Lane", "Denver", "CO", "80201"),
            ("Madison Recreation Center", "987 Birch Drive", "Seattle", "WA", "98101"),
            ("Monroe Athletic Club", "147 Spruce Way", "Phoenix", "AZ", "85001"),
            ("Adams Youth Center", "258 Willow Court", "Atlanta", "GA", "30301"),
            ("Jackson Community Hub", "369 Ash Boulevard", "Miami", "FL", "33101"),
            ("Wilson Sports Park", "741 Cypress Avenue", "Boston", "MA", "02101"),
        ]

        for i, (name, address, city, state, zip_code) in enumerate(school_data):
            area = self.areas[i % len(self.areas)]
            school = School(
                id=str(uuid4()),
                name=name,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                area_id=area.id,
                is_active=True,
            )
            session.add(school)
            self.schools.append(school)

        await session.flush()
        logger.info(f"Created {len(self.schools)} schools")

    async def seed_programs(self, session: AsyncSession):
        """Seed sports programs."""
        logger.info("Seeding programs...")

        program_data = [
            ("Soccer", "Youth soccer training and leagues"),
            ("Basketball", "Basketball skills and team play"),
            ("Baseball", "Baseball fundamentals and leagues"),
            ("Tennis", "Tennis lessons and tournaments"),
            ("Swimming", "Swimming lessons and water safety"),
            ("Gymnastics", "Gymnastics training and routines"),
            ("Martial Arts", "Karate and self-defense training"),
            ("Dance", "Various dance styles and performance"),
            ("Track & Field", "Running, jumping, and throwing events"),
            ("Volleyball", "Volleyball skills and team play"),
        ]

        for name, desc in program_data:
            program = Program(
                id=str(uuid4()),
                name=name,
                description=desc,
                is_active=True,
            )
            session.add(program)
            self.programs.append(program)

        await session.flush()
        logger.info(f"Created {len(self.programs)} programs")

    async def seed_children(self, session: AsyncSession):
        """Seed children for parent users."""
        logger.info("Seeding children...")

        # Get parent users only
        parents = [u for u in self.users if u.role == Role.PARENT]

        child_first_names = [
            "Emma",
            "Liam",
            "Olivia",
            "Noah",
            "Ava",
            "Ethan",
            "Sophia",
            "Mason",
            "Isabella",
            "Logan",
            "Mia",
            "Lucas",
            "Charlotte",
            "Oliver",
            "Amelia",
            "Elijah",
            "Harper",
            "James",
            "Evelyn",
            "Benjamin",
        ]

        grades = list(Grade)
        jersey_sizes = list(JerseySize)
        how_heard = list(HowHeardAboutUs)

        for i, parent in enumerate(parents):
            # Each parent has 1-2 children
            num_children = random.randint(1, 2)
            for j in range(num_children):
                first_name = child_first_names[(i * 2 + j) % len(child_first_names)]
                dob = date.today() - timedelta(days=random.randint(2555, 4380))  # 7-12 years

                child = Child(
                    id=str(uuid4()),
                    user_id=parent.id,
                    first_name=first_name,
                    last_name=parent.last_name,
                    date_of_birth=dob,
                    jersey_size=random.choice(jersey_sizes),
                    grade=random.choice(grades),
                    medical_conditions_encrypted=encrypt_pii("None" if random.random() > 0.3 else "Asthma"),
                    has_no_medical_conditions=random.random() > 0.3,
                    after_school_attendance=random.random() > 0.5,
                    after_school_program="After School Care" if random.random() > 0.5 else None,
                    health_insurance_number_encrypted=encrypt_pii(f"INS{random.randint(100000, 999999)}"),
                    how_heard_about_us=random.choice(how_heard),
                    is_active=True,
                )
                session.add(child)
                self.children.append(child)

        await session.flush()
        logger.info(f"Created {len(self.children)} children")

    async def seed_emergency_contacts(self, session: AsyncSession):
        """Seed emergency contacts for children."""
        logger.info("Seeding emergency contacts...")

        contact_names = [
            ("Grandma", "grandmother"),
            ("Grandpa", "grandfather"),
            ("Aunt Sarah", "aunt"),
            ("Uncle Mike", "uncle"),
            ("Neighbor Jane", "neighbor"),
        ]

        count = 0
        for child in self.children:
            # Each child has 2-3 emergency contacts
            num_contacts = random.randint(2, 3)
            for i in range(num_contacts):
                name, relation = contact_names[i % len(contact_names)]
                contact = EmergencyContact(
                    id=str(uuid4()),
                    child_id=child.id,
                    name=name,
                    relation=relation,
                    phone=f"555-{random.randint(2000, 9999)}",
                    email=f"{name.lower().replace(' ', '.')}@email.com",
                    is_primary=(i == 0),
                )
                session.add(contact)
                count += 1

        await session.flush()
        logger.info(f"Created {count} emergency contacts")

    async def seed_waivers(self, session: AsyncSession):
        """Seed waiver templates."""
        logger.info("Seeding waivers...")

        waiver_data = [
            (
                WaiverType.LIABILITY,
                "General Liability Waiver",
                "<h1>Liability Release</h1><p>I acknowledge and assume all risks...</p>",
            ),
            (
                WaiverType.MEDICAL_RELEASE,
                "Medical Treatment Authorization",
                "<h1>Medical Authorization</h1><p>I authorize emergency medical treatment...</p>",
            ),
            (
                WaiverType.PHOTO_RELEASE,
                "Photo and Video Release",
                "<h1>Media Release</h1><p>I grant permission to use photos and videos...</p>",
            ),
            (
                WaiverType.CANCELLATION_POLICY,
                "Cancellation Policy Agreement",
                "<h1>Cancellation Policy</h1><p>I understand and agree to the cancellation policy...</p>",
            ),
        ]

        for waiver_type, name, content in waiver_data:
            waiver = WaiverTemplate(
                id=str(uuid4()),
                waiver_type=waiver_type,
                name=name,
                content=content,
                version=1,
                is_active=True,
                is_required=True,
            )
            session.add(waiver)
            self.waivers.append(waiver)

        await session.flush()
        logger.info(f"Created {len(self.waivers)} waiver templates")

    async def seed_classes(self, session: AsyncSession):
        """Seed class offerings."""
        logger.info("Seeding classes...")

        weekday_combinations = [
            [Weekday.MONDAY, Weekday.WEDNESDAY],
            [Weekday.TUESDAY, Weekday.THURSDAY],
            [Weekday.MONDAY, Weekday.WEDNESDAY, Weekday.FRIDAY],
            [Weekday.SATURDAY],
            [Weekday.SUNDAY],
        ]

        time_slots = [
            (time(9, 0), time(10, 0)),
            (time(10, 30), time(11, 30)),
            (time(14, 0), time(15, 0)),
            (time(15, 30), time(16, 30)),
            (time(17, 0), time(18, 0)),
        ]

        class_count = 0
        for program in self.programs:
            # Create 3-4 classes per program
            for i in range(random.randint(3, 4)):
                school = self.schools[class_count % len(self.schools)]
                weekdays = random.choice(weekday_combinations)
                start_time, end_time = random.choice(time_slots)

                start_date = date.today() + timedelta(days=random.randint(7, 30))
                duration = random.choice([60, 90, 120])  # days
                end_date = start_date + timedelta(days=duration)

                class_type = random.choice(["short_term", "membership"])
                price = Decimal(random.choice([150, 200, 250, 300, 350]))

                cls = Class(
                    id=str(uuid4()),
                    name=f"{program.name} - Level {i+1}",
                    description=f"Great {program.name.lower()} class for skill level {i+1}",
                    program_id=program.id,
                    school_id=school.id,
                    class_type=class_type,
                    weekdays=[w.value for w in weekdays],
                    start_time=start_time,
                    end_time=end_time,
                    start_date=start_date,
                    end_date=end_date,
                    capacity=random.randint(15, 25),
                    current_enrollment=0,
                    waitlist_enabled=True,
                    price=price,
                    membership_price=price * Decimal("0.8") if class_type == "membership" else None,
                    installments_enabled=random.random() > 0.5,
                    min_age=random.randint(5, 8),
                    max_age=random.randint(12, 16),
                    is_active=True,
                )
                session.add(cls)
                self.classes.append(cls)
                class_count += 1

        await session.flush()
        logger.info(f"Created {len(self.classes)} classes")

    async def seed_discount_codes(self, session: AsyncSession):
        """Seed discount codes."""
        logger.info("Seeding discount codes...")

        # Get an admin user to be the creator
        admin_user = next((u for u in self.users if u.role == Role.ADMIN), self.users[0])

        discount_data = [
            ("SUMMER2024", DiscountType.PERCENTAGE, Decimal("20"), 100, None),
            ("FALL50", DiscountType.FIXED_AMOUNT, Decimal("50"), 50, Decimal("200")),
            ("EARLYBIRD", DiscountType.PERCENTAGE, Decimal("15"), 200, None),
            ("WELCOME10", DiscountType.PERCENTAGE, Decimal("10"), 500, None),
            ("SAVE25", DiscountType.FIXED_AMOUNT, Decimal("25"), 100, Decimal("150")),
            ("SPRING2024", DiscountType.PERCENTAGE, Decimal("25"), 75, None),
            ("FAMILY20", DiscountType.PERCENTAGE, Decimal("20"), 150, Decimal("300")),
            ("TRIAL100", DiscountType.FIXED_AMOUNT, Decimal("100"), 30, Decimal("500")),
            ("LOYALTY15", DiscountType.PERCENTAGE, Decimal("15"), 200, None),
            ("FRIEND30", DiscountType.FIXED_AMOUNT, Decimal("30"), 100, Decimal("200")),
        ]

        for code, disc_type, value, usage, min_amount in discount_data:
            discount = DiscountCode(
                id=str(uuid4()),
                code=code,
                discount_type=disc_type,
                discount_value=value,
                max_uses=usage,
                current_uses=random.randint(0, int(usage * 0.3)),
                min_order_amount=min_amount,
                valid_from=datetime.now() - timedelta(days=30),
                valid_until=datetime.now() + timedelta(days=90),
                is_active=True,
                created_by_id=admin_user.id,
            )
            session.add(discount)

        await session.flush()
        logger.info("Created 10 discount codes")

    async def seed_scholarships(self, session: AsyncSession):
        """Seed scholarships for some children."""
        logger.info("Seeding scholarships...")

        # Get an admin user to be the approver
        admin_user = next((u for u in self.users if u.role == Role.ADMIN), self.users[0])

        # Give scholarships to 5 children
        scholarship_children = random.sample(self.children, min(5, len(self.children)))

        for child in scholarship_children:
            scholarship = Scholarship(
                id=str(uuid4()),
                user_id=child.user_id,
                child_id=child.id,
                scholarship_type=random.choice(["Need-Based", "Merit-Based", "Community"]),
                discount_percentage=Decimal(random.choice([25, 50, 75])),
                approved_by_id=admin_user.id,
                valid_until=date.today() + timedelta(days=365),
            )
            session.add(scholarship)

        await session.flush()
        logger.info(f"Created {len(scholarship_children)} scholarships")

    async def seed_orders_and_enrollments(self, session: AsyncSession):
        """Seed orders and enrollments."""
        logger.info("Seeding orders and enrollments...")

        # Create orders for children
        for i, child in enumerate(self.children[:15]):  # First 15 children get enrollments
            # Each child enrolls in 1-2 classes
            num_classes = random.randint(1, 2)
            selected_classes = random.sample(self.classes, min(num_classes, len(self.classes)))

            # Create order
            order_total = sum(cls.price for cls in selected_classes)
            order_status = random.choice(["paid", "pending_payment"])

            order = Order(
                id=str(uuid4()),
                user_id=child.user_id,
                status=order_status,
                subtotal=order_total,
                discount_total=Decimal("0"),
                total=order_total,
            )
            session.add(order)
            await session.flush()

            # Create order line items and enrollments
            for cls in selected_classes:
                line_item = OrderLineItem(
                    id=str(uuid4()),
                    order_id=order.id,
                    description=f"{cls.name} - {child.full_name}",
                    unit_price=cls.price,
                    quantity=1,
                    line_total=cls.price,
                )
                session.add(line_item)

                # Create enrollment if order is paid
                if order_status == "paid":
                    enrollment = Enrollment(
                        id=str(uuid4()),
                        user_id=child.user_id,
                        child_id=child.id,
                        class_id=cls.id,
                        status="active",
                        enrolled_at=datetime.now(),
                        base_price=cls.price,
                        discount_amount=Decimal("0"),
                        final_price=cls.price,
                    )
                    session.add(enrollment)
                    self.enrollments.append(enrollment)

                    # Increment class enrollment counter
                    cls.current_enrollment += 1

            self.orders.append(order)

        await session.flush()
        logger.info(f"Created {len(self.orders)} orders and {len(self.enrollments)} enrollments")

    async def seed_payments(self, session: AsyncSession):
        """Seed payments for completed orders."""
        logger.info("Seeding payments...")

        completed_orders = [o for o in self.orders if o.status == "paid"]

        for order in completed_orders:
            payment_type = random.choice(["one_time", "subscription"])

            payment = Payment(
                id=str(uuid4()),
                order_id=order.id,
                user_id=order.user_id,
                amount=order.total,
                payment_type=payment_type,
                status="succeeded",
                stripe_payment_intent_id=f"pi_{uuid4().hex[:24]}",
            )
            session.add(payment)

        await session.flush()
        logger.info(f"Created {len(completed_orders)} payments")

    async def seed_installment_plans(self, session: AsyncSession):
        """Seed installment plans for some orders."""
        logger.info("Seeding installment plans...")

        # Create installment plans for 3 orders
        installment_orders = random.sample(self.orders, min(3, len(self.orders)))

        for order in installment_orders:
            plan = InstallmentPlan(
                id=str(uuid4()),
                order_id=order.id,
                user_id=order.user_id,
                total_amount=order.total,
                num_installments=2,
                installment_amount=order.total / 2,
                frequency="monthly",
                start_date=date.today(),
                status="active",
                stripe_subscription_id=f"sub_{uuid4().hex[:24]}",
            )
            session.add(plan)
            await session.flush()

            # Create installment payments
            for i in range(2):
                installment_payment = InstallmentPayment(
                    id=str(uuid4()),
                    installment_plan_id=plan.id,
                    installment_number=i + 1,
                    due_date=date.today() + timedelta(days=30 * i),
                    amount=plan.installment_amount,
                    status="paid" if i == 0 else "pending",
                    paid_at=datetime.now() if i == 0 else None,
                )
                session.add(installment_payment)

        await session.flush()
        logger.info(f"Created {len(installment_orders)} installment plans")

    async def seed_waiver_acceptances(self, session: AsyncSession):
        """Seed waiver acceptances for enrollments."""
        logger.info("Seeding waiver acceptances...")

        count = 0
        for enrollment in self.enrollments:
            # Accept all waivers for each enrollment
            # Get user for signer name
            user = next((u for u in self.users if u.id == enrollment.user_id), None)
            if not user:
                continue

            for waiver in self.waivers:
                acceptance = WaiverAcceptance(
                    id=str(uuid4()),
                    waiver_template_id=waiver.id,
                    user_id=enrollment.user_id,
                    waiver_version=waiver.version,
                    signer_name=f"{user.first_name} {user.last_name}",
                    signer_ip=f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
                    signer_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    accepted_at=datetime.now() - timedelta(days=random.randint(1, 30)),
                )
                session.add(acceptance)
                count += 1

        await session.flush()
        logger.info(f"Created {count} waiver acceptances")

    async def seed_password_history(self, session: AsyncSession):
        """Seed password history for users."""
        logger.info("Seeding password history...")

        # Add current password to history for all users
        for user in self.users:
            if user.hashed_password:
                history = PasswordHistory(
                    id=str(uuid4()),
                    user_id=user.id,
                    hashed_password=user.hashed_password,
                    created_at=datetime.now(),
                )
                session.add(history)

        await session.flush()
        logger.info(f"Created {len(self.users)} password history records")


async def main():
    """Main entry point for seeding."""
    seeder = DatabaseSeeder()
    await seeder.seed_all()


if __name__ == "__main__":
    asyncio.run(main())
