#!/usr/bin/env python3
"""
Тест для проверки обработки никнеймов в main.py
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

async def test_main_nicknames():
    """Тестирует обработку никнеймов как в main.py"""
    
    if not VOX_TOKEN:
        logger.error("VOX_TOKEN не найден в config.py")
        return
    
    vox = AsyncVoxAPI(token=VOX_TOKEN)
    
    # Тестовые случаи - имитируем то, что приходит в main.py
    test_cases = [
        ("@user_name", "user_name"),  # с нижним подчеркиванием
        ("@test_user", "test_user"),  # с нижним подчеркиванием
        ("@simple", "simple"),        # без нижнего подчеркивания
    ]
    
    logger.info("Тестирование обработки никнеймов как в main.py:")
    logger.info("=" * 50)
    
    for target_message, expected_nickname in test_cases:
        try:
            logger.info(f"\nТестируем: {target_message} -> {expected_nickname}")
            
            # Имитируем логику из main.py
            target = target_message.strip()
            if not target.startswith("@"):
                logger.error(f"❌ Неверный формат: {target}")
                continue
                
            nickname = target[1:]  # Убираем @
            logger.info(f"Извлеченный никнейм: {nickname}")
            
            # Тестируем process_user_nickname (для качеств)
            logger.info(f"Тестируем process_user_nickname для {nickname}...")
            try:
                result = await process_user_nickname(
                    vox, 
                    nickname, 
                    "Опиши этого пользователя в одном предложении."
                )
                if result:
                    logger.info(f"✅ process_user_nickname успешно для {nickname}")
                else:
                    logger.error(f"❌ process_user_nickname вернул None для {nickname}")
            except Exception as e:
                logger.error(f"❌ Ошибка в process_user_nickname для {nickname}: {e}")
            
            # Тестируем process_user_nicknames (для совместимости)
            logger.info(f"Тестируем process_user_nicknames для {nickname}...")
            try:
                result = await process_user_nicknames(
                    vox,
                    "test_user",  # фиксированный пользователь для теста
                    nickname,
                    "Проанализируй совместимость этих людей."
                )
                if result:
                    logger.info(f"✅ process_user_nicknames успешно для {nickname}")
                else:
                    logger.error(f"❌ process_user_nicknames вернул None для {nickname}")
            except Exception as e:
                logger.error(f"❌ Ошибка в process_user_nicknames для {nickname}: {e}")
                
        except Exception as e:
            logger.error(f"❌ Общая ошибка для {target_message}: {e}")
    
    await vox.close()
    logger.info("\nТест завершен!")

if __name__ == "__main__":
    asyncio.run(test_main_nicknames()) 