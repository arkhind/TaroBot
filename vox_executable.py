from vox.asyncapi import AsyncVoxAPI
from vox.models import Subject
import json
from config import VOX_TOKEN
from loguru import logger
from utils.openai_gpt import ask_gpt


def _process_report_lines(report_str: str) -> str:
    lines = report_str.split("\n")
    processed_lines = []
    for line in lines:
        if line.strip().startswith("* "):
            first_star_index = line.find("*")
            if first_star_index != -1:
                line = line[:first_star_index] + "-" + line[first_star_index + 1 :]
        processed_lines.append(line)
    return "\n".join(processed_lines)


async def process_user_nickname(vox: AsyncVoxAPI, nickname, prompt):
    try:
        if not nickname:
            # Fallback: если нет ника, используем GPT напрямую
            logger.info("[DEBUG] process_user_nickname: nickname is None or empty, fallback to GPT")
            return ask_gpt(prompt)
        logger.info(f"[DEBUG] process_user_nickname: начинаем обработку {nickname}")
        logger.info(f"[DEBUG] process_user_nickname: вызываем get_user_id с nickname={nickname}")
        user_id_response = await vox.get_user_id(nickname)
        logger.info(f"[DEBUG] process_user_nickname: ответ get_user_id: {user_id_response}")
        user_id = user_id_response["id"]
        logger.info(f"[DEBUG] process_user_nickname: используем user_id={user_id}")

        logger.info(f"[DEBUG] process_user_nickname: получаем AI аналитику для {nickname}")
        ai_analytic = await vox.ai_analytics(subject=Subject.USER, subject_id=user_id)
        logger.info(f"[DEBUG] process_user_nickname: AI аналитика получена: {type(ai_analytic)}")
        
        # Проверяем, есть ли данные от VOX
        if ai_analytic is None or (isinstance(ai_analytic, dict) and not ai_analytic.get("report")):
            logger.info(f"[DEBUG] process_user_nickname: нет данных от VOX для {nickname}, отправляем промпт напрямую в ChatGPT")
            # Отправляем промпт напрямую в ChatGPT
            return ask_gpt(prompt)
        else:
            if "report" in ai_analytic:
                ai_analytic = ai_analytic["report"]
                logger.info(f"[DEBUG] process_user_nickname: извлекли report из AI аналитики")

            logger.info(f"[DEBUG] process_user_nickname: создаем кастомный отчет для {nickname}")
            report = await vox.custom_report(
                subject=Subject.USER,
                subject_id=user_id,
                custom_prompt=f"{str(ai_analytic)}\n\n{prompt}",
            )
        
        logger.info(f"[DEBUG] process_user_nickname: кастомный отчет получен: {type(report)}")
        
        # Проверяем, есть ли report в ответе
        if report and "report" in report and report["report"]:
            logger.info(f"[DEBUG] process_user_nickname: извлекаем report из ответа")
            try:
                report_data = json.loads(report["report"])
                logger.info(f"[DEBUG] process_user_nickname: распарсенный JSON: {report_data}")
                if "report" in report_data:
                    report_text = report_data["report"]
                    logger.info(f"[DEBUG] process_user_nickname: финальный report получен")
                    return _process_report_lines(report_text)
                else:
                    logger.error(f"[DEBUG] process_user_nickname: нет 'report' в распарсенном JSON")
            except json.JSONDecodeError:
                logger.error(f"[DEBUG] process_user_nickname: ошибка парсинга JSON")
        else:
            logger.info(f"[DEBUG] process_user_nickname: нет 'report' в ответе API или пустой ответ, отправляем промпт напрямую в ChatGPT")
            return ask_gpt(prompt)
    except Exception as e:
        logger.error(f"Error in process_user_nickname for {nickname}: {e}")
        logger.exception(f"Full traceback for process_user_nickname error:")
        raise
    return None


async def process_user_nicknames(vox: AsyncVoxAPI, from_user, about_user, prompt):
    logger.info(
        f"run process_user_nicknames for {from_user} about {about_user}; prompt:\n{prompt}"
    )
    try:
        from_user_id = await vox.get_user_id(from_user)
        from_user_id = from_user_id["id"]
        
        airep_from_user = await vox.ai_analytics(
            subject=Subject.USER, subject_id=from_user_id
        )
        # Проверяем, есть ли данные от VOX для первого пользователя
        if airep_from_user is None or (isinstance(airep_from_user, dict) and not airep_from_user.get("report")):
            logger.info(f"[DEBUG] process_user_nicknames: нет данных от VOX для {from_user}")
            airep_from_user = f"Пользователь: {from_user}"
        else:
            if "report" in airep_from_user:
                airep_from_user = airep_from_user["report"]

        about_user_id = await vox.get_user_id(about_user)
        about_user_id = about_user_id["id"]
        
        airep_about_user = await vox.ai_analytics(
            subject=Subject.USER, subject_id=about_user_id
        )
        # Проверяем, есть ли данные от VOX для второго пользователя
        if airep_about_user is None or (isinstance(airep_about_user, dict) and not airep_about_user.get("report")):
            logger.info(f"[DEBUG] process_user_nicknames: нет данных от VOX для {about_user}")
            airep_about_user = f"Пользователь: {about_user}"
        else:
            if "report" in airep_about_user:
                airep_about_user = airep_about_user["report"]

        report = await vox.custom_report(
            subject=Subject.USER,
            subject_id=about_user_id,
            custom_prompt=f"Я {from_user}\n{str(airep_from_user)}\n\n"
            + f"Спросил о {about_user}\n{str(airep_about_user)}\n\n{prompt}",
        )
        
        # Проверяем, есть ли report в ответе
        if report and "report" in report and report["report"]:
            try:
                report_data = json.loads(report["report"])
                if "report" in report_data:
                    report_text = report_data["report"]
                    logger.info(report_text)
                    report_processed = _process_report_lines(report_text)
                    logger.info(report_processed)
                    return report_processed
            except json.JSONDecodeError:
                logger.error(f"[DEBUG] process_user_nicknames: ошибка парсинга JSON")
        else:
            logger.info(f"[DEBUG] process_user_nicknames: нет 'report' в ответе API или пустой ответ, отправляем промпт напрямую в ChatGPT")
            return ask_gpt(prompt)
    except Exception as e:
        logger.error(f"Error occurred in process_user_nicknames: {e}")
        logger.exception(f"Full traceback for process_user_nicknames error:")
        raise
    return None


# Пример вызова:
# process_user_nickname('narhipovd', 'что интересно данному пупсу')
