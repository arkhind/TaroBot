from vox.api import VoxAPI
from vox.models import Subject
from dotenv import load_dotenv
import os
import json

load_dotenv()

vox = VoxAPI(token=os.getenv("VOX_TOKEN"))

nickname = 'g_engel'
user_id = vox.get_user_id(nickname)['id']

ai_analytic = vox.ai_analytics(subject=Subject.USER, subject_id=user_id)
if 'report' in ai_analytic:
    ai_analytic = ai_analytic['report']
print(ai_analytic)

report = vox.custom_report(subject=Subject.USER, subject_id=user_id,
                           custom_prompt=str(ai_analytic)+"\n\nНапиши предсказание для этого человека на неделю. " +\
                           "Пиши в стиле гадания на картах таро. Укажи название карт и что это значит. " +\
                           "В начале напиши что раскладываешь карты. Отделяй каждую карту и ее описание \\n\\n. " +\
                           "В конце через \\n\\n напиши рекомендацию от карт на неделю. "+\
                           "Используй эмодзи. Не ссылайся на активность в конкретных каналах и чатах.")
if 'report' in report:
    report = json.loads(report['report'])
    if 'report' in report:
        report = report['report']
print(report)

