import os
from dotenv import load_dotenv
from openai import OpenAI

# Загружаем переменные окружения из .env файла
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ask_gpt(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=800,
    )
    content = response.choices[0].message.content
    return content.strip() if content else "" 