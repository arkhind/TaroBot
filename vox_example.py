from vox.api import VoxAPI
from vox.models import Subject
from dotenv import load_dotenv
import os
import json

load_dotenv()

vox = VoxAPI(token=os.getenv("VOX_TOKEN"))

def process_user_nickname(nickname, prompt):
    try:
        user_id = vox.get_user_id(nickname)['id']

        ai_analytic = vox.ai_analytics(subject=Subject.USER, subject_id=user_id)
        if 'report' in ai_analytic:
            ai_analytic = ai_analytic['report']

        report = vox.custom_report(subject=Subject.USER, subject_id=user_id,
                                   custom_prompt=f"{str(ai_analytic)}\n\n{prompt}")
        if 'report' in report:
            report_data = json.loads(report['report'])
            if 'report' in report_data:
                return report_data['report']
    except Exception as e:
        print(f"An error occurred: {e}")
    return None

# Пример вызова:
# process_user_nickname('g_engel', 'что интересно данному пупсу')
