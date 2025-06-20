from vox.api import VoxAPI
from vox.models import Subject
from dotenv import load_dotenv
import os

load_dotenv()

vox = VoxAPI(token=os.getenv("VOX_TOKEN"))

nickname = 'narhipovd'
user_id = vox.get_user_id(nickname)['id']

ai_analytic = vox.ai_analytics(subject=Subject.USER, subject_id=user_id)
print(ai_analytic)

report = vox.custom_report(subject=Subject.USER, subject_id=user_id,
                           custom_prompt=str(ai_analytic)+"\n\nНапиши предсказание для этого человека на неделю. " +\
                           "Пиши в стиле гадания на картах таро. Укажи название карт и что это значит. " +\
                           "Используй эмодзи в меру.")['report']
print(report)

