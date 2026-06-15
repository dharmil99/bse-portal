import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    host     = os.getenv("DB_HOST")
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME")
    
    url = f"mysql+pymysql://{user}:{password}@{host}/{database}"
    engine = create_engine(url)
    return engine

if __name__ == "__main__":
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Connected to MySQL successfully!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")