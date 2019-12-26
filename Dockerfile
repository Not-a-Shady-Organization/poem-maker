# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.7-slim

# Get source files & API key
COPY poem_maker.py requirements.txt auth-key-file.json app.py ./
COPY not-shady-utils /usr/local/not-shady-utils
#COPY craigslist-scraper /usr/local/craigslist-scraper
COPY ["fonts/Brush Script.ttf", "/usr/share/fonts/Brush Script.ttf"]

# Note credential location for use of Google/YouTube APIs
ENV GOOGLE_APPLICATION_CREDENTIALS=./auth-key-file.json

# Note where to find utils functions
ENV PYTHONPATH=$PYTHONPATH:usr/local/not-shady-utils
ENV PYTHONPATH=$PYTHONPATH:usr/local/craigslist-scraper

# Note that we're in the docker container (so we access font as 'Brush-Script-MT-Italic' for some reason :\)
ENV in_docker=True

# Install Python dependencies
RUN pip3 install -r requirements.txt
RUN pip3 install gunicorn

# Install other dependencies
RUN apt-get update && apt-get install -y \
  ffmpeg \
  imagemagick

# Define the entrypoint (we only want this container for this program anyways)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
