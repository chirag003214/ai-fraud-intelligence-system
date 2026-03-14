# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirement files first (to leverage Docker caching)
COPY backend/requirements.txt ./backend/requirements.txt

# Install build dependencies, install python packages, and cleanup in one layer
RUN apt-get update && apt-get install -y build-essential \
    && pip install --no-cache-dir -r backend/requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code
COPY . /app

# Expose the designated port
EXPOSE 10000

# Set Python path so `backend.main` is resolvable
ENV PYTHONPATH=/app

# Start the FastAPI application.
# (If deploying on Render.com, Render will automatically inject the "PORT" environment variable
#  if you need dynamic binding, you could use `--port ${PORT:-10000}`)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]
