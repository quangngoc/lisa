# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory to /app
WORKDIR /app

# Copy the app.py into the container at /app
COPY app.py .

# Install the required packages
RUN pip install --no-cache-dir fastapi[standard] uvicorn[standard]

# Expose port 8080 to the outside world
EXPOSE 8080

# Command to run the application with Uvicorn on port 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]