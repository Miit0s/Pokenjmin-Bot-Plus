# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install system dependencies
RUN apt-get update && \
    apt-get install -y libcairo2-dev inkscape && \
    rm -rf /var/lib/apt/lists/*
	
#Remove all installed font to have a clean slate
RUN rm -rf /usr/share/fonts/

#Install some default fonts
RUN apt-get update && \
	apt reinstall fonts-dejavu fonts-dejavu-core fonts-liberation -y

# Create a directory for fonts
RUN mkdir -p /usr/share/fonts/truetype/

# Copy fonts to the system directory
RUN cp -r /usr/src/app/Fonts /usr/share/fonts/truetype/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["python", "-u", "./bot.py"]
