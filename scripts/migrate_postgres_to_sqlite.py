#!/usr/bin/env python3
"""
Data Migration Script: PostgreSQL → SQLite

This script migrates all data from a PostgreSQL database to SQLite.
Use this when deploying to PythonAnywhere or switching from PostgreSQL to SQLite.

Usage:
    python scripts/migrate_postgres_to_sqlite.py

Environment Variables Required:
    - POSTGRES_URL: Source PostgreSQL database URL
    - SQLITE_URL: Target SQLite database URL (or use default: sqlite+aiosqlite:///./csf.db)

Example:
    export POSTGRES_URL="postgresql+asyncpg://user:pass@localhost:5432/csf_db"
    export SQLITE_URL="sqlite+aiosqlite:///./csf.db"
    python scripts/migrate_postgres_to_sqlite.py
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import all models to ensure they're registered
from app.models import (
    User, Child, Program, Area, School, Class,
    WaiverTemplate, WaiverAcceptance,
    Order, OrderLineItem, Payment, InstallmentPlan, InstallmentPayment,
    DiscountCode, Enrollment, Organization
)


# Define table migration order (respecting foreign key dependencies)
MIGRATION_ORDER = [
    # Base tables (no dependencies)
    ("organizations", Organization),
    ("users", User),
    ("programs", Program),
    ("areas", Area),
    ("schools", School),

    # Tables with basic dependencies
    ("waiver_templates", WaiverTemplate),
    ("classes", Class),
    ("children", Child),
    ("discount_codes", DiscountCode),

    # Tables with multiple dependencies
    ("orders", Order),
    ("order_line_items", OrderLineItem),
    ("enrollments", Enrollment),
    ("payments", Payment),
    ("installment_plans", InstallmentPlan),
    ("installment_payments", InstallmentPayment),
    ("waiver_acceptances", WaiverAcceptance),
]


async def create_engines():
    """Create database engines for source and target databases."""
    postgres_url = os.getenv("POSTGRES_URL")
    sqlite_url = os.getenv("SQLITE_URL", "sqlite+aiosqlite:///./csf.db")

    if not postgres_url:
        print("❌ Error: POSTGRES_URL environment variable not set")
        print("   Example: export POSTGRES_URL='postgresql+asyncpg://user:pass@localhost:5432/csf_db'")
        sys.exit(1)

    print(f"📊 Source: {postgres_url.split('@')[1] if '@' in postgres_url else 'PostgreSQL'}")
    print(f"📊 Target: {sqlite_url}")
    print()

    # Create engines
    source_engine = create_async_engine(postgres_url, echo=False)
    target_engine = create_async_engine(sqlite_url, echo=False)

    return source_engine, target_engine


async def get_table_count(session: AsyncSession, model):
    """Get count of records in a table."""
    result = await session.execute(select(func.count()).select_from(model))
    return result.scalar()


async def migrate_table(
    source_session: AsyncSession,
    target_session: AsyncSession,
    table_name: str,
    model
):
    """Migrate all records from one table to another."""
    print(f"  📋 Migrating {table_name}...", end=" ", flush=True)

    try:
        # Get count
        source_count = await get_table_count(source_session, model)

        if source_count == 0:
            print("✓ (0 records)")
            return True

        # Fetch all records from source
        result = await source_session.execute(select(model))
        records = result.scalars().all()

        # Insert into target
        for record in records:
            # Create a dictionary of the record's data
            record_dict = {}
            for column in model.__table__.columns:
                value = getattr(record, column.name)
                record_dict[column.name] = value

            # Create new instance for target database
            new_record = model(**record_dict)
            target_session.add(new_record)

        # Commit to target
        await target_session.commit()

        # Verify count
        target_count = await get_table_count(target_session, model)

        if source_count == target_count:
            print(f"✓ ({target_count} records)")
            return True
        else:
            print(f"⚠️  ({source_count} source, {target_count} target)")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        await target_session.rollback()
        return False


async def verify_migration(source_session: AsyncSession, target_session: AsyncSession):
    """Verify that all data was migrated correctly."""
    print("\n🔍 Verifying migration...")
    print("=" * 60)

    all_match = True

    for table_name, model in MIGRATION_ORDER:
        source_count = await get_table_count(source_session, model)
        target_count = await get_table_count(target_session, model)

        status = "✓" if source_count == target_count else "❌"
        print(f"  {status} {table_name:30} Source: {source_count:5} | Target: {target_count:5}")

        if source_count != target_count:
            all_match = False

    print("=" * 60)

    return all_match


async def main():
    """Main migration function."""
    print("\n" + "=" * 60)
    print("  PostgreSQL → SQLite Data Migration")
    print("=" * 60 + "\n")

    # Create engines
    source_engine, target_engine = await create_engines()

    # Create session factories
    SourceSession = sessionmaker(source_engine, class_=AsyncSession, expire_on_commit=False)
    TargetSession = sessionmaker(target_engine, class_=AsyncSession, expire_on_commit=False)

    print("⚙️  Migration Steps:")
    print("  1. Read data from PostgreSQL")
    print("  2. Write data to SQLite")
    print("  3. Verify data integrity")
    print()

    # Confirm before proceeding
    response = input("Continue with migration? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Migration cancelled")
        return

    print()

    # Create sessions
    async with SourceSession() as source_session, TargetSession() as target_session:
        print("📦 Migrating tables...")
        print("=" * 60)

        success_count = 0
        total_count = len(MIGRATION_ORDER)

        # Migrate each table in order
        for table_name, model in MIGRATION_ORDER:
            success = await migrate_table(source_session, target_session, table_name, model)
            if success:
                success_count += 1

        print("=" * 60)
        print(f"\n✨ Migration Summary: {success_count}/{total_count} tables migrated successfully")

        # Verify migration
        all_match = await verify_migration(source_session, target_session)

        if all_match:
            print("\n✅ Migration completed successfully!")
            print("   All record counts match between source and target.")
        else:
            print("\n⚠️  Migration completed with warnings")
            print("   Some record counts don't match. Please review the verification output above.")

    # Close engines
    await source_engine.dispose()
    await target_engine.dispose()

    print()
    print("💾 SQLite database ready at:", os.getenv("SQLITE_URL", "./csf.db"))
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
