# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables (for example, you could directly provide them here, but it's recommended to set them via Render's environment settings)
# ENV TELEGRAM_TOKEN=<your_telegram_token> (Don't hardcode secrets in Dockerfiles)

# Expose the port the bot will run on (if needed, typically bots don't require port exposure unless using webhooks)
EXPOSE 8443

# Run bot.py when the container launches
CMD ["python", "bot.py"]
