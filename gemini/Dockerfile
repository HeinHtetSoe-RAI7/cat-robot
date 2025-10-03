# Dockerfile
FROM python:3.12-slim

# Create app directory
WORKDIR /app

# Copy server and client scripts
COPY gemini_server.py gemini_client.py requirements.txt ./

# Install required packages
RUN pip install -r requirements.txt

# Default command (can be overridden in compose)
CMD ["python", "gemini_server.py"]
