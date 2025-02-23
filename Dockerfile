# Dockerfile
# Start with Python 3.9 slim image to keep the size down while having all we need
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /app

# Install system dependencies needed for Playwright
# We need these for the browser automation to work properly
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy your requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its dependencies
# This is crucial for the web scraping to work
RUN playwright install chromium
RUN playwright install-deps

# Copy all your application files
COPY . .

# Command to run the API when the container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
