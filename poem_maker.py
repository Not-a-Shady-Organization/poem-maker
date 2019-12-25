
'''
-- TODO --
Add images to blank sections
Try interpolation for None interval entities
Toss poems which contain few entities
Toss poems which contain long held entities

Add ability to insert image manually
Make voice options pass into TTS
Make bucket searchable by topics

Improve logging

Add pauses
'''


# Setup for logging
import logging
from contextlib import redirect_stdout

from subprocess import check_output
import io
import argparse
import os
from shutil import copyfile

from utils import BadOptionsError, makedir, clean_word, download_image_from_url, LogDecorator, text_to_image
from google_utils import find_entities, synthesize_text, transcribe_audio, interval_of, download_image, list_blobs, upload_file_to_bucket
from ffmpeg_utils import create_slideshow, add_audio_to_video, change_audio_speed, media_to_mono_flac, resize_image, fade_in_fade_out, concat_videos, resize_video, get_media_length

from Scraper import Scraper
from mutagen.mp3 import MP3


POSTS_DIRECTORY = './posts'

class NoAdError(Exception):
    pass

class DomainError(Exception):
    pass

class NoEntitiesInTTS(Exception):
    pass


def next_log_file(log_directory):
    files = os.listdir(log_directory)
    if files:
        greatest_num = max([int(filename.replace('log-', '').replace('.txt', '')) for filename in files])
        return f'log-{greatest_num+1}.txt'
    return 'log-0.txt'


def get_filenames(post_subdirectory):
    return {
        'image_dir': f'{post_subdirectory}/image',
        'frame_dir': f'{post_subdirectory}/image/frame',
        'relative_frame_dir': '../image/frame',

        'post.txt': f'{post_subdirectory}/text/post.txt',
        'entities.txt': f'{post_subdirectory}/text/entities.txt',

        'tts-title.mp3': f'{post_subdirectory}/audio/tts-title.mp3',
        'tts-title-rate-RATE.mp3': f'{post_subdirectory}/audio/tts-title-rate-RATE.mp3',
        'tts-title-rate-RATE.flac': f'{post_subdirectory}/audio/tts-title-rate-RATE.mp3',

        'tts-body.mp3': f'{post_subdirectory}/audio/tts-body.mp3',
        'tts-body-rate-RATE.mp3': f'{post_subdirectory}/audio/tts-body-rate-RATE.mp3',
        'tts-body-rate-RATE.flac': f'{post_subdirectory}/audio/tts-body-rate-RATE.flac',

        'body-slideshow.mp4': f'{post_subdirectory}/video/body-slideshow.mp4',
        'body-slideshow-with-audio.mp4': f'{post_subdirectory}/video/body-slideshow-with-audio.mp4',
        'body-slideshow-with-audio-and-fades.mp4': f'{post_subdirectory}/video/body-slideshow-with-audio-and-fades.mp4',
        'body-slideshow-with-audio-and-fades-1920x1080.mp4': f'{post_subdirectory}/video/body-slideshow-with-audio-and-fades-1920x1080.mp4',
        'body-concat.txt': f'{post_subdirectory}/video/body-concat.txt',

        'title-frame.jpg': f'{post_subdirectory}/image/frame/title-frame.jpg',
        'title-frame-full.jpg': f'{post_subdirectory}/image/frame/title-frame-full.jpg',
        'relative title-frame-full.jpg': f'../image/frame/title-frame-full.jpg',

        'title-slideshow.mp4': f'{post_subdirectory}/video/title-slideshow.mp4',
        'title-slideshow-with-audio.mp4': f'{post_subdirectory}/video/title-slideshow-with-audio.mp4',
        'title-slideshow-with-audio-and-fades.mp4': f'{post_subdirectory}/video/title-slideshow-with-audio-and-fades.mp4',
        'title-slideshow-with-audio-and-fades-1920x1080.mp4': f'{post_subdirectory}/video/title-slideshow-with-audio-and-fades-1920x1080.mp4',
        'title-concat.txt': f'{post_subdirectory}/video/title-concat.txt',

        'poem-concat.txt': f'{post_subdirectory}/video/poem-concat.txt',
        'poem.mp4': f'{post_subdirectory}/video/poem.mp4'
    }
    pass



