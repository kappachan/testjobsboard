import os
from dotenv import load_dotenv
from supabase.client import create_client, Client
import traceback

load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

print(f"SUPABASE_URL: {supabase_url}")
print(f"SUPABASE_KEY: {'*' * len(supabase_key) if supabase_key else None}")

supabase: Client = create_client(
    supabase_url=supabase_url,
    supabase_key=supabase_key
)

def cleanup_table(table_name: str) -> bool:
    """Clean up a single table."""
    try:
        print(f"Cleaning {table_name} table...")
        supabase.table(table_name).delete().neq("id", 0).execute()
        print(f"✓ {table_name} table cleaned")
        return True
    except Exception as e:
        if "does not exist" in str(e):
            print(f"! {table_name} table does not exist")
        else:
            print(f"! Error cleaning {table_name} table: {str(e)}")
        return False

def cleanup_db():
    """Clean up all tables while preserving schema."""
    try:
        print("Cleaning up database...")
        
        # Clean each table independently
        tables = ["jobs", "snapshots", "monitors"]
        results = []
        for table in tables:
            results.append(cleanup_table(table))
        
        # Consider it successful if at least one table was cleaned
        if any(results):
            print("Database cleanup completed successfully!")
            return True
        else:
            print("No tables were cleaned!")
            return False
    except Exception as e:
        print(f"Error cleaning database: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return False

def verify_db():
    """Verify database connection and table existence."""
    try:
        print("Verifying Supabase connection...")
        
        # Check monitors table
        print("\nChecking monitors table...")
        monitors = supabase.table("monitors").select("*").limit(1).execute()
        print("✓ Monitors table exists")
        
        # Check snapshots table
        print("\nChecking snapshots table...")
        snapshots = supabase.table("snapshots").select("*").limit(1).execute()
        print("✓ Snapshots table exists")
        
        # Check jobs table
        print("\nChecking jobs table...")
        jobs = supabase.table("jobs").select("*").limit(1).execute()
        print("✓ Jobs table exists")
        
        print("\nAll tables verified successfully!")
        return True
    except Exception as e:
        print(f"Error verifying database: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # First clean up the database
    if cleanup_db():
        print("\nDatabase cleanup completed successfully!")
    else:
        print("\nDatabase cleanup failed!")
    
    # Then verify the database structure
    if verify_db():
        print("\nDatabase verification completed successfully!")
    else:
        print("\nDatabase verification failed!")