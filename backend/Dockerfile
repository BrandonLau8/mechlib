FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    exiftool \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies (including api extras for FastAPI)
RUN uv sync

# Copy application code
COPY . .

# Copy ExifTool config
COPY .ExifTool_config /app/.ExifTool_config

# Expose API port
EXPOSE 8000

# Run the FastAPI server with auto-reload for development
CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]