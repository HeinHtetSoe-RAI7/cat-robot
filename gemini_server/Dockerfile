# # ===== Single Stage Go Build =====
# FROM golang:1.24.4

# WORKDIR /app

# # Copy local dependency manifests and cache (no internet fetching)
# COPY go.mod go.sum ./

# # Copy the rest of your project
# COPY . .

# # Optional: install CA certificates (safe fallback)
# RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
#     && rm -rf /var/lib/apt/lists/*

# # Build the binary (optimized, no cgo)
# RUN go build -ldflags="-s -w" -o gemini-server main.go

# # Expose port (if applicable)
# EXPOSE 8765

# # Default command
# CMD ["./gemini-server"]

# ===== Multi-stage Build =====
# Build stage
FROM golang:1.24.4-alpine AS builder

WORKDIR /app

# Copy only go.mod and go.sum (no download/tidy)
COPY go.mod go.sum ./

# Copy the rest of your project
COPY . .

# Build the binary (optimized, no cgo)
RUN go build -ldflags="-s -w" -o gemini-server .

# Runtime stage
FROM alpine:latest

WORKDIR /root/

# Install CA certificates
RUN apk --no-cache add ca-certificates

# Copy the binary from builder
COPY --from=builder /app/gemini-server .

EXPOSE 8765

CMD ["./gemini-server"]
