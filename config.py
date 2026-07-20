import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("postgresql://postgres:Atenea123@db.usjxyskzgbbnhjivjisc.supabase.co:5432/postgresb")
SECRET_KEY = os.getenv("SECRET_KEY", "atenea_super_secret_key_change_me_in_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

