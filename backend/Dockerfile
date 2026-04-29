FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    poppler-utils \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt


COPY . .

EXPOSE 2020

RUN mkdir -p data

CMD ["uvicorn", "MainApplicationRunner:app", "--host", "0.0.0.0", "--port", "2020"]