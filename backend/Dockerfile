FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /usr/local/bin/

# 仮想環境はソースのマウント先（/app）の外に置く
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
