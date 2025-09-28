# dockerfile for ucs-detect - unicode terminal detection tool
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install the package in development mode
RUN pip install -e .

# Default command
CMD ["ucs-detect", "--help"]