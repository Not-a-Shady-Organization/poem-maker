FROM python:3

# Get source files & API key
COPY poem-maker.py requirements.txt auth-key-file.json ./
COPY not-shady-utils /usr/local/not-shady-utils
COPY ["fonts/Brush Script.ttf", "/usr/share/fonts/Brush Script.ttf"]

# Note credential location for use of Google/YouTube APIs
ENV GOOGLE_APPLICATION_CREDENTIALS=./auth-key-file.json

# Note where to find utils functions
ENV PYTHONPATH=$PYTHONPATH:usr/local/not-shady-utils

# Note that we're in the docker container (so we access font as 'Brush-Script-MT-Italic' for some reason :\)
ENV in_docker=True

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Install other dependencies
RUN apt-get update && apt-get install -y \
  ffmpeg \
  imagemagick

# Define the entrypoint (we only want this container for this program anyways)
ENTRYPOINT ["python", "poem-maker.py"]
