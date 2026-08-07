# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install system dependencies
RUN apt-get update && \
    apt-get install -y libcairo2-dev inkscape fontconfig ghostscript && \
    rm -rf /var/lib/apt/lists/*

# Create a directory for fonts
RUN mkdir -p /usr/share/fonts/truetype/

# Copy fonts to the system directory
RUN cp -r /usr/src/app/Fonts /usr/share/fonts/truetype/

# Refresh system font cache so Inkscape can find them
RUN fc-cache -f -v

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["python", "-u", "./bot.py"]
