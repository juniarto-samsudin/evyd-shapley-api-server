# Use an official Python runtime as a parent image
FROM python:3.10-alpine

# Set the working directory to /app
WORKDIR /app

# Create /app/logs and /app/uploads directories
RUN mkdir -p /app/logs /app/uploads

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
#RUN pip install --no-cache-dir flask
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
# COMMENT OUT THE LINE BELOW TO RUN IN PRODUCTION
# ENV FLASK_ENV=development 
# ENV FLASK_DEBUG=1

# Run app.py when the container launches
CMD ["flask", "run"]
