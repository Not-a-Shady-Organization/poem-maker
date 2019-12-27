# Poem Maker

## Local
### Setup
The poem maker uses `not-shady-utils` and `craigslist-scraper`, thus we need a local copy of these repos. We point to these instances in our `PYTHONPATH` as...

```bash
export PYTHONPATH=$PYTHONPATH:path/to/not-shady-utils
export PYTHONPATH=$PYTHONPATH:path/to/craigslist-scraper
```

To allow access to our GCP resources we use...

```bash
export GOOGLE_APPLICATION_CREDENTIALS=path/to/auth-key-file.json
```

To install Python dependencies...

```bash
pip install -r requirements.txt
```

We must install [FFMPEG](https://www.ffmpeg.org/download.html) and [ImageMagick](https://imagemagick.org/script/download.php) (system dependent), and finally (and most weirdly) we must have Brush Script I font. Just.. oy.

### Run
The poem maker can make a poem only being given a `BUCKET_DIR` as

```bash
python poem-maker.py --bucket-dir [BUCKET_DIR]
```

with optional `--min-word-count` option to filter for longer ads. We also can scrape & make a poem from a particular ad with  `URL` as...

```bash
python poem_maker.py --url [URL]
```

Also we can use a local file as the source text where the first line is the title and all other lines are the body. This is called as...

```bash
python poem_maker.py --local-file path/to/local-file.txt
```


## Dockerized
*There's probably a way around these steps, but for now this will work.*

### Setup
- Copy auth-file-key.json for the GCP project to this directory

- Ensure Brush Script I lives in a place ImageMagick can find it -- check using `convert -list fonts`

- Clone the needed repos into this repo at `./not-shady-utils` and `./craigslist-scraper`

```bash
git clone https://github.com/Not-a-Shady-Organization/not-shady-utils.git
git clone https://github.com/Not-a-Shady-Organization/craigslist-scraper.git
```

*Probably better to create a utils volume and mount it to all containers that need it.*

### Build
To build the container image locally, use...

```bash
docker image build -t poem-maker:1.0 .
```

TODO: We should create a dockerhub instance for these and pull from that

### Run
By calling the built container and passing it a command, we can use the scraping script. *Note* -- these commands will return before the process is complete. Use `docker ps` to see if the container is still running.

#### Examples
```bash
docker run --env PORT=8080 -dt poem-maker:1.0
```


#### Push to Cloud Run
To push our image to GCP's Cloud Run for event based runs, we build as above, then...

```bash
docker tag poem-maker:[TAG] us.gcr.io/ccblender/poem-maker:[TAG]
docker push us.gcr.io/ccblender/poem-maker:[TAG]
```

Then, hop onto Cloud Run on the GCP Console. Select the `poem-maker` service and select `Deploy New Revision`. We should see our newly uploaded container in the list. Revise and wait for it to go live. Hitting the given endpoint with a browser will return a "We are live :)" message when the container is ready for requests.

#### List of text-to-speech voices
https://cloud.google.com/text-to-speech/docs/voices
##### Creepy Voices
en-GB-Wavenet-C
en-US-Wavenet-A

