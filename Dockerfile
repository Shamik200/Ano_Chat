# Use official Python image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy files to the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "main.py"]
