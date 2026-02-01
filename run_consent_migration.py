"""Run database migration to add consent fields to broker_configs table."""

from sqlalchemy import text

from portfolio_tracker.database import engine


def run_migration():
    """Run the migration."""
    print("Running migration: Add consent_given and consent_timestamp columns to broker_configs table")

    try:
        with engine.begin() as connection:
            # Check if columns exist
            result = connection.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='broker_configs' AND column_name IN ('consent_given', 'consent_timestamp')
            """))

            existing_columns = [row[0] for row in result.fetchall()]

            if 'consent_given' in existing_columns and 'consent_timestamp' in existing_columns:
                print("ℹ️  Columns already exist, skipping migration")
                return

            # Add consent_given column if not exists
            if 'consent_given' not in existing_columns:
                connection.execute(text("""
                    ALTER TABLE broker_configs
                    ADD COLUMN consent_given BOOLEAN DEFAULT FALSE NOT NULL
                """))
                print("✅ Added consent_given column")

            # Add consent_timestamp column if not exists
            if 'consent_timestamp' not in existing_columns:
                connection.execute(text("""
                    ALTER TABLE broker_configs
                    ADD COLUMN consent_timestamp TIMESTAMP WITH TIME ZONE
                """))
                print("✅ Added consent_timestamp column")

            print("✅ Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("\nYou can run this SQL manually in your database:")
        print("""
ALTER TABLE broker_configs ADD COLUMN consent_given BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE broker_configs ADD COLUMN consent_timestamp TIMESTAMP WITH TIME ZONE;
        """)


if __name__ == "__main__":
    run_migration()