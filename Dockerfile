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
    flask \
    flask-socketio \
    python-dotenv \
    eventlet \
    gunicorn

# Install AWS packages without version constraints
RUN pip install --no-cache-dir \
    boto3 \
    amazon-transcribe

# Copy application code
COPY . .

# Command to run the application
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:$PORT", "app:app"] 