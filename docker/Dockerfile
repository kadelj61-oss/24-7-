# Build stage
FROM python:3.10 as builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.10-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

RUN mkdir -p logs recordings

EXPOSE 8080
ENV PYTHONUNBUFFERED=1
ENV PATH=/root/.local/bin:$PATH

CMD ["python", "main.py"]
