FROM python:3.11-slim

# Install system dependencies required for building awscrt
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create and activate virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies in multiple steps to handle problematic packages
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    flask-socketio==5.3.6 \
    python-dotenv==1.0.0 \
    eventlet==0.33.3 \
    gunicorn==21.2.0

# Install boto3 and related packages separately
RUN pip install --no-cache-dir \
    botocore==1.34.7 \
    boto3==1.34.7 \
    amazon-transcribe==0.5.0

# Copy application code
COPY . .

# Command to run the application
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:$PORT", "app:app"] 