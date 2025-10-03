FROM python:3.12-slim

# Install system dependencies for sounddevice / PortAudio
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     libsndfile1 \
#     libsndfile1-dev \
#     portaudio19-dev \
#     && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy files
COPY main.py requirements.txt ./

# Expose network port
EXPOSE 2700

# Install dependencies
RUN pip install --cache-dir=/root/.cache/pip -r requirements.txt

# Run the app
CMD ["python", "main.py"]
