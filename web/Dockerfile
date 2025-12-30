# web/Dockerfile
FROM python:3.13-slim-bookworm

# Zmienne środowiskowe
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instalacja zależności systemowych (Postgres + ewentualnie inne biblioteki)
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     gcc \
     libpq-dev \
     netcat-openbsd \
     # Jeśli używasz Pillow (obrazki), dodaj te biblioteki:
     libjpeg-dev \
     zlib1g-dev \
  && rm -rf /var/lib/apt/lists/*

# Instalacja zależności Python
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt
# Dodajemy gunicorn i psycopg2 (jeśli nie ma w requirements)
RUN pip install psycopg2-binary gunicorn

# Kopiowanie kodu
COPY . /app/

# Skrypt startowy
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
