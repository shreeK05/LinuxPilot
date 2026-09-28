import os

# Set PostgreSQL port to 5433 for testing, avoiding conflicts with production database
os.environ["POSTGRES_PORT"] = "5433"
