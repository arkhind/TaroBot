from vox.api import VoxAPI
from vox.models import Subject
import json
from config import VOX_TOKEN
from loguru import logger

vox = VoxAPI(token=VOX_TOKEN)

def _process_report_lines(report_str: str) -> str:
    lines = report_str.split('\n')
    processed_lines = []
    for line in lines:
        if line.strip().startswith('* '):
            first_star_index = line.find('*')
            if first_star_index != -1:
                line = line[:first_star_index] + '-' + line[first_star_index+1:]
        processed_lines.append(line)
    return '\n'.join(processed_lines)

def process_user_nickname(nickname, prompt):
    try:
        user_id = vox.get_user_id(nickname)['id']

        ai_analytic = vox.ai_analytics(subject=Subject.USER, subject_id=user_id)
        if 'report' in ai_analytic:
            ai_analytic = ai_analytic['report']

        report = vox.custom_report(subject=Subject.USER, subject_id=user_id,
                                   custom_prompt=f"{str(ai_analytic)}\n\n{prompt}")
        if 'report' in report:
            report = json.loads(report['report'])
            if 'report' in report:
                report = report['report']
                return _process_report_lines(report)
    except Exception as e:
        logger.error(f'Error in process_user_nickname: {e}')
    return None

def process_user_nicknames(from_user, about_user, prompt):
    logger.info(f'run process_user_nicknames for {from_user} about {about_user}; prompt:\n{prompt}')
    try:
        from_user_id = vox.get_user_id(from_user)['id']
        airep_from_user = vox.ai_analytics(subject=Subject.USER, subject_id=from_user_id)
        if 'report' in airep_from_user:
            airep_from_user = airep_from_user['report']

        about_user_id = vox.get_user_id(about_user)['id']
        airep_about_user = vox.ai_analytics(subject=Subject.USER, subject_id=about_user_id)
        if 'report' in airep_about_user:
            airep_about_user = airep_about_user['report']

        report = vox.custom_report(subject=Subject.USER, subject_id=about_user_id,
                                   custom_prompt=f"Пользователь {from_user}\n{str(airep_from_user)}\n\n" +\
                                                 f"Спросил о {about_user}\n{str(airep_about_user)}\n\n{prompt}")
        if 'report' in report:
            report = json.loads(report['report'])
            if 'report' in report:
                # logger.info(report_data['report'])
                report = report['report']
                logger.info(report)
                report = _process_report_lines(report)
                logger.info(report)
                return report
    except Exception as e:
        logger.error(f"Error occurred in process_user_nicknames: {e}")
    return None

# Пример вызова:
# process_user_nickname('narhipovd', 'что интересно данному пупсу')