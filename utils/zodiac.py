from datetime import date


def get_zodiac_sign(birth_date: date) -> str:
    """Определяет знак зодиака по дате рождения и возвращает тег для перевода"""
    month = birth_date.month
    day = birth_date.day

    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "zodiac_aries"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "zodiac_taurus"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "zodiac_gemini"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "zodiac_cancer"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "zodiac_leo"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "zodiac_virgo"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "zodiac_libra"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "zodiac_scorpio"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "zodiac_sagittarius"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "zodiac_capricorn"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "zodiac_aquarius"
    else:
        return "zodiac_pisces"
