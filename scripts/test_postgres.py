import os
import sys
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL", "postgresql://tathya:tathya@localhost:5432/tathya")
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

print(f"Testing PostgreSQL connection to: {db_url}")

try:
    from sqlalchemy import create_engine, text
    engine = create_engine(db_url, connect_args={"connect_timeout": 3})

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        print(f"SELECT 1 result: {result}")
        
        # Test temporary table
        conn.execute(text("CREATE TEMPORARY TABLE tathya_test (id serial, val text)"))
        conn.execute(text("INSERT INTO tathya_test (val) VALUES ('smoke_test')"))
        val = conn.execute(text("SELECT val FROM tathya_test")).scalar()
        conn.execute(text("DROP TABLE tathya_test"))
        print(f"Temporary table test passed: val={val}")
        
    print("POSTGRES_SERVER: PASS")
    print("DB_CONNECTION: PASS")
    print("SQLALCHEMY: PASS")
except Exception as e:
    print(f"POSTGRES_SERVER: FAIL ({e})")
    print("DB_CONNECTION: FAIL")
    print("SQLALCHEMY: FAIL")
    print("\nACTION NEEDED: Start local PostgreSQL server or configure DATABASE_URL in .env before H0.")
