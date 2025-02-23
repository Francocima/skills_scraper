# Dockerfile
# Start with Python 3.9 slim image to keep the size down while having all we need
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /app

# Install system dependencies needed for Playwright
# We need these for the browser automation to work properly

# Copy your requirements file
COPY requirements.txt .

# Install system dependencies required for Playwright and Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    libnss3 \
    libgdk-pixbuf2.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcomposite1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libnspr4 \
    libxss1 \
    libxtst6 \
    fonts-liberation \
    libappindicator3-1 \
    libu2f-udev \
    libozone1 \
    xdg-utils && rm -rf /var/lib/apt/lists/*

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
