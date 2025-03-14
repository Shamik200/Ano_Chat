# Use a lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "main.py"]
