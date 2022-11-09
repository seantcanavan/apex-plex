import os
import re
import sys
import subprocess
import json

def print_to_stderr(*a):
    print(*a, file = sys.stderr)

# change this for other languages (3 character code)
LANG = ["eng","nor"]

# set this to the path for mkvmerge
MKVMERGE = "/usr/bin/mkvmerge"

AUDIO_RE = re.compile(
    r"Track ID (\d+): audio \([A-Z0-9_/]+\) [number:\d+ uid:\d+ codec_id:[A-Z0-9_/]+ codec_private_length:\d+ language:([a-z]{3})")
SUBTITLE_RE = re.compile(
    r"Track ID (\d+): subtitles \([A-Z0-9_/]+\) [number:\d+ uid:\d+ codec_id:[A-Z0-9_/]+ codec_private_length:\d+ language:([a-z]{3})(?: track_name:\w*)? default_track:[01]{1} forced_track:([01]{1})")

if len(sys.argv) < 2:
    print("Please supply an input directory")
    sys.exit()

in_dir = sys.argv[1]

for root, dirs, files in os.walk(in_dir):
    for f in files:

        # filter out non mkv files
        if not f.endswith(".mkv"):
            continue

        # path to file
        path = os.path.join(root, f)

        # build command line
        cmd = [MKVMERGE, "-J", path]

        # get mkv info
        mkvmerge = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = mkvmerge.communicate()
        if mkvmerge.returncode != 0:
            print_to_stderr("mkvmerge failed to identify "+ path)
            continue

        # find audio and subtitle tracks
        audio = []
        subtitle = []
        info_json = json.loads(stdout)
        tracks = info_json['tracks']
        for track in tracks:
            track['properties']['id'] = track['id']
            if track['type'] == 'audio':
                audio.append(track)
            elif track['type'] == 'subtitles':
                subtitle.append(track)

        # filter out files that don't need processing
        if len(audio) < 2 and len(subtitle) < 2:
            print_to_stderr("nothing to do for " + path)
            continue

        # filter out tracks that don't match the language
        audio_lang = list(filter(lambda a: a['properties']['language'] in LANG, audio))
        subtitle_lang = list(filter(lambda a: a['properties']['language'] in LANG, subtitle))

        # filter out files that don't need processing
        if audio_lang == audio and subtitle_lang == subtitle:
            print_to_stderr("nothing to do for " + path)
            continue

        # filter out files that don't need processing
        if len(audio_lang) == 0 and len(subtitle_lang) == 0:
            print_to_stderr("no tracks with that language in " + path)
            continue

        # build command line
        cmd = [MKVMERGE, "-o", path + ".temp"]
        if len(audio_lang):
            cmd += ["--audio-tracks", ",".join([str(a['id']) for a in audio_lang])]
            for i in range(len(audio_lang)):
                cmd += ["--default-track", ":".join([str(audio_lang[i]['id']), "0" if i else "1"])]
        if len(subtitle_lang):
            cmd += ["--subtitle-tracks", ",".join([str(s['id']) for s in subtitle_lang])]
            for i in range(len(subtitle_lang)):
                cmd += ["--default-track", ":".join([str(subtitle_lang[i]['id']), "0"])]
        cmd += [path]

        # process file
        print_to_stderr("Processing " + path + "...")
        mkvmerge = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = mkvmerge.communicate()
        if mkvmerge.returncode != 0:
            print_to_stderr("Failed")
            print(stdout)
            continue

        print_to_stderr("Succeeded")

        # overwrite file
        os.remove(path)  # Don't overwrite
        os.rename(path + ".temp", path)