def create_file_structure(post_subdirectory):
    makedir(post_subdirectory)
    makedir(f'{post_subdirectory}/audio')
    makedir(f'{post_subdirectory}/image')
    makedir(f'{post_subdirectory}/text')
    makedir(f'{post_subdirectory}/video')
    makedir(f'{post_subdirectory}/image/frame')




def create_poetry(title, body):
    ffmpeg_config = {'loglevel': 'panic', 'safe': 0, 'hide_banner': None, 'y': None}

    print(f'Creating poem on... \n\tTitle:{title}\n\tBody:{body}')

    # Make directories to store files for post
    clean_title = clean_word(title)
    post_subdirectory = f'{POSTS_DIRECTORY}/{clean_title}'

    # Create directories and filenames
    create_file_structure(post_subdirectory)
    file_map = get_filenames(post_subdirectory)

    print('File structure created')

    # Write the post's full text to file
    with open(file_map['post.txt'], 'w') as f:
        f.write(title + '\n')
        f.write(body)

    print('Source text saved to file')

    # Find entities in body and write to file for records
    entities = find_entities(body)
    with open(file_map['entities.txt'], 'w') as f:
        logging.info(f'Entities detected: {[e.name for e in entities]}')
        for entity in entities:
            f.write(str(entity))

    print(f'Entities detected in text via Google: {", ".join([e.name for e in entities])}')

    # TTS on both title and body
    synthesize_text(
        title,
        file_map['tts-title.mp3'],
        name='en-IN-Wavenet-B',
        pitch=-1,
        speaking_rate=0.8,
    )

    synthesize_text(
        body,
        file_map['tts-body.mp3'],
        name='en-IN-Wavenet-B',
        pitch=-1,
        speaking_rate=0.8,
    )

    print('Text-to-speech audio created')

    # Slow the TTS voice further
    title_rate = 0.9
    change_audio_speed(
        file_map['tts-title.mp3'],
        title_rate,
        file_map['tts-title-rate-RATE.mp3'].replace('RATE', str(title_rate)),
        **ffmpeg_config
    )

    body_rate = 0.9
    change_audio_speed(
        file_map['tts-body.mp3'],
        body_rate,
        file_map['tts-body-rate-RATE.mp3'].replace('RATE', str(body_rate)),
        **ffmpeg_config
    )

    print(f'TTS audio speed altered')

    # Find audio length
    title_audio = MP3(file_map['tts-title-rate-RATE.mp3'].replace('RATE', str(title_rate)))
    title_audio_length = title_audio.info.length
    body_audio = MP3(file_map['tts-body-rate-RATE.mp3'].replace('RATE', str(body_rate)))
    body_audio_length = body_audio.info.length

    # Transcribe the audio to learn when words are said
    media_to_mono_flac(
        file_map['tts-body-rate-RATE.mp3'].replace('RATE', str(body_rate)),
        file_map['tts-body-rate-RATE.flac'].replace('RATE', str(body_rate)),
        **ffmpeg_config
    )
    transcription = transcribe_audio(file_map['tts-body-rate-RATE.flac'].replace('RATE', str(body_rate)))

    print('TTS transcribed via Google')

    # TODO: Probably don't toss out words we can detect in speech.. Make estimates
    entity_intervals = dict()
    for entity in entities:
        interval = interval_of(entity.name, transcription)
        if interval != None:
            entity_intervals[entity.name] = interval_of(entity.name, transcription)

    print('Spoken time of entities found')

    entity_information = dict()

    # Call to redirect_stdout catches output in variable f (Don't want it, I just don't like the output)
    f = io.StringIO()
    with redirect_stdout(f):
        for word, interval in entity_intervals.items():
            image_filepath = download_image(clean_word(word), file_map['image_dir'], f'{clean_word(word)}')

            entity_information[word] = {
                'image_filepath': f'{image_filepath}',
                'interval': interval
            }

    print('Images downloaded for transcribed entities')

    # Copy to frames directory to record selections for video
    for word, info in entity_information.items():
        resize_image(f'{file_map["image_dir"]}/{info["image_filepath"]}', 1920, 1080, f'{file_map["frame_dir"]}/{clean_word(word)}.jpg')

    print('Images resized and copied to frames directory')

    # Sort entities by occurance in the source text
    def find_word(word, text):
        try:
            return body.index(' ' + word)
        except ValueError:
            return body.index(word)
    entity_information_list = sorted(list(entity_information.items()), key=lambda x: find_word(x[0], body))

    # Find intervals for images in slideshow
    image_intervals = []
    for i, (name, info) in enumerate(entity_information_list):
        if i == 0:
            start = 0
        else:
            start = entity_information_list[i][1]['interval'][0]

        if i != len(entity_information)-1:
            end = entity_information_list[i+1][1]['interval'][0]
        else:
            end = body_audio_length
        image_intervals += [(name, start, end)]

    if image_intervals == []:
        raise NoEntitiesInTTS('No entities were successfully found in the TTS audio.')

    image_information = []
    for (word, start, end) in image_intervals:
        image_information.append((word, start, end, f"{file_map['relative_frame_dir']}/{clean_word(word)}.jpg"))

    # Create slideshow
    write_concat_file(file_map['body-concat.txt'], image_information)
    create_slideshow(file_map['body-concat.txt'], file_map['body-slideshow.mp4'])

    print('Slideshow of frames created')

    # Add audio to slideshow
    add_audio_to_video(
        file_map['tts-body-rate-RATE.mp3'].replace('RATE', str(body_rate)),
        file_map['body-slideshow.mp4'],
        file_map['body-slideshow-with-audio.mp4'],
        **ffmpeg_config
    )

    print('Altered TTS audio added to body slideshow')

    # Text to image the title & resize
    def clean_title(t):
        return t.replace('"','').replace("'",'').replace('/','-')

    if 'in_docker' in os.environ and os.environ['in_docker'] == 'True':
        text_to_image(clean_title(title), file_map['title-frame.jpg'], font='Brush-Script-MT-Italic')
    else:
        text_to_image(clean_title(title), file_map['title-frame.jpg'])

    resize_image(file_map['title-frame.jpg'], 1920, 1080, file_map['title-frame-full.jpg'])

    print('Title card created & resized')

    # Create title card slideshow
    title_information = [('title', 0, title_audio_length + 1, file_map['relative title-frame-full.jpg'])]
    write_concat_file(file_map['title-concat.txt'], title_information)
    create_slideshow(file_map['title-concat.txt'], file_map['title-slideshow.mp4'], )

    print('Title card slideshow created')

    add_audio_to_video(
        file_map['tts-title-rate-RATE.mp3'].replace('RATE', str(title_rate)),
        file_map['title-slideshow.mp4'],
        file_map['title-slideshow-with-audio.mp4'],
        **ffmpeg_config
    )

    print('Altered TTS audio added to title slideshow')

    fade_length = 0.4
    fade_in_fade_out(file_map['title-slideshow-with-audio.mp4'], fade_length, fade_length, file_map['title-slideshow-with-audio-and-fades.mp4'], **ffmpeg_config)
    fade_in_fade_out(file_map['body-slideshow-with-audio.mp4'], fade_length, fade_length, file_map['body-slideshow-with-audio-and-fades.mp4'], **ffmpeg_config)

    # TODO: Solve why this fade command breaks the Docker container for some videos...
    # Maybe TO ?
