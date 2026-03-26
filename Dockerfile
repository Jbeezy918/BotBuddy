FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create data directory
RUN mkdir -p /root/.robobuddy

# Expose port (Railway sets $PORT dynamically)
EXPOSE 8000

# Run the app - Railway overrides this with its own start command
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
