# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Create a directory for fonts
RUN mkdir -p /usr/share/fonts/truetype/

# Copy fonts to the system directory
RUN cp -r /usr/src/app/Fonts /usr/share/fonts/truetype/

# Install system dependencies
RUN apt-get update && \
    apt-get install -y libcairo2-dev inkscape && \
    rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["python", "./bot.py"]
