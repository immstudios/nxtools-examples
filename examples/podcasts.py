#!/usr/bin/env python3

"""

podcast.py is a very simple podcast downloader which can used with cron.
It takes only one positional argument (path to a json configuration file)

Structure of this file follows:

{
    "save_dir" : "~/Music/Podcasts",
    "feeds" : [
        {
        "title" : "Demuxed",
        "url" : "https://www.heavybit.com/category/library/podcasts/demuxed/feed/"
        },
        {
        "title" : "Marvin suicide",
        "url" : "http://feeds.feedburner.com/marvinsuicidefeedburner?format=xml"
        }
    ]
}

Podcasts are downloaded and converted using ffmpeg to specified "save_dir" as

{podcast_name}/{episode name}.mp3

all names are slugified. eg. specials characters are stripped,
spaces replaced with dashes etc...

Script also sets MP3 metadata (see the code)

"""

import os
import sys
import json
import requests

from nxtools import *
from nxtools.media import *

config = {}


if len(sys.argv) == 2:
    config_path = sys.argv[-1]
else:
    config_path = os.path.abspath(os.path.expanduser("~/.private/special/podcasts.json"))

if not os.path.exists(config_path):
    critical_error("Config path does not exist")

try:
    config = json.load(open(config_path))
except Exception:
    log_traceback()
    critical_error("Unable to open config file")


def get_feed(**kwargs):
    title = kwargs.get("title")
    url = kwargs.get("url")
    if not (url and title):
        logging.error("Title and url must be specified in feed config")
        return False

    try:
        feed_data = requests.get(url)
        feed = xml(feed_data.text)
        channel = feed.find("channel")
    except Exception:
        return

    for item in channel.findall("item"):
        try:
            ititle = item.find("title").text
            iurl = item.find("enclosure").attrib["url"]
        except Exception:
            continue

        tpath = FileObject(
                    os.path.expanduser(config["save_dir"]),
                    slugify(title),
                    slugify(ititle) + ".mp3"
                )
        if tpath.exists:
            continue

        if not os.path.isdir(tpath.dir_name):
            os.makedirs(tpath.dir_name)

        res = ffmpeg( "-y",
                "-i", iurl,
                "-vn", "-c:a", "libmp3lame", "-b:a", "128k",
                "-map_metadata", "-1",
                "-metadata", "title={}".format(ititle),
                "-metadata", "album={}".format(title),
                "-metadata", "artist=_Podcasts_",
                tpath
            )

        if not res:
            if tpath.exists:
                os.remove(tpath.path)


if __name__ == "__main__":
    for feedconfig in config.get("feeds", []):
        get_feed(**feedconfig)

    if os.path.exists("/usr/bin/mpc"):
        os.system("mpc update")
