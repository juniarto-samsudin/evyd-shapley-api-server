# Use an official Python runtime as a parent image
FROM python:3.10-alpine

# Set the working directory to /app
WORKDIR /app

# Create /app/logs and /app/uploads directories
RUN mkdir -p /app/logs 

COPY . /app

# Install any needed packages specified in requirements.txt
#RUN pip install --no-cache-dir flask
RUN pip install --no-cache-dir -r requirements.txt

# Run app.py when the container launches
CMD ["python", "app.py"]
