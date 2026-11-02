FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Зависимости отдельным слоем: при правках кода они не переустанавливаются
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY migrations/ migrations/
COPY app/ app/
COPY scripts/ scripts/

# Непривилегированный пользователь; /app принадлежит ему,
# потому что scripts/check_imdb.py пишет файлы в рабочую директорию
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8000

# Миграции накатываются при каждом запуске, затем стартует API
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
