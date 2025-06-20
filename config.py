import os
from dotenv import load_dotenv

load_dotenv()

PGPASSWORD = os.environ["PGPASSWORD"]  # Обязательное поле
PGUSER = os.environ["PGUSER"]
PGDATABASE = os.environ["PGDATABASE"]
PGHOST = os.environ["PGHOST"]
VOX_TOKEN = os.environ["VOX_TOKEN"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# os.getenv для необязательных полей. Вернет None если нет