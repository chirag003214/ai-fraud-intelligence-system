# Use official Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY . .

# Expose the port
EXPOSE 10000

# Start the Backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]