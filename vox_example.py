from vox.api import VoxAPI
from vox.models import Subject
import json
from config import VOX_TOKEN
from loguru import logger

vox = VoxAPI(token=VOX_TOKEN)

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
        logger.error(f'Error in process_user_nickname: {e}')
    return None

def process_user_nicknames(nickname_user, nickname_find, prompt):
    try:
        user_id = vox.get_user_id(nickname_user)['id']
        ai_analytic_user = vox.ai_analytics(subject=Subject.USER, subject_id=user_id)
        if 'report' in ai_analytic_user:
            ai_analytic_user = ai_analytic_user['report']

        find_id = vox.get_user_id(nickname_find)['id']
        ai_analytic_find = vox.ai_analytics(subject=Subject.USER, subject_id=find_id)
        if 'report' in ai_analytic_find:
            ai_analytic_find = ai_analytic_find['report']

        report = vox.custom_report(subject=Subject.USER, subject_id=user_id,
                                   custom_prompt=f"Пользователь:\n{str(ai_analytic_user)}\n\n{nickname_find}:\n{str(ai_analytic_find)}\n\n{prompt}")
        if 'report' in report:
            report_data = json.loads(report['report'])
            if 'report' in report_data:
                logger.info(report_data['report'])
                return report_data['report']
    except Exception as e:
        logger.error(f"Error occurred in process_user_nicknames: {e}")
    return None

# Пример вызова:
# process_user_nickname('narhipovd', 'что интересно данному пупсу')