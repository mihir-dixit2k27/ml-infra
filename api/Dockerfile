# api/Dockerfile

# Start from a slim Python base image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the main requirements file first to leverage Docker cache
# Assumes requirements.txt is in the parent directory (project root)
COPY requirements.txt .

# Install all dependencies including uvicorn for serving
# Ensure mlflow is included as it's needed to load the model
RUN pip install --no-cache-dir -r requirements.txt uvicorn

# Copy your API code into the container
# Copy the entire api directory to maintain package structure
COPY ./api /app/api

# Expose the port the app will run on
EXPOSE 8000

# Command to run the application using uvicorn
# --host 0.0.0.0 makes it accessible from outside the container
CMD ["uvicorn", "api.simple_api:app", "--host", "0.0.0.0", "--port", "8000"]
