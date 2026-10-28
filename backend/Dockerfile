FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# On installe FastAPI et Uvicorn
RUN pip install fastapi uvicorn

COPY . .

# On expose l'API sur le port 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]