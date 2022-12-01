import os
import sys
import subprocess
import json
from pprint import pprint


def print_to_stderr(*a):
    print(*a, file=sys.stderr)


# change this for other languages (3 character code)
AUDIO_LANG = ["eng", "jpn"]
SUBTITLE_LANG = ["eng"]

# set this to the path for mkvmerge
MKVMERGE = "/usr/bin/mkvmerge"


def map_audio_tracks(flat_audio_tracks):
    track_map = {}
    for current_track in flat_audio_tracks:
        track_lang = current_track['properties']['language']
        track_channels = current_track['properties']['audio_channels']
        if track_lang not in track_map:
            track_map[track_lang] = {}
        if track_channels not in track_map[track_lang]:
            track_map[track_lang][track_channels] = []
        track_map[track_lang][track_channels].append(current_track)
    return track_map


def prefer_ac3(some_tracks):
    for some_track in some_tracks:
        if some_track['codec'] == 'AC-3':
            return [some_track]
    return some_tracks


def filter_audio_tracks(track_map):
    winning_tracks = []
    for current_lang in ['eng', 'jpn']:
        if 6 not in track_map[current_lang] and 8 not in track_map[current_lang] and 2 in track_map[current_lang]:
            winning_tracks.append(prefer_ac3(track_map[current_lang][2]))
        elif 2 not in track_map[current_lang] and 8 not in track_map[current_lang] and 6 in track_map[current_lang]:
            winning_tracks.append(prefer_ac3(track_map[current_lang][6]))
        elif 2 not in track_map[current_lang] and 6 not in track_map[current_lang] and 8 in track_map[current_lang]:
            winning_tracks.append(prefer_ac3(track_map[current_lang][8]))
        elif 6 in track_map[current_lang]:
            winning_tracks.append(prefer_ac3(track_map[current_lang][6]))
        elif 2 in track_map[current_lang]:
            winning_tracks.append(prefer_ac3(track_map[current_lang][2]))
        else:
            winning_tracks.append(prefer_ac3(track_map[current_lang][8]))
    return winning_tracks


def map_subtitle_tracks(flat_subtitle_tracks):
    track_map = {}
    for current_track in flat_subtitle_tracks:
        track_lang = current_track['properties']['language']
        track_codec = current_track['codec']
        if track_lang not in track_map:
            track_map[track_lang] = {}
        if track_codec not in track_map[track_lang]:
            track_map[track_lang][track_codec] = []
        track_map[track_lang][track_codec].append(current_track)
    return track_map


def filter_subtitle_tracks(flat_subtitle_tracks):
    winning_tracks = []
    for current_lang in ['eng']:



if len(sys.argv) < 2:
    print("Please supply an input directory")
    sys.exit()

in_dir = sys.argv[1]

for root, dirs, files in os.walk(in_dir):
    for f in files:

        # filter out non mkv files
        if not f.endswith(".mkv"):
            continue

        print("working on file " + str(f))

        # path to file
        path = os.path.join(root, f)

        # build command line
        cmd = [MKVMERGE, "-J", path]

        # get mkv info
        mkv_merge = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = mkv_merge.communicate()
        if mkv_merge.returncode != 0:
            print_to_stderr("mkvmerge failed to identify " + path)
            continue

        # find audio and subtitle tracks
        all_audio_tracks = []
        all_subtitle_tracks = []
        info_json = json.loads(stdout)
        tracks = info_json['tracks']
        for track in tracks:
            track['properties']['id'] = track['id']
            if track['type'] == 'audio':
                all_audio_tracks.append(track)
            elif track['type'] == 'subtitles':
                all_subtitle_tracks.append(track)

        mapped_audio_tracks = map_audio_tracks(all_audio_tracks)
        mapped_subtitle_tracks = map_subtitle_tracks(all_subtitle_tracks)

        pprint(mapped_audio_tracks)
        pprint(mapped_subtitle_tracks)

        filtered_audio = filter_audio_tracks(mapped_audio_tracks)
        filtered_subtitle_tracks = filter_subtitle_tracks(mapped_subtitle_tracks)

        pprint(filtered_audio)
        pprint(filtered_subtitle_tracks)

        # if len(filtered_audio) == len(all_audio_tracks) and len(filtered_subtitle_tracks) == len(all_subtitle_tracks):
        #     print_to_stderr("mapped and filtered and have the same amount of tracks " + path)
        #     continue

        # filter out tracks that don't match the language
        audio_lang = list(filter(lambda a: a['properties']['language'] in AUDIO_LANG, all_audio_tracks))
        subtitle_lang = list(filter(lambda a: a['properties']['language'] in SUBTITLE_LANG, all_subtitle_tracks))

        # filter out files that don't need processing
        # if audio_lang == audio and subtitle_lang == subtitle:
        #     print_to_stderr("nothing to do for " + path)
        #     continue

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
        cmd += ["--no-chapters", "--no-attachments"]
        cmd += [path]
        print("cmd is " + str(cmd))

        # process file
        print_to_stderr("Processing " + path + "...")
        mkv_merge = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = mkv_merge.communicate()
        if mkv_merge.returncode != 0:
            print_to_stderr("Failed")
            print(stdout)
            continue

        print_to_stderr("Succeeded")

        # overwrite file
        os.remove(path)  # Don't overwrite
        os.rename(path + ".temp", path)
