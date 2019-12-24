# Poem Maker

## Local
### Setup
The poem maker uses `not-shady-utils`, thus we need a local copy of the utils repo. We point to that instance in our `PYTHONPATH` as...

`git clone https://github.com/Not-a-Shady-Organization/not-shady-utils.git`

`git clone https://github.com/Not-a-Shady-Organization/craigslist-scraper.git`

`export PYTHONPATH=$PYTHONPATH:path/to/not-shady-utils`

`export PYTHONPATH=$PYTHONPATH:path/to/craigslist-scraper`

To allow access to our GCP resources we use...

`export GOOGLE_APPLICATION_CREDENTIALS=path/to/auth-key-file.json`

To install Python dependencies...

`pip install -r requirements.txt`

We must install FFMPEG and ImageMagick (system dependent), and finally (and most weirdly) we must have Brush Script I font.

### Run
The poem maker can make a poem only being given a `BUCKET_DIR` as

`python poem-maker.py --bucket-dir [BUCKET_DIR]`

with optional `--min-word-count` option to filter for longer ads. We also can scrape a particular ad at `URL` as...

`python poem_maker.py --url [URL]`

Also we can use a local file as the source text where the first line is the title and all other lines are the body. This is called as...

`python poem_maker.py --local-file path/to/local-file.txt`


## Dockerized
*There's probably a way around these steps, but for now this will work.*

### Setup
- Copy auth-file-key.json for the GCP project to this directory

- Ensure Brush Script I lives in a place ImageMagick can find it -- check using `convert -list fonts`

- Clone the utils repo into this repo at `./not-shady-utils`

`git clone https://github.com/Not-a-Shady-Organization/not-shady-utils.git`

*Probably better to create a utils volume and mount it to all containers that need it.*

### Build
To build the container image locally, use...

`docker image build -t poem-maker:1.0 .`

TODO: We should create a dockerhub instance for these and pull from that

### Run
By calling the built container and passing it a command, we can use the scraping script. *Note* -- these commands will return before the process is complete. Use `docker ps` to see if the container is still running.

#### Examples
`docker run -dt poem-maker:1.0 --city portland --min-word-count 30`
