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

MIXPANEL_TOKEN = os.getenv("MIXPANEL_TOKEN")

ERROR_CHAT_ID = int(os.environ["ERROR_CHAT_ID"])
