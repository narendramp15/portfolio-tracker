"""Run database migration to add last_price_update column."""

from sqlalchemy import text

from portfolio_tracker.database import engine


def run_migration():
    """Run the migration."""
    print("Running migration: Add last_price_update column to assets table")
    
    try:
        with engine.begin() as connection:
            # Check if column exists first
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='assets' AND column_name='last_price_update'
            """))
            
            if result.fetchone():
                print("ℹ️  Column already exists, skipping migration")
                return
            
            # Add the column
            connection.execute(text("""
                ALTER TABLE assets 
                ADD COLUMN last_price_update TIMESTAMP WITH TIME ZONE
            """))
            
            # Set default value for existing rows
            connection.execute(text("""
                UPDATE assets 
                SET last_price_update = CURRENT_TIMESTAMP
            """))
            
            print("✅ Migration completed successfully!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("\nYou can run this SQL manually in your Neon console:")
        print("""
ALTER TABLE assets ADD COLUMN last_price_update TIMESTAMP WITH TIME ZONE;
UPDATE assets SET last_price_update = CURRENT_TIMESTAMP;
        """)

if __name__ == "__main__":
    run_migration()
