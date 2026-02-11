FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs recordings

EXPOSE 8080

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
