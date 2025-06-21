# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml .
COPY uv.lock .

# Устанавливаем uv для управления зависимостями
RUN pip install uv

# Устанавливаем зависимости
RUN uv sync

# Копируем исходный код
COPY . .

ENV PATH="/app/.venv/bin:$PATH"

# Запускаем бота
CMD ["python", "main.py"]
