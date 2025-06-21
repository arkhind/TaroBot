import yaml
import re
import glob
import loguru
import random

translations = {}
for file in glob.glob("translations/strings/*.yaml"):
    language_code = re.search(r"strings\.([a-z]{2})\.yaml", file).group(1)
    with open(file, "r") as f:
        translations[language_code] = yaml.load(f, Loader=yaml.FullLoader)
assert len(translations.keys()) > 0
DEFAULT_LANGUAGE = "ru"


def get_phrase(phrase_tag, language="ru", index: None|int = None):
    """
    :param phrase_tag: тэг необходимой фразы
    :param language: необходимый язык
    :param index: индекс варианта фразы
    :return: фразу из необходимого языка.
    Если есть варианты (phrase is instance lis) и index none, то вернуть случайную
    Если index is int, то вернуть по индексу.
    Если нет вариантов, то вернуть само значение.
    """
    try:
        if language not in translations:
            language = DEFAULT_LANGUAGE
        
        if phrase_tag not in translations[language]:
            loguru.logger.warning(f"Phrase tag '{phrase_tag}' not found in language '{language}'")
            return phrase_tag
        
        phrase = translations[language][phrase_tag]
        
        # Если фраза - это список (есть варианты)
        if isinstance(phrase, list):
            if index is None:
                # Возвращаем случайную фразу из списка
                return random.choice(phrase)
            elif isinstance(index, int):
                # Возвращаем фразу по индексу
                if 0 <= index < len(phrase):
                    return phrase[index]
                else:
                    loguru.logger.warning(f"Index {index} out of range for phrase '{phrase_tag}' with {len(phrase)} variants")
                    return random.choice(phrase)
            else:
                # Некорректный тип index, возвращаем случайную
                return random.choice(phrase)
        elif isinstance(phrase, str):
            # Фраза - это строка, возвращаем как есть
            return phrase
        else:
            loguru.logger.warning(f"Phrase '{phrase_tag}' is not a string or list")
            return phrase_tag
            
    except Exception as e:
        loguru.logger.exception(e)
        return phrase_tag