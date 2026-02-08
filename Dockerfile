FROM python:3.13-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create data directory with proper permissions
RUN mkdir -p /app/data && chmod 777 /app/data

# Expose Gradio default port
EXPOSE 7860

# Run the application
CMD ["python", "main.py"]
