FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MONGO_HOST=mongodb
ENV MONGO_PORT=27017
ENV PORT=7861

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY set_up_globals.py .
COPY utilities.py .
COPY program_actions.py .
COPY data/ data/
COPY services/ services/
COPY infrastructure/ infrastructure/
COPY src/ src/

# Install dependencies using uv
RUN uv sync --no-dev

# Create uploads directory
RUN mkdir -p /app/uploads

# Expose port
EXPOSE 7861

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7861/ || exit 1

# Run the application
CMD ["uv", "run", "python", "-m", "src.mecfs_ui.app"]