#    copyfile(file_map['title-slideshow-with-audio.mp4'], file_map['title-slideshow-with-audio-and-fades.mp4'])
#    copyfile(file_map['body-slideshow-with-audio.mp4'], file_map['body-slideshow-with-audio-and-fades.mp4'])


    print('Fade in and out added to body and title videos')
    resize_video(file_map['title-slideshow-with-audio-and-fades.mp4'], file_map['title-slideshow-with-audio-and-fades-1920x1080.mp4'], **ffmpeg_config)
    resize_video(file_map['body-slideshow-with-audio-and-fades.mp4'], file_map['body-slideshow-with-audio-and-fades-1920x1080.mp4'], **ffmpeg_config)

    concat_videos([
            file_map['title-slideshow-with-audio-and-fades-1920x1080.mp4'],
            file_map['body-slideshow-with-audio-and-fades-1920x1080.mp4']
        ],
        file_map['poem.mp4'],
        **ffmpeg_config
    )

    print('Videos concatenated')
    print('Poem complete!')
    return file_map['poem.mp4']



@LogDecorator()
def write_concat_file(concat_filepath, image_information):
    with open(concat_filepath, 'w') as f:
        f.write('ffconcat version 1.0\n')
        for (word, start, end, filepath) in image_information:
            f.write(f'file {filepath}\n')
            f.write(f'duration {end - start}\n')

        # BUG: This is the source of some miss timing on images & corruption for YouTube
        # Audio gets misaligned because this file is longer in video than expected
        # Concating seems to advance audio if the track is null Need to set the track to not null
        f.write(f'file {filepath}\n')


