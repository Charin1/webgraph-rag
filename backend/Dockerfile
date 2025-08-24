# Use a stable, slim version of Python
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's layer caching.
# The long pip install step will only re-run if this file changes.
COPY requirements.txt /app/requirements.txt

# Install system dependencies, Python packages, and pre-cache AI models in a single RUN command
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    # Install Playwright's system dependencies for the Chromium browser
    && playwright install-deps chromium \
    # Install Python packages
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt \
    # Install the Playwright browser itself
    && playwright install chromium \
    # Pre-download and cache the AI models. This makes application startup almost instant.
    && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" \
    && python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')" \
    # Clean up apt caches to keep the final image size smaller
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code
COPY ./app /app/app

# Expose the port the application will run on
EXPOSE 8000

# Set the default command to run the application.
# Note: For development with live-reload, this is overridden in docker-compose.yml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]