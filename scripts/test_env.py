import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Print environment variables
print("Environment Variables:")
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY')}")
print(f"FIRECRAWL_API_KEY: {os.getenv('FIRECRAWL_API_KEY')}")
print(f"DEBUG: {os.getenv('DEBUG')}")
print(f"HOST: {os.getenv('HOST')}")
print(f"PORT: {os.getenv('PORT')}")
print(f"CHECK_INTERVAL: {os.getenv('CHECK_INTERVAL')}")
print(f"MAX_WORKERS: {os.getenv('MAX_WORKERS')}") 