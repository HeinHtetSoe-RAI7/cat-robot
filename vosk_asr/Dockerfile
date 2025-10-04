# FROM python:3.12-slim

# # Install system dependencies for sounddevice / PortAudio
# # RUN apt-get update && apt-get install -y \
# #     build-essential \
# #     libsndfile1 \
# #     libsndfile1-dev \
# #     portaudio19-dev \
# #     && rm -rf /var/lib/apt/lists/*

# # Set working directory
# WORKDIR /app

# # Copy files
# COPY main.py requirements.txt ./

# # Expose network port
# EXPOSE 2700

# # Install dependencies
# RUN pip install --cache-dir=/root/.cache/pip -r requirements.txt

# # Run the app
# CMD ["python", "main.py"]

# ===== Stage 1: Build dependencies =====
FROM python:3.12-slim AS builder

# Install system dependencies needed for building Python packages
# RUN apt-get update && apt-get install -y \
#         build-essential \
#         libsndfile1-dev \
#         portaudio19-dev \
#     && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only requirements first for caching
COPY requirements.txt ./

# Install Python dependencies into a temporary directory
RUN pip install --prefix=/install --cache-dir=/root/.cache/pip -r requirements.txt

# ===== Stage 2: Runtime =====
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy installed Python packages from the builder
COPY --from=builder /install /usr/local

# Copy application code
COPY main.py ./

# Expose network port
EXPOSE 2700

# Run the app
CMD ["python", "main.py"]
