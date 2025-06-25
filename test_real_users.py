#!/usr/bin/env python3
"""
Тест с реальными никнеймами для проверки работы API
"""

import asyncio
import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vox.asyncapi import AsyncVoxAPI
from vox.models import Subject
from vox_executable import process_user_nicknames, process_user_nickname
from config import VOX_TOKEN
from loguru import logger

async def test_real_users():
    """Тестирует работу с реальными пользователями"""
    
    if not VOX_TOKEN:
        logger.error("VOX_TOKEN не найден в config.py")
        return
    
    vox = AsyncVoxAPI(token=VOX_TOKEN)
    
    # Реальные никнеймы, которые точно существуют (из предыдущих тестов)
    real_users = [
        "user_name",  # ID: 139802264
        "test_user",  # ID: 1000370642
    ]
    
    logger.info("Тестирование с реальными пользователями:")
    logger.info("=" * 40)
    
    for nickname in real_users:
        try:
            logger.info(f"\nТестируем реального пользователя: @{nickname}")
            
            # Тестируем process_user_nickname
            logger.info(f"Тестируем process_user_nickname для {nickname}...")
            result = await process_user_nickname(
                vox, 
                nickname, 
                "Опиши этого пользователя в одном предложении."
            )
            if result:
                logger.info(f"✅ process_user_nickname успешно для {nickname}")
                logger.info(f"Результат: {result[:100]}...")
            else:
                logger.error(f"❌ process_user_nickname вернул None для {nickname}")
            
            # Тестируем process_user_nicknames
            logger.info(f"Тестируем process_user_nicknames для {nickname}...")
            result = await process_user_nicknames(
                vox,
                "user_name",  # используем другого реального пользователя
                nickname,
                "Проанализируй совместимость этих людей."
            )
            if result:
                logger.info(f"✅ process_user_nicknames успешно для {nickname}")
                logger.info(f"Результат: {result[:100]}...")
            else:
                logger.error(f"❌ process_user_nicknames вернул None для {nickname}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка для {nickname}: {e}")
    
    await vox.close()
    logger.info("\nТест завершен!")

if __name__ == "__main__":
    asyncio.run(test_real_users()) 