@LogDecorator()
def checkout_craigslist_ad(bucket_path=None, bucket_dir=None, min_word_count=None):
    # Retreive and filter blobs
    blobs = list_blobs('craig-the-poet')

    to_checkout = None
    if bucket_dir:
        blobs = [blob for blob in blobs if bucket_dir in blob.name]
        for blob in blobs:
            # Check if compliant with filters
            if 'ledger.txt' in blob.name:
                continue

            unused = (blob.metadata['used'] == 'false') and (blob.metadata['in-use'] == 'false')
            not_a_loser = blob.metadata['failed'] == 'false'
            long_enough = (not min_word_count) or (int(blob.metadata['ad-body-word-count']) > min_word_count)

            if unused and long_enough and not_a_loser:
                to_checkout = blob
    else:
        blobs = [blob for blob in blobs if bucket_path in blob.name]
        for blob in blobs:
            if blob.name == bucket_path:
                to_checkout = blob

    if not to_checkout:
        return

    text = to_checkout.download_as_string().decode("utf-8")
    splitted = text.split('\n')

    print(f'Checking out {to_checkout.name}')

    # Check it out and update the metadata
    to_checkout.metadata = {'in-use': 'true'}
    to_checkout.patch()

    return {
        'blob': to_checkout,
        'title': splitted[0],
        'body': '\n'.join(splitted[1:]),
    }





def poem_maker(bucket_path=None, source_bucket_dir=None, url=None, local_file=None, destination_bucket_dir=None, preserve=None, min_word_count=None, **kwargs):
    #################
    # VALIDATE MODE #
    #################

    # Validate that we have some source text
    if not bucket_path and not source_bucket_dir and not url and not local_file:
        raise BadOptionsError('Please specify one of --bucket-path, --source-bucket-dir, --url, or --local-file')

    # Check if two input paths exist
    empty_count = sum(1 for i in [bucket_path, source_bucket_dir, url, local_file] if i == None)
    if empty_count < 3:
        raise BadOptionsError('Multiple text sources were specified. Please specify one of --bucket-path, --url, --local-file, or --source-bucket-dir')

    if (bucket_path and not destination_bucket_dir) or (url and not destination_bucket_dir) or (local_file and not destination_bucket_dir):
        raise BadOptionsError('When not pulling from a --source-bucket-dir, must specify a --destination-bucket-dir')

    # Note which options are unused
    if (url or local_file) and min_word_count:
        print('As a particular source text was specified, --min-word-count flag is ignored')

    if (url or local_file) and preserve:
        print('As we do not interact with a bucket blob in this mode, --preserve flag is ignored')


    # TODO Make this work
    # Construct params for Google TTS
#    tts_params = {
#        'name': voice,
#        'speaking_rate': speaking_rate,
#        'pitch': pitch,
#    }

    # Setup for logging
    makedir(f'logs')
    log_filename = next_log_file(f'logs')
    LOG_FILEPATH = f'logs/{log_filename}'
    logging.basicConfig(filename=LOG_FILEPATH, level=logging.DEBUG)
    import LogDecorator


    poem_filepath = ''

    # Get a subject ad
    if source_bucket_dir:
        logging.info(f'Starting program on bucket directory {source_bucket_dir}')
        obj = checkout_craigslist_ad(bucket_dir=source_bucket_dir, min_word_count=min_word_count)

    elif bucket_path:
        obj = checkout_craigslist_ad(bucket_path=bucket_path)

    elif url:
        logging.info(f'Starting program on specified URL: {url}')
        s = Scraper()
        obj = s.scrape_craigslist_ad(url)

    elif local_file:
        logging.info(f'Starting program on specified ad: {local_file}')

        try:
            obj = {}
            with open(local_file, 'r') as f:
                lines = f.readlines()
                obj['title'] = lines[0]
                obj['body'] = '\n'.join(lines[1:])
        except:
            raise NoAdError(f'Failed to read local file {local_file} as ad')

    # Check that we got an ad successfully
    if not obj:
        raise NoAdError(f'Failed to retreive ad')

    # Make a poem from the ad
    try:
        poem_filepath = create_poetry(obj['title'], obj['body'])
        blob = obj['blob']
        blob.metadata = {'in-use': 'false'}
        blob.patch()
    except:
        logging.error(f'Could not complete poem generation on ad {obj["title"]}')
        blob = obj['blob']
        blob.metadata = {'in-use': 'false', 'failed': 'true'}
        blob.patch()

    # If we got the ad from a bucket, handle metadata
    metadata = {
        'ad-url': '',
        'ad-title': '',
        'ad-posted-time': '',
        'ad-body-word-count': '',
        'runtime': '',
    }

    if source_bucket_dir or bucket_path:
        blob = obj['blob']

        # TODO Grab all needed elemetns and pass on
        # Note the posted url, title, posted time, and body word count
        metadata['ad-url'] = blob.metadata['ad-url']
        metadata['ad-title'] = blob.metadata['ad-title']
        metadata['ad-posted-time'] = blob.metadata['ad-posted-time']
        metadata['ad-body-word-count'] = blob.metadata['ad-body-word-count']

        # Mark as used if applicable
        if not preserve:
            blob.metadata = {'used': 'true'}
            blob.patch()

    if url:
        metadata['ad-url'] = url
        metadata['ad-title'] = obj['title']
        metadata['ad-posted-time'] = obj['ad-posted-time']
        metadata['ad-body-word-count'] = len(obj['body'].split(' '))

    if local_file:
        metadata['ad-title'] = obj['title']
        metadata['ad-body-word-count'] = len(obj['body'].split(' '))

    runtime = get_media_length(poem_filepath)
    metadata['runtime'] = runtime

    # Upload poem to destination bucket dir
    if not destination_bucket_dir:
        destination_bucket_dir = source_bucket_dir

    dest_path = f'poems/{destination_bucket_dir}/{clean_word(obj["title"])}.mp4'
    upload_file_to_bucket('craig-the-poet', poem_filepath, dest_path, metadata=metadata)
    logging.info(f'Uploaded to bucket at {dest_path}')




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket-path')
    parser.add_argument('--source-bucket-dir')
    parser.add_argument('--url')
    parser.add_argument('--local-file')
    parser.add_argument('--destination-bucket-dir')

    parser.add_argument('--preserve', help="Don't delete ad from bucket after poem generates", action='store_true')
    parser.add_argument('--min-word-count', type=int, help="Minimum word count allowed for selected ad")


    parser.add_argument('--voice', default='en-IN-Wavenet-C', help="TTS voice option")
    parser.add_argument('--speaking_rate', type=float, default=.85, help="TTS speaking rate")
    parser.add_argument('--pitch', type=float, default=-1., help="TTS pitch")

    parser.add_argument('--title-speed-factor', type=float, default=.85, help="Speed multiplier for title audio")
    parser.add_argument('--body-speed-factor', type=float, default=.9, help="Speed multiplier for body audio")

    args = parser.parse_args()

    poem_maker(**vars(args))
