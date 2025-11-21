# Use Python 3.11
FROM python:3.11-slim

# Create working directory
WORKDIR /code

# Install system dependencies if Selenium or others need them
RUN apt-get update && apt-get install -y \
    wget curl unzip xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code
COPY src ./src
COPY static ./static
COPY public ./public
COPY run_app.py .

# Expose Render port
EXPOSE 8000

# Start FastAPI via run_app.py
CMD ["python", "run_app.py"]
