FROM python:3.10-slim

# Install all OpenCV dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libsm6 \
    libxrender1 \
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Run the app
CMD ["python", "main.py"]
