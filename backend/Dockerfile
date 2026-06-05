FROM python:3.10-slim

# Create a non-root user (optional) and set workdir
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment in a writable location and install Python dependencies there
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
# Install packages into the virtual environment without caching to reduce image size
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Use the virtual environment's Python to run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
