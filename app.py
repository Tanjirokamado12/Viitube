import os
import re
import time
import json
import random
import string
import threading
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse, urlencode, urljoin
import requests
import jwt              # pip install PyJWT
import isodate          # pip install isodate
import html
from dateutil import parser
import xml.dom.minidom
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape, escape
import os
import json
import re
from datetime import datetime, timedelta
from flask import Flask, Response, request
import requests
import xml.sax.saxutils as saxutils
import sys

from flask import (
    Flask, request, Response, send_file, send_from_directory,
    jsonify, redirect, session, url_for, abort
)
from pytubefix import YouTube
from pytube import Channel
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timezone

def clean_xml_text(text):
    if not text:
        return ''
    if not isinstance(text, str):
        text = str(text)

    # Remove control characters not allowed in XML 1.0
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    # Escape standard XML-sensitive characters
    text = xml_escape(text, {'"': "&quot;", "'": "&apos;"})

    return text


# === CONFIG ===
PLAYLIST_CACHE_DIR = Path("./assets/cache/playlist")
VIDEOMETA_PLAYLIST_CACHE_DIR = Path("./assets/cache/videoinfo")
CACHE_MAX_AGE = 48 * 60 * 60  # 48 hours
OAUTH2_DEVICE_CODE_URL = 'https://oauth2.googleapis.com/device/code'
OAUTH2_TOKEN_URL = 'https://oauth2.googleapis.com/token'
CLIENT_ID = '627431331381.apps.googleusercontent.com'
CLIENT_SECRET = 'O_HOjELPNFcHO_n_866hamcO'
DEVICE_CODE_URL = 'https://oauth2.googleapis.com/device/code'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
REDIRECT_URI = ''
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/channels"
SCOPE = 'https://www.googleapis.com/auth/youtube.readonly'
AUTHORIZATION_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
SCOPE = 'https://www.googleapis.com/auth/youtube.readonly'
CACHE_DIR = os.path.join(os.path.dirname(__file__), "assets", "cache", "search")
VIITUBE_SEARCH_DIR = "./assets/cache/search"
VIITUBE_VIDEO_CACHE_DIR = "./assets/cache/videoinfo"
YOUTUBE_SEARCH_DISLIKE_API = "https://returnyoutubedislikeapi.com/votes?videoId="
YOUTUBEI_SEARCH_QUERY_LINK = "https://www.youtube.com/youtubei/v1/search?key=YOUR_API_KEY"
YOUTUBEI_VIDEOMETA_URL = "https://www.youtube.com/youtubei/v1/player?key=YOUR_API_KEY"
VIDEOMETA_PLAYLIST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
PLAYLIST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
app = Flask(__name__)

@app.route('/deviceregistration/v1/devices', methods=['POST'])
def upload_hex():
    return jsonify({
    "id": "AP+lc78BjKeJW5h+DRL/JIQA7RWj1iq8KzTeYzOxDe9dV6OX/LraIwUX2JiV91A",
    "key": "AP+lc7+4QeLHuvmoYL4IiyU0GJDP1Ub8iWm786sTXD1z+g9MSOULGBkeXdCvYsbQpxc2gxd1shAzvqU29or/Osmh0NRUfliReepIKtJozUju+1Bmre1a+s/5Pj69F51DpbFi427qLrH6tQ"
}), 200

# === CONFIG ===
VIITUBE_PLAYLIST_CACHE_DIR = Path("./assets/cache/playlist")
VIDEO_VIITUBE_PLAYLIST_CACHE_DIR = Path("./assets/cache/videoinfo")
VIITUBE_PLAYLIST_CACHE_MAX_AGE = 48 * 60 * 60  # 48 hours

VIITUBE_PLAYLiST_CONTENT_YOUTUBEI_URL = "https://www.youtube.com/youtubei/v1"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
    "X-Youtube-Client-Name": "1",
    "X-Youtube-Client-Version": "2.20210721.00.00",
}


# === Utilities ===
def viitube_playlist_content_is_cache_valid(path):
    return path.exists() and (time.time() - path.stat().st_mtime < VIITUBE_PLAYLIST_CACHE_MAX_AGE)

def viitube_playlist_fetch_playlist_raw(playlist_id):
    raw = []
    continuation = None
    CONTEXT = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20210721.00.00",
            }
        },
        "browseId": f"VL{playlist_id}",
    }

    while True:
        url = f"{VIITUBE_PLAYLiST_CONTENT_YOUTUBEI_URL}/next" if continuation else f"{VIITUBE_PLAYLiST_CONTENT_YOUTUBEI_URL}/browse"
        body = {"context": CONTEXT["context"], "continuation": continuation} if continuation else CONTEXT
        resp = requests.post(url, headers=HEADERS, json=body).json()
        raw.append(resp)

        try:
            items = resp["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]["tabRenderer"] \
                    ["content"]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"] \
                    ["contents"][0]["playlistVideoListRenderer"]["contents"]
        except KeyError:
            try:
                items = resp["onResponseReceivedActions"][0]["appendContinuationItemsAction"]["continuationItems"]
            except KeyError:
                break

        continuation = None
        for it in items:
            if "continuationItemRenderer" in it:
                continuation = it["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"]
                break
        if not continuation:
            break
    return raw

def viitube_playlist_load_or_fetch_raw(playlist_id):
    CACHE_PATH = VIITUBE_PLAYLIST_CACHE_DIR / f"{playlist_id}.raw.json"
    if viitube_playlist_content_is_cache_valid(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    VIITUBE_PLAYLIST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    raw = viitube_playlist_fetch_playlist_raw(playlist_id)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2)
    return raw

# === FIXED viitube_playlist_extract_playlist_title ===
def viitube_playlist_extract_playlist_title(raw):
    # Try known possible paths for playlist title:
    try:
        # Default path in many responses
        return raw[0]["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]["tabRenderer"]["title"]
    except (IndexError, KeyError):
        pass
    
    try:
        # Sometimes title under header > pageHeaderRenderer
        return raw[0]["header"]["pageHeaderRenderer"]["title"]
    except (IndexError, KeyError):
        pass

    try:
        # Sometimes under pageTitle key in header
        return raw[0]["header"]["pageHeaderRenderer"]["pageTitle"]
    except (IndexError, KeyError):
        pass

    try:
        # Sometimes deeper fallback: metadata > playlistMetadataRenderer > title
        return raw[0]["metadata"]["playlistMetadataRenderer"]["title"]
    except (IndexError, KeyError):
        pass

    return "Unknown Playlist"

def viitube_playlist_extract_playlist_items(raw):
    items_all = []
    pos = 1
    for block in raw:
        try:
            items = block["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]["tabRenderer"] \
                     ["content"]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"] \
                     ["contents"][0]["playlistVideoListRenderer"]["contents"]
        except KeyError:
            items = block.get("onResponseReceivedActions", [{}])[0].get("appendContinuationItemsAction", {}).get("continuationItems", [])
        for it in items:
            pr = it.get("playlistVideoRenderer")
            if not pr:
                continue
            items_all.append({
                "position": pos,
                "videoId": pr.get("videoId"),
                "title": pr["title"]["runs"][0]["text"]
            })
            pos += 1
    return items_all

def viitube_playlist_fetch_video_details(video_id):
    video_cache_path = VIDEO_VIITUBE_PLAYLIST_CACHE_DIR / f"{video_id}.json"
    VIDEO_VIITUBE_PLAYLIST_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        if viitube_playlist_content_is_cache_valid(video_cache_path):
            # Load data from cache
            with open(video_cache_path, encoding="utf-8") as f:
                try:
                    resp = json.load(f)  # Try loading the JSON data
                except json.JSONDecodeError as e:
                    resp = None
                    # Handle further, such as re-fetching the data
        else:
            # Fetch data from API
            payload = {"context": {"client": {"clientName": "WEB", "clientVersion": "2.20210721.00.00"}}, "videoId": video_id}
            try:
                response = requests.post(f"{VIITUBE_PLAYLiST_CONTENT_YOUTUBEI_URL}/player", headers=HEADERS, json=payload)
                resp = response.json()  # Attempt to parse JSON response
            except requests.exceptions.RequestException as e:
                return None  # Handle network error, like timeout or unreachable URL
            except json.JSONDecodeError as e:
                return None  # Handle error in case response is not valid JSON
            
            # Save to cache
            with open(video_cache_path, "w", encoding="utf-8") as f:
                json.dump(resp, f, indent=2, ensure_ascii=False)

        if resp is None:
            return None  # If there was an issue getting the response

        # Extract video details from the JSON response
        video_details = resp.get("videoDetails", {})
        microformat = resp.get("microformat", {}).get("playerMicroformatRenderer", {})

        channel_handle = ""
        if "ownerProfileUrl" in microformat:
            channel_handle = microformat["ownerProfileUrl"].split("/")[-1]
        channel_handle = channel_handle.lstrip("@")

        duration_seconds = int(video_details.get("lengthSeconds") or 0)

        return {
            "videoId": video_id,
            "title": video_details.get("title") or microformat.get("title", {}).get("simpleText", ""),
            "publishedAt": microformat.get("publishDate", ""),
            "channelId": video_details.get("channelId") or microformat.get("externalChannelId", ""),
            "channelHandle": channel_handle,
            "channelTitle": video_details.get("author") or microformat.get("ownerChannelName", ""),
            "viewCount": int(video_details.get("viewCount", 0)),
            "likeCount": int(microformat.get("likeCount", 0)) if microformat.get("likeCount") else 0,
            "dislikeCount": 0,  # If you want to handle dislikes, you may need to check if this exists in `microformat`
            "description": microformat.get("description", {}).get("simpleText") or video_details.get("shortDescription", ""),
            "durationSeconds": duration_seconds,
        }

    except Exception as e:
        return None
        
# === XML Generator ===
def viitube_playlist_generate_video_entry(video, base_url):
    return f"""<entry gd:etag='W/"YDwqeyM."'>
    <id>tag:youtube.com,2008:playlist:5A4E6E3F17B78FA1:PLFoD08MpX6_oJJo4YULX39bJJFtqy_8cM</id>
    <published>{escape(video['publishedAt'])}</published>
    <updated>{escape(video['publishedAt'])}</updated>
    <category scheme="http://schemas.google.com/g/2005#kind" term="{base_url}/schemas/2007#video"/>
    <category scheme="{base_url}/schemas/2007/categories.cat" term="Entertainment" label="Entertainment"/>
    <title>{escape(video['title'])}</title>
    <content type="application/x-shockwave-flash" src="http://www.youtube.com/v/{video['videoId']}?version=3&amp;f=playlists/&amp;app=youtube_gdata"/>
    <link rel="alternate" type="text/html" href="http://www.youtube.com/watch?v={video['videoId']}&amp;feature=youtube_gdata"/>
    <link rel="{base_url}/schemas/2007#video.related" type="application/atom+xml" href="{base_url}/feeds/api/videos/{video['videoId']}/related?v=2"/>
    <link rel="{base_url}/schemas/2007#mobile" type="text/html" href="http://m.youtube.com/details?v={video['videoId']}"/>
    <link rel="{base_url}/schemas/2007#uploader" type="application/atom+xml" href="{base_url}/feeds/api/users/{video['channelId']}?v=2"/>
    <link rel="related" type="application/atom+xml" href="{base_url}/feeds/api/videos/{video['videoId']}?v=2"/>
    <link rel="self" type="application/atom+xml" href="{base_url}/feeds/api/playlists//5A4E6E3F17B78FA1/PLFoD08MpX6_oJJo4YULX39bJJFtqy_8cM?v=2"/>
    <author>
        <name>{escape(video['channelHandle'])}</name>
        <uri>{base_url}/feeds/api/users/{escape(video['channelHandle'])}</uri>
        <yt:userId>{escape(video['channelId'])}</yt:userId>
    </author>
    <yt:accessControl action="comment" permission="allowed"/>
    <yt:accessControl action="commentVote" permission="allowed"/>
    <yt:accessControl action="videoRespond" permission="moderated"/>
    <yt:accessControl action="rate" permission="allowed"/>
    <yt:accessControl action="embed" permission="allowed"/>
    <yt:accessControl action="list" permission="allowed"/>
    <yt:accessControl action="autoPlay" permission="allowed"/>
    <yt:accessControl action="syndicate" permission="allowed"/>
    <gd:comments>
        <gd:feedLink rel="{base_url}/schemas/2007#comments" href="{base_url}/feeds/api/videos/{video['videoId']}/comments?v=2" countHint="8"/>
    </gd:comments>
    <yt:hd/>
		<media:group>
			<media:category label='Entertainment' scheme='{base_url}/schemas/2007/categories.cat'>Entertainment</media:category>
            <media:content url='{base_url}/channel_fh264_getvideo?v={video['videoId']}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='3'/>
			<media:credit role='uploader' scheme='urn:youtube' yt:display='{video['channelTitle']}'>{video['channelHandle']}</media:credit>
			<media:description type='plain'>{escape(video['description'])}</media:description>
			<media:keywords/>
			<media:license type='text/html' href='http://www.youtube.com/t/terms'>youtube</media:license>
			<media:player url='http://www.youtube.com/watch?v={video['videoId']}&amp;feature=youtube_gdata_player'/>
			<media:thumbnail url='http://i1.ytimg.com/vi/{video['videoId']}/default.jpg' height='90' width='120' time='00:01:14' yt:name='default'/>
			<media:thumbnail url='http://i1.ytimg.com/vi/{video['videoId']}/mqdefault.jpg' height='180' width='320' yt:name='mqdefault'/>
			<media:thumbnail url='http://i1.ytimg.com/vi/{video['videoId']}/hqdefault.jpg' height='360' width='480' yt:name='hqdefault'/>
			<media:thumbnail url='http://i1.ytimg.com/vi/{video['videoId']}/sddefault.jpg' height='480' width='640' yt:name='sddefault'/>
			<media:thumbnail url='http://i1.ytimg.com/vi/{video['videoId']}/1.jpg' height='90' width='120' time='00:00:37' yt:name='start'/>
			<media:thumbnail url='http://i1.ytimg.com/vi/{video['videoId']}/2.jpg' height='90' width='120' time='00:01:14' yt:name='middle'/>
			<media:thumbnail url='http://i1.ytimg.com/vi/{video['videoId']}/3.jpg' height='90' width='120' time='00:01:51' yt:name='end'/>
			<media:title type='plain'>{video['title']}</media:title>
			<yt:duration seconds='{video.get("durationSeconds", 0)}'/>
			<yt:uploaded>2011-04-26T23:17:56.000Z</yt:uploaded>
			<yt:uploaderId>UC{video['channelId']}</yt:uploaderId>
			<yt:videoid>{video['videoId']}</yt:videoid>
		</media:group>
		<gd:rating average='4.2' max='5' min='1' numRaters='5' rel='http://schemas.google.com/g/2005#overall'/>
		<yt:statistics favoriteCount='0' viewCount='{video['viewCount']}'/>
		<yt:rating numDislikes='{video['dislikeCount']}' numLikes='{video['likeCount']}'/>
		<yt:position>{video['position']}</yt:position>
        
	</entry>"""

def viitube_playlist_generate_xml_feed(videos, base_url, playlist_id, playlist_title):
    entries = "\n".join(viitube_playlist_generate_video_entry(video, base_url) for video in videos)

    first_video = videos[0] if videos else {}
    channel_handle = first_video.get("channelHandle", "")
    channel_id = first_video.get("channelId", "")
    video_id = first_video.get("videoId", "")

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<feed
    xmlns='http://www.w3.org/2005/Atom'
    xmlns:app='http://www.w3.org/2007/app'
    xmlns:media='http://search.yahoo.com/mrss/'
    xmlns:openSearch='http://a9.com/-/spec/opensearch/1.1/'
    xmlns:gd='http://schemas.google.com/g/2005'
    xmlns:yt='http://gdata.youtube.com/schemas/2007' gd:etag='W/&quot;DUECRn47eCp7I2A9WhJVEkU.&quot;'>
    <id>tag:youtube.com,2008:playlist:{playlist_id}</id>
    <updated>2012-08-30T00:47:47.000Z</updated>
    <category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#playlist'/>
    <title>{playlist_title}</title>
    <subtitle>{playlist_title}</subtitle>
    <logo>http://www.gstatic.com/youtube/img/logo.png</logo>
    <link rel='alternate' type='text/html' href='http://www.youtube.com/playlist?list={playlist_id}'/>
    <link rel='http://schemas.google.com/g/2005#feed' type='applicatio0tom+xml' href='http://gdata.youtube.com/feeds/api/playlists//{playlist_id}?v=2'/>
    <link rel='http://schemas.google.com/g/2005#batch' type='applicatio0tom+xml' href='http://gdata.youtube.com/feeds/api/playlists//{playlist_id}/batch?v=2'/>
    <link rel='self' type='applicatio0tom+xml' href='http://gdata.youtube.com/feeds/api/playlists//{playlist_id}?start-index=1&amp;max-results=25&amp;v=2'/>
    <link rel='service' type='applicatio0tomsvc+xml' href='http://gdata.youtube.com/feeds/api/playlists//{playlist_id}?alt=atom-service&amp;v=2'/>
    <author>
        <name>{channel_id}</name>
        <uri>http://gdata.youtube.com/feeds/api/users/{channel_id}</uri>
        <yt:userId>{channel_id}</yt:userId>
    </author>
    <generator version='2.1' uri='http://gdata.youtube.com'>YouTube data API</generator>
    <openSearch:totalResults>{len(videos)}</openSearch:totalResults>
    <openSearch:startIndex>1</openSearch:startIndex>
    <openSearch:itemsPerPage>25</openSearch:itemsPerPage>
    <media:group>
        <media:content url='http://www.youtube.com/p/{playlist_id}' type='application/x-shockwave-flash' yt:format='5'/>
        <media:description type='plain'>{playlist_title}</media:description>
        <media:thumbnail url='http://i.ytimg.com/vi/{video_id}/default.jpg' height='90' width='120' yt:name='default'/>
        <media:thumbnail url='http://i.ytimg.com/vi/{video_id}/mqdefault.jpg' height='180' width='320' yt:name='mqdefault'/>
        <media:thumbnail url='http://i.ytimg.com/vi/{video_id}/hqdefault.jpg' height='360' width='480' yt:name='hqdefault'/>
        <media:title type='plain'>{playlist_title}</media:title>
    </media:group>
    <yt:playlistId>{playlist_id}</yt:playlistId>
{entries}
</feed>"""

@app.route("/feeds/api/playlists/<playlist_id>")
def viitube_playlist_xml(playlist_id):
    # Fetch raw playlist data
    raw = viitube_playlist_load_or_fetch_raw(playlist_id)
    
    # Extract playlist title and items
    playlist_title = viitube_playlist_extract_playlist_title(raw)
    items = viitube_playlist_extract_playlist_items(raw)

    # Read start-index and max-results from query parameters
    try:
        start_index = int(request.args.get("start-index", 1))
    except ValueError:
        start_index = 1
    
    try:
        max_results = int(request.args.get("max-results", 25))
    except ValueError:
        max_results = 25

    # Convert 1-based start-index to 0-based list index
    start_pos = max(start_index - 1, 0)
    end_pos = start_pos + max_results

    # Slice the playlist items based on the pagination parameters
    sliced_items = items[start_pos:end_pos]

    videos = []
    for item in sliced_items:
        details = viitube_playlist_fetch_video_details(item["videoId"])
        
        # Skip the item if video details are None
        if details is None:
            continue
        
        # Merge item and video details into a single dictionary
        video = {**item, **details}
        videos.append(video)
        
        # Rate limit to avoid throttling (sleep for 0.1 seconds)
        time.sleep(0.1)

    # Generate XML response with playlist data
    base_url = request.host_url.rstrip("/")  # Get the base URL of the request
    xmlresponse = viitube_playlist_generate_xml_feed(videos, base_url, playlist_id, playlist_title)

    # Return the XML response with the appropriate content type
    return Response(xmlresponse, content_type="application/xml")


def generate_device_id():
    charset = "qwertyuiopasdfghjklzxcvbnm1234567890"
    return ''.join(random.choices(charset, k=7))

@app.route('/youtube/accounts/registerDevice', methods=['POST'])
@app.route('/proxy/ytbt', methods=['POST'])
def register_device():
    device_id = generate_device_id()

    # Simulated check—can be replaced with real logic if needed
    used_device_ids = set()
    while device_id in used_device_ids:
        device_id = generate_device_id()

    # Send response similar to Node.js version
    response_text = f"DeviceId={device_id}\nDeviceKey=ULxlVAAVMhZ2GeqZA/X1GgqEEIP1ibcd3S+42pkWfmk="
    return response_text

TEMPLATE_PATH = 'Mobile/player.json'
Innertube_CACHE_DIR = 'assets/cache/innertube'
PLACEHOLDER = b'thevideoiid'  # must be 11 bytes for exact replacement

@app.route('/youtubei/v1/player', methods=['GET', 'POST'])
@app.route('/youtube/v3/players', methods=['GET', 'POST'])
def youtube_player():
    video_id = request.args.get('id', '').strip() 

    if not video_id:
        return jsonify({"error": "Missing 'id' parameter"}), 400

    if len(video_id) != 11:
        return jsonify({"error": "Video ID must be 11 characters"}), 400

    # Prepare cache path
    os.makedirs(Innertube_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(Innertube_CACHE_DIR, f"{video_id}.json")

    # Return cached version if exists
    if os.path.exists(cache_path):
        return send_file(cache_path, mimetype='application/octet-stream')

    # Load binary template
    try:
        with open(TEMPLATE_PATH, 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        return jsonify({"error": "Template file not found"}), 500

    # Ensure placeholder exists
    if PLACEHOLDER not in data:
        return jsonify({"error": "Placeholder not found in binary"}), 500

    # Replace placeholder with video ID
    try:
        modified_data = data.replace(PLACEHOLDER, video_id.encode('utf-8'))
    except Exception as e:
        return jsonify({"error": f"Replacement failed: {str(e)}"}), 500

    # Save to cache
    try:
        with open(cache_path, 'wb') as f:
            f.write(modified_data)
    except Exception as e:
        return jsonify({"error": f"Failed to save: {str(e)}"}), 500

    return send_file(cache_path, mimetype='application/octet-stream')

    # Determine IP-based endpoint
    client_ip = request.host.split(':')[0]
    try:
        last_octet = client_ip.split('.')[-1]
        digit_count = len(last_octet)
        e_count = 10 + digit_count
        endpoint_name = f"g{'e' * e_count}t_video"
        video_url = f"http://{client_ip}/{endpoint_name}?video_id={video_id}"
    except Exception:
        video_url = f"http://{client_ip}/geeeeeeeet_video?video_id={video_id}"

    return jsonify({
        "status": "ok",
        "cache_file": cache_path,
        "video_url": video_url
    })


# 📁 Define storage paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "assets")
CACHE_PATH = os.path.join(SAVE_PATH, "cache", "videoinfo")

os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(CACHE_PATH, exist_ok=True)  

# ✅ Helper class to fetch video info
class GetVideoInfo:
    def build(self, video_id):
        cache_file = os.path.join(CACHE_PATH, f"{video_id}.json")

        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

        # 🌐 Fetch from YouTube internal API
        url = "https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }
        payload = {
            "context": {
                "client": {
                    "hl": "en",
                    "gl": "US",
                    "clientName": "WEB",
                    "clientVersion": "2.20210714.01.00"
                }
            },
            "videoId": video_id
        }

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            return {"error": "Failed to fetch video info"}

        try:
            data = response.json()
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except Exception as e:
            return {"error": str(e)}


# 🎥 Download video and fetch info
def download_video(video_id):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    yt = YouTube(video_url)

    video_filename = f"{video_id}.mp4"
    video_path = os.path.join(SAVE_PATH, video_filename)

    if not os.path.exists(video_path):
        stream = yt.streams.get_highest_resolution()
        stream.download(SAVE_PATH, filename=video_filename)

    # 💾 Also get video info
    GetVideoInfo().build(video_id)

    return video_path


# 🔍 Extract clean video ID
def get_clean_video_id():
    raw_id = request.args.get("video_id", "") or request.args.get("v", "")
    match = re.match(r"^[A-Za-z0-9_-]{11}", raw_id)
    return match.group(0) if match else None


# 📡 All endpoints below
@app.route('/get_480', methods=['GET'])
@app.route('/exp_hd', methods=['GET'])
@app.route('/channel_fh264_getvideo', methods=['GET'])
@app.route('/geeeeeeeeeeeeet_video', methods=['GET'])
@app.route('/geeeeeeeeeeeet_video', methods=['GET'])
@app.route('/get_video', methods=['GET'])
@app.route('/geeeeeeeeeeeeeet_video', methods=['GET'])
def serve_video():
    video_id = get_clean_video_id()

    if not video_id:
        return "Missing or invalid video_id parameter", 400

    try:
        video_path = download_video(video_id)
        return send_file(video_path, as_attachment=True)
    except Exception as e:
        return "Internal server error", 500

@app.route('/wiitv')
def wiitv():
    return send_file('swf/leanbacklite_wii.swf', mimetype='application/x-shockwave-flash')

@app.route('/s/tv/wii/config')
def config():
    return send_file('swf/yt_lbl.swf', mimetype='application/x-shockwave-flash')
    
@app.route('/youtube/v3/activities')
def river1():
    return send_file('Mobile/browse.json')
 
@app.route('/apiplayer')
def apiloader():
    return send_from_directory('swf', 'apiloader.swf')
 
@app.route('/yt/swfbin/apiplayer-vfl3wD2Ji.swf')
@app.route('/videoplayback')
def videoplayback():
    return send_from_directory('swf', 'apiplayer.swf')
  
@app.route('/leanbacklite')
@app.route('/tv')
def tv():
    return send_from_directory('swf', 'leanbacklite_v3.swf')
   
@app.route('/device_204')
@app.route('/leanback_ajax')
def leanback_ajax():
    return send_from_directory('swf', 'leanback_ajax.json')
    
def river_clean_xml_text(text):
    illegal_xml_re = re.compile(
        r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]'
    )
    if text:
        return illegal_xml_re.sub('', text)
    return ''

Startofxml = """<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:media="http://search.yahoo.com/mrss/"
      xmlns:yt="http://gdata.youtube.com/schemas/2007"
      xmlns:openSearch="http://a9.com/-/spec/opensearchrss/1.0/">
  <openSearch:totalResults>20</openSearch:totalResults>
  <link rel="next" href="..."/>"""

ending = """</feed>"""

xmltemplate = """    <entry>
    <link>
      <entry>
        <id>tag:youtube.com,2008:video:{videoId}</id>
        <title>{title}</title>
        <published>{published}</published>
        <author><name>{author}</name></author>
        <media:group>
          <media:thumbnail yt:name="mqdefault" url="http://i.ytimg.com/vi/{videoId}/mqdefault.jpg"/>
          <yt:duration seconds="{duration}"/>
          <yt:uploaderId>EE{channelId}</yt:uploaderId>
          <media:description>{description}</media:description>
          <yt:videoid>{videoId}</yt:videoid>
        </media:group>
        <yt:statistics viewCount="{viewCount}"/>
        <yt:hd/>
      </entry>
    </link>
  </entry>"""

CACHE_PATH = os.path.join("assets", "cache", "users", "river.xml")

@app.route('/feeds/api/users/default/river', methods=['GET'])
def river():
    oauth_token = request.args.get('oauth_token')

    if not oauth_token:
        # Return cached XML if exists
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                cached_xml = f.read()
            return Response(cached_xml, content_type='application/xml')
        else:
            return Response("No cached data available and no oauth_token provided.", status=404)

    try:
        creds = Credentials(oauth_token)
        youtube = build('youtube', 'v3', credentials=creds)

        subs_request = youtube.subscriptions().list(
            part='snippet',
            mine=True,
            maxResults=50
        )
        subs_response = subs_request.execute()
        channel_ids = [item['snippet']['resourceId']['channelId'] for item in subs_response['items']]

        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        published_after = seven_days_ago.isoformat()

        all_entries = []
        max_videos_total = 20
        videos_fetched = 0

        for channel_id in channel_ids:
            if videos_fetched >= max_videos_total:
                break

            search_request = youtube.search().list(
                part='snippet',
                channelId=channel_id,
                maxResults=10,
                order='date',
                publishedAfter=published_after,
                type='video'
            )
            search_response = search_request.execute()

            video_ids = [item['id']['videoId'] for item in search_response['items']]
            if not video_ids:
                continue

            videos_request = youtube.videos().list(
                part='contentDetails,snippet,statistics',
                id=','.join(video_ids)
            )
            videos_response = videos_request.execute()

            for video in videos_response['items']:
                if videos_fetched >= max_videos_total:
                    break

                snippet = video['snippet']
                stats = video.get('statistics', {})
                content = video['contentDetails']

                video_id = video['id']
                title = snippet['title']
                published = snippet['publishedAt']
                author = snippet['channelTitle']
                channel_id = snippet['channelId']
                description = snippet.get('description', '')

                duration_iso = content['duration']
                duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())

                view_count = stats.get('viewCount', '0')

                entry = xmltemplate.format(
                    videoId=river_clean_xml_text(video_id),
                    title=river_clean_xml_text(title),
                    published=river_clean_xml_text(published),
                    author=river_clean_xml_text(author),
                    duration=duration_seconds,
                    channelId=river_clean_xml_text(channel_id),
                    description=river_clean_xml_text(description),
                    viewCount=view_count
                )
                all_entries.append(entry)

                videos_fetched += 1

        full_xml = Startofxml + "\n".join(all_entries) + ending

        # Save fresh XML to cache
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            f.write(full_xml)

        return Response(full_xml, content_type='application/xml')

    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)


PROFILE_PICTURE_DIR = './assets/cache/pfp'
os.makedirs(PROFILE_PICTURE_DIR, exist_ok=True)

UPDATE_INTERVAL = 12 * 3600  # 12 hours

def get_channel_pfp_url(channel_id):
    try:
        channel_url = f'https://www.youtube.com/channel/{channel_id}'
        channel = Channel(channel_url)

        # pytube.Channel doesn’t provide pfp directly, so fetch HTML manually
        response = requests.get(channel_url)
        if response.status_code != 200:
            return None
        html = response.text

        # Extract profile picture from meta tag og:image
        import re
        match = re.search(r'<meta property="og:image" content="([^"]+)">', html)
        if match:
            return match.group(1)
        else:
            return None
    except Exception as e:
        return None

def save_pfp(channel_id):
    pfp_url = get_channel_pfp_url(channel_id)
    if not pfp_url:
        return False
    
    response = requests.get(pfp_url)
    if response.status_code != 200:
        return False

    filepath = os.path.join(PROFILE_PICTURE_DIR, f'{channel_id}.jpg')
    with open(filepath, 'wb') as f:
        f.write(response.content)
    return True

def needs_update(channel_id):
    filepath = os.path.join(PROFILE_PICTURE_DIR, f'{channel_id}.jpg')
    if not os.path.exists(filepath):
        return True
    last_modified = os.path.getmtime(filepath)
    return (time.time() - last_modified) > UPDATE_INTERVAL

@app.route('/feeds/api/users/<channel_id>/icon')
def serve_pfp(channel_id):
    filepath = os.path.join(PROFILE_PICTURE_DIR, f'{channel_id}.jpg')

    if needs_update(channel_id):
        success = save_pfp(channel_id)
        if not success and not os.path.exists(filepath):
            abort(404, description='Profile picture not found')

    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    else:
        abort(404, description='Profile picture not found')


# Constants and cache dirs
MOBILE_CHANNEL_INFO_CACHE = Path("./assets/cache/channelinfo")
MOBILE_CHANNEL_SEARCH = Path("./assets/cache/search")
MOBILE_CHANNEL_INFO_CACHE.mkdir(parents=True, exist_ok=True)
MOBILE_CHANNEL_SEARCH.mkdir(parents=True, exist_ok=True)

MOBILE_YOUTUBEI_BROWSE_URL = "https://www.youtube.com/youtubei/v1/browse"
MOBILE_YOUTUBEI_SEARCH_URL = "https://www.youtube.com/youtubei/v1/search"
MOBILE_CLIENT_VERSION = "2.20230801.00.00"
MOBILE_MAX_RETRIES = 3
MOBILE_RETRY_DELAY = 1  # seconds

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    ),
    "X-Youtube-Client-Name": "1",
    "X-Youtube-Client-Version": MOBILE_CLIENT_VERSION,
    "Origin": "https://www.youtube.com"
}

def mobile_get_cache_path_channelinfo(channel_id):
    return MOBILE_CHANNEL_INFO_CACHE / f"{channel_id}.json"

def mobile_get_cache_path_search(handle):
    sanitized = handle.lower().lstrip("@").replace(" ", "_")
    return MOBILE_CHANNEL_SEARCH / f"{sanitized}.json"

def mobile_is_cache_valid(path):
    if not path.exists():
        return False
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    return age_hours < 48  # 48 hours cache expiry

def mobile_post_with_retries(url, headers, json_payload):
    for attempt in range(1, MOBILE_MAX_RETRIES + 1):
        try:
            response = requests.post(url, headers=headers, json=json_payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            if attempt < MOBILE_MAX_RETRIES:
                time.sleep(MOBILE_RETRY_DELAY * attempt)
            else:
                raise

def mobile_fetch_channel_info(channel_id):
    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": MOBILE_CLIENT_VERSION
            }
        },
        "browseId": channel_id
    }
    return mobile_post_with_retries(MOBILE_YOUTUBEI_BROWSE_URL, HEADERS, payload)

def mobile_fetch_search_results(handle):
    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": MOBILE_CLIENT_VERSION
            }
        },
        "query": handle,
        "params": "EgIQAg%3D%3D"  # This filters the search to channels only
    }
    return mobile_post_with_retries(MOBILE_YOUTUBEI_SEARCH_URL, HEADERS, payload)


def mobile_normalize_handle(handle: str) -> str:
    return handle.lower().lstrip("@")

def mobile_parse_number(text):
    if not text or text == "0":
        return "0"
    text = text.lower().replace("subscribers", "").replace("videos", "").strip()
    multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}

    try:
        text = text.replace(",", "")
        if text[-1] in multipliers:
            num = float(text[:-1])
            num = int(num * multipliers[text[-1]])
        else:
            num = int(float(text))
        return str(num)
    except Exception:
        return "0"

def mobile_parse_channel_data(data):
    try:
        header = data.get("header", {}).get("pageHeaderRenderer", {})

        # Extract total views string like "1,234,567 views"
        total_views_text = header.get("viewCountText", {}).get("simpleText", "0")

        title_data = header.get("content", {}).get("pageHeaderViewModel", {}).get("title", {})
        name = title_data.get("dynamicTextViewModel", {}).get("text", {}).get("content", "0")

        metadata_rows = header.get("content", {}).get("pageHeaderViewModel", {}).get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
        handle = "0"
        subscribers = "0"
        total_uploads = "0"

        if len(metadata_rows) > 0:
            handle = metadata_rows[0]["metadataParts"][0]["text"]["content"]

        if len(metadata_rows) > 1:
            # Parse subscribers and uploads more robustly
            for part in metadata_rows[1].get("metadataParts", []):
                content = part.get("text", {}).get("content", "").lower()
                if "subscriber" in content:
                    subscribers = part.get("text", {}).get("content", "0")
                elif "video" in content:
                    total_uploads = part.get("text", {}).get("content", "0")

        avatar_sources = header.get("content", {}).get("pageHeaderViewModel", {}).get("image", {}).get("decoratedAvatarViewModel", {}).get("avatar", {}).get("avatarViewModel", {}).get("image", {}).get("sources", [])
        profile_picture = avatar_sources[-1]["url"] if avatar_sources else "0"

        description = data.get("metadata", {}).get("channelMetadataRenderer", {}).get("description", "0")
        channel_id = data.get("metadata", {}).get("channelMetadataRenderer", {}).get("externalId", "0")

        subscribers_num = mobile_parse_number(subscribers)
        uploads_num = mobile_parse_number(total_uploads)
        total_views_num = mobile_parse_number(total_views_text)

        return {
            "channel_id": channel_id,
            "name": name,
            "description": description,
            "subscribers": subscribers_num,
            "total_uploads": uploads_num,
            "profile_picture": profile_picture,
            "handle": handle.lstrip("@"),
            "total_views": total_views_num
        }

    except Exception as e:
        return {}

def mobile_search_channel_handle(handle):
    cache_path = mobile_get_cache_path_search(handle)

    data = None
    if mobile_is_cache_valid(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            # Optionally delete corrupted cache file
            try:
                os.remove(cache_path)
            except OSError:
                # Could log the error here or silently ignore
                pass
            data = None  # or handle re-fetching the data
    else:
        data = None  # Cache invalid, handle accordingly

    if data is None:
        data = mobile_fetch_search_results(handle)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    norm_handle = mobile_normalize_handle(handle)

    try:
        sections = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"]
        for section in sections:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                channel = item.get("channelRenderer")
                if channel:
                    canonical_url = channel.get("navigationEndpoint", {}).get("browseEndpoint", {}).get("canonicalBaseUrl", "")
                    channel_handle = canonical_url.lstrip("/").lstrip("@").lower()

                    if channel_handle == norm_handle:
                        return channel.get("channelId")

        # fallback: first channel ID if no exact match
        for section in sections:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                channel = item.get("channelRenderer")
                if channel:
                    return channel.get("channelId")

    except Exception as e:
        pass

    return None


def mobile_get_channel_info(channel_id):
    cache_path = mobile_get_cache_path_channelinfo(channel_id)

    if mobile_is_cache_valid(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = mobile_fetch_channel_info(channel_id)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return mobile_parse_channel_data(data)

def mobile_get_info_by_handle(handle):
    if handle.startswith("UC") and len(handle) == 24:
        return mobile_get_channel_info(handle)
    else:
        channel_id = mobile_search_channel_handle(handle)
        if not channel_id:
            return None
        return mobile_get_channel_info(channel_id)

@app.route("/feeds/api/channels/<handle>", methods=["GET"])
@app.route("/feeds/api/users/<handle>", methods=["GET"])
def mobile_user_info(handle):
    info = mobile_get_info_by_handle(handle)
    if not info:
        return Response("Channel not found", status=404, mimetype="text/plain")

    base_url = f"{request.scheme}://{request.host}"

    def mobile_xml_escape(text):
        if not text:
            return ""
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&apos;"))

    xml_response = f"""<?xml version='1.0' encoding='UTF-8'?>
<entry
    xmlns='http://www.w3.org/2005/Atom'
    xmlns:gd='http://schemas.google.com/g/2005'
    xmlns:yt='http://gdata.youtube.com/schemas/2007'
    xmlns:media='http://search.yahoo.com/mrss/' gd:etag='W/&quot;D0YMQX47eCp7I2A9XRdbEkQ.&quot;'>
    <id>tag:youtube.com,2008:user:{mobile_xml_escape(info.get('channel_id', '0'))}</id>
    <published>2007-10-11T09:27:42.000Z</published>
    <updated>2014-12-11T10:53:00.000Z</updated>
    <category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#userProfile'/>
    <category scheme='http://gdata.youtube.com/schemas/2007/channeltypes.cat' term='GURU'/>
    <title>{mobile_xml_escape(info.get('name', '0'))}</title>
    <summary>{mobile_xml_escape(info.get('description', ''))}</summary>
    <link rel='alternate' type='text/html' href='http://www.youtube.com/channel/{mobile_xml_escape(info.get('channel_id', '0'))}'/>
    <link rel='self' type='applicatio0tom+xml' href='{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('channel_id', '0'))}?v=2'/>
    <author>
        <name>{mobile_xml_escape(info.get('name', '0'))}</name>
        <uri>{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('handle', '0'))}</uri>
        <yt:userId>{mobile_xml_escape(info.get('channel_id', '0'))}</yt:userId>
    </author>
    <yt:channelId>{mobile_xml_escape(info.get('channel_id', '0'))}</yt:channelId>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.subscriptions' href='{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('handle', '0'))}/subscriptions?v=2' countHint='377'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.liveevent' href='{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('handle', '0'))}/live/events?v=2' countHint='0'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.favorites' href='{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('handle', '0'))}/favorites?v=2' countHint='99'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.contacts' href='{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('handle', '0'))}/contacts?v=2' countHint='284'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.inbox' href='{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('handle', '0'))}/inbox?v=2'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.playlists' href='{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('handle', '0'))}/playlists?v=2'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.uploads' href='{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('handle', '0'))}/uploads?v=2' countHint='321'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.newsubscriptionvideos' href='{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('handle', '0'))}/newsubscriptionvideos?v=2'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.watchwhileactivity' href='{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('handle', '0'))}/newsubscriptionvideos?v=2'/>
    <yt:googlePlusUserId>105395577935858592015</yt:googlePlusUserId>
    <yt:location>NL</yt:location>
    <yt:statistics lastWebAccess='1970-01-01T00:00:00.000Z' subscriberCount='{mobile_xml_escape(info.get('subscribers', '0'))}' videoWatchCount='0' viewCount='0' totalUploadViews='{mobile_xml_escape(info.get('total_uploads', '0'))}'/>
    <media:thumbnail url='{mobile_xml_escape(base_url)}/feeds/api/users/{mobile_xml_escape(info.get('channel_id', '0'))}/icon'/>
    <yt:userId>{mobile_xml_escape(info.get('channel_id', '0'))}</yt:userId>
    <yt:username display='{mobile_xml_escape(info.get('name', '0'))}'>{mobile_xml_escape(info.get('name', '0'))}</yt:username>
</entry>"""

    return Response(xml_response, mimetype="application/xml")

@app.route('/schemas/2007/categories.cat')
def categories():
    return send_file('Mobile/categories.cat')

@app.route('/o/oauth2/device/code', methods=['POST'])
def deviceCode():
    response = requests.post(
        OAUTH2_DEVICE_CODE_URL,
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'scope': 'https://www.googleapis.com/auth/youtube',
        }
    )
    if response.status_code != 200:
        return jsonify({"error": "Failed to get device code"}), 400
    data = response.json()
    device_code = data['device_code']
    user_code = data['user_code']
    verification_url = data['verification_url']
    expires_in = data['expires_in']
    message = f"Please visit {verification_url} and enter the user code: {user_code}"
    return jsonify({
        'device_code': device_code,
        'user_code': user_code,
        'verification_url': verification_url,
        'expires_in': expires_in,
        'message': message
    })

@app.route('/o/oauth2/device/code/status', methods=['POST'])
def checkStatus():
    device_code = request.json.get('device_code')
    if not device_code:
        return jsonify({"error": "Device code is required"}), 400
    response = requests.post(
        OAUTH2_TOKEN_URL,
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'device_code': device_code,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
        }
    )
    if response.status_code == 200:
        data = response.json()
        return jsonify({
            'access_token': data['access_token'],
            'refresh_token': data.get('refresh_token'),
            'expires_in': data['expires_in']
        })
    elif response.status_code == 400:
        data = response.json()
        if data.get('error') == 'authorization_pending':
            return jsonify({"status": "pending", "message": "User hasn't authorized yet."}), 200
        elif data.get('error') == 'slow_down':
            return jsonify({"status": "slow_down", "message": "Too many requests, try again later."}), 429
        return jsonify({"error": "Authorization failed."}), 400
    return jsonify({"error": "Unknown error occurred."}), 500
@app.route('/o/oauth2/token', methods=['POST'])
def oauth2_token():
    youtube_oauth_url = 'https://www.youtube.com/o/oauth2/token'
    response = requests.post(youtube_oauth_url, data=request.form)
    if response.status_code == 200:
        return jsonify(response.json())


DEFAULT_USER_CACHE_FILE = os.path.join("assets", "cache", "users", "channelinfo.json")

def save_user_cache(data):
    os.makedirs(os.path.dirname(DEFAULT_USER_CACHE_FILE), exist_ok=True)
    with open(DEFAULT_USER_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_user_cache():
    if os.path.exists(DEFAULT_USER_CACHE_FILE):
        with open(DEFAULT_USER_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def fetch_youtube_user_data(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "part": "snippet,statistics,contentDetails",
        "mine": "true"
    }
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        headers=headers,
        params=params
    )
    if r.status_code != 200:
        return None, r.text
    data = r.json()
    if "items" not in data or not data["items"]:
        return None, "No channel data found"
    return data["items"][0], None

@app.route("/feeds/api/users/default")
def user_feed():
    access_token = request.args.get("oauth_token")

    if access_token:
        # Refresh data from YouTube
        item, error = fetch_youtube_user_data(access_token)
        if error:
            return Response(f"Failed to fetch channel info: {error}", status=401)
        # Save fresh data to cache
        save_user_cache(item)
    else:
        # Load cached data
        item = load_user_cache()
        if not item:
            return Response("No cached data found and no oauth_token provided", status=404)

    # Extract info from item
    try:
        channel_id = item["id"]
        title = item["snippet"]["title"]
        description = item["snippet"].get("description", "")
        subscribers = item["statistics"].get("subscriberCount", "0")
        total_views = item["statistics"].get("viewCount", "0")
        upload_count = item["statistics"].get("videoCount", "0")
        base_url = request.url_root.rstrip('/')
        handle = channel_id  # no handle in v3 API

        xml_response = f"""<?xml version='1.0' encoding='UTF-8'?>
<entry
    xmlns='http://www.w3.org/2005/Atom'
    xmlns:gd='http://schemas.google.com/g/2005'
    xmlns:yt='http://gdata.youtube.com/schemas/2007'
    xmlns:media='http://search.yahoo.com/mrss/' gd:etag='W/&quot;D0YMQX47eCp7I2A9XRdbEkQ.&quot;'>
    <id>tag:youtube.com,2008:user:{xml_escape(channel_id)}</id>
    <published>2007-10-11T09:27:42.000Z</published>
    <updated>2025-08-03T12:00:00.000Z</updated>
    <category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#userProfile'/>
    <category scheme='http://gdata.youtube.com/schemas/2007/channeltypes.cat' term='GURU'/>
    <title>{xml_escape(title)}</title>
    <summary>{xml_escape(description)}</summary>
    <link rel='alternate' type='text/html' href='http://www.youtube.com/channel/{xml_escape(channel_id)}'/>
    <link rel='self' type='application/atom+xml' href='{xml_escape(urljoin(base_url + "/", f"feeds/api/users/{channel_id}?v=2"))}'/>
    <author>
        <name>{xml_escape(title)}</name>
        <uri>{xml_escape(urljoin(base_url + "/", f"feeds/api/users/{handle}"))}</uri>
        <yt:userId>{xml_escape(channel_id)}</yt:userId>
    </author>
    <yt:channelId>{xml_escape(channel_id)}</yt:channelId>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.subscriptions' href='{xml_escape(urljoin(base_url + "/", f"feeds/api/users/{handle}/subscriptions?v=2"))}' countHint='0'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.liveevent' href='{xml_escape(urljoin(base_url + "/", f"feeds/api/users/{handle}/live/events?v=2"))}' countHint='0'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.favorites' href='{xml_escape(urljoin(base_url + "/", f"feeds/api/users/{handle}/favorites?v=2"))}' countHint='0'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.contacts' href='{xml_escape(urljoin(base_url + "/", f"feeds/api/users/{handle}/contacts?v=2"))}' countHint='0'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.inbox' href='{xml_escape(urljoin(base_url + "/", f"feeds/api/users/{handle}/inbox?v=2"))}'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.playlists' href='{xml_escape(urljoin(base_url + "/", f"feeds/api/users/{handle}/playlists?v=2"))}'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.uploads' href='{xml_escape(urljoin(base_url + "/", f"feeds/api/users/{handle}/uploads?v=2"))}' countHint='{xml_escape(upload_count)}'/>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.newsubscriptionvideos' href='{xml_escape(urljoin(base_url + "/", f"feeds/api/users/{handle}/newsubscriptionvideos?v=2"))}'/>
    <yt:statistics lastWebAccess='1970-01-01T00:00:00.000Z' subscriberCount='{xml_escape(subscribers)}' videoWatchCount='0' viewCount='{xml_escape(total_views)}' totalUploadViews='{xml_escape(total_views)}'/>
    <media:thumbnail url='{xml_escape(urljoin(base_url + "/", f"feeds/api/users/{channel_id}/icon"))}'/>
    <yt:userId>{xml_escape(channel_id)}</yt:userId>
    <yt:username display='{xml_escape(title)}'>{xml_escape(title)}</yt:username>
</entry>
"""
        return Response(xml_response, content_type="application/atom+xml")

    except Exception as e:
        return Response(f"Error generating XML: {str(e)}", status=500)
   
PLAYLIST_CACHE_FILE  = 'assets/cache/users/playlistinfo.json'

def fetch_playlists_from_api(oauth_token):
    url = 'https://www.googleapis.com/youtube/v3/playlists'
    params = {
        'part': 'snippet,contentDetails',
        'mine': 'true',
        'maxResults': 25
    }
    headers = {
        'Authorization': f'Bearer {oauth_token}'
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def fetch_first_video_info(oauth_token, playlist_id):
    """Get the first video's ID and thumbnail URL in the playlist."""
    url = 'https://www.googleapis.com/youtube/v3/playlistItems'
    params = {
        'part': 'snippet',
        'playlistId': playlist_id,
        'maxResults': 25
    }
    headers = {
        'Authorization': f'Bearer {oauth_token}'
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        items = data.get('items', [])
        if not items:
            return "", ""  # no videos in playlist
        first_video_id = items[0]['snippet']['resourceId']['videoId']
        thumbnails = items[0]['snippet'].get('thumbnails', {})
        thumbnail_url = ""
        for quality in ['maxres', 'standard', 'high', 'medium', 'default']:
            if quality in thumbnails:
                thumbnail_url = thumbnails[quality]['url']
                break
        return first_video_id, thumbnail_url
    else:
        return "", ""

def build_xml_template(data, base_url, oauth_token=None):
    if not data:
        return '"""$xmltemplates\n<error>Unable to retrieve data</error>\n"""'

    xml_template = [f'''<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'
xmlns:media='http://search.yahoo.com/mrss/'
xmlns:openSearch='http://a9.com/-/spec/opensearchrss/1.0/'
xmlns:gd='http://schemas.google.com/g/2005'
xmlns:yt='{base_url}/schemas/2007'>
    <id>{base_url}/feeds/mobile/api/standardfeeds/us/recently_featured</id>
    <updated>2010-12-21T18:59:58.000-08:00</updated>
    <category scheme='http://schemas.google.com/g/2005#kind' term='{base_url}/schemas/2007#video'/>
    <title type='text'> </title>
    <logo>http://www.youtube.com/img/pic_youtubelogo_123x63.gif</logo>
    <author>
        <name>YouTube</name>
        <uri>http://www.youtube.com/</uri>
    </author>
    <generator version='2.0' uri='{base_url}/'>YouTube data API</generator>
    <openSearch:totalResults>25</openSearch:totalResults>
    <openSearch:startIndex>1</openSearch:startIndex>
    <openSearch:itemsPerPage>25</openSearch:itemsPerPage>
''']


    for item in data.get('items', []):
        playlist_id = item.get("id", "")
        title = item["snippet"].get("title", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        description = item["snippet"].get("description", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        published_at = item["snippet"].get("publishedAt", "")
        item_count = item["contentDetails"].get("itemCount", 0)
        author = item["snippet"].get("channelTitle", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        channel_id = item["snippet"].get("channelId", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        first_video_id = ""
        thumbnail_url = ""
        if oauth_token:
            first_video_id, thumbnail_url = fetch_first_video_info(oauth_token, playlist_id)

        xml_template.append(f"""<entry>
	    <id>{base_url}/feeds/mobile/api/playlists/{playlist_id}</id>
        <playlistId>{playlist_id}</playlistId>
        <yt:playlistId>{playlist_id}</yt:playlistId>
		<published>2008-08-25T10:05:58.000-07:00</published>
		<updated>2008-08-27T22:37:59.000-07:00</updated>
		<category scheme='http://schemas.google.com/g/2005#kind' term='{base_url}/schemas/2007#playlistLink'/>
		<title type='text'>{title}</title>
		<content type='text' src='{base_url}/feeds/mobile/api/playlists/{playlist_id}'>None</content>
		<link rel='related' type='application/atom+xml' href='{base_url}/feeds/mobile/api/users/{author}'/>
		<link rel='alternate' type='text/html' href='{base_url}/view_play_list?p={playlist_id}'/>
		<link rel='self' type='application/atom+xml' href='{base_url}/feeds/mobile/api/playlists/{playlist_id}'/>
		<author>
			<name>{author}</name>
			<uri>{base_url}/feeds/mobile/api/users/{author}</uri>
		</author>
		<gd:feedLink rel='{base_url}/schemas/2007#playlist' href='{base_url}/feeds/mobile/api/playlists/{playlist_id}' countHint='{item_count}'/>
		<yt:description>{description}</yt:description>
		<media:group>
			<media:thumbnail url='http://i.ytimg.com/vi/{first_video_id}/mqdefault.jpg' height='180' width='320' yt:name='mqdefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{first_video_id}/mqdefault.jpg' height='180' width='320' yt:name='mqdefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{first_video_id}/hqdefault.jpg' height='360' width='480' yt:name='hqdefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{first_video_id}/sddefault.jpg' height='480' width='640' yt:name='sddefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{first_video_id}/1.jpg' height='90' width='120' time='00:10:26.500' yt:name='start'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{first_video_id}/2.jpg' height='90' width='120' time='00:20:53' yt:name='middle'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{first_video_id}/3.jpg' height='90' width='120' time='00:31:19.500' yt:name='end'/>
		</media:group>
        <yt:countHint>{item_count}</yt:countHint>
		<summary>{description}</summary>
	</entry>""")

    xml_template.append('</feed>')
    final_xml = '\n'.join(xml_template)
    return f'{final_xml}'

@app.route('/feeds/api/users/default/playlists', methods=['GET'])
def get_playlists():
    oauth_token = request.args.get('oauth_token')

    if oauth_token:
        data = fetch_playlists_from_api(oauth_token)
        if data:
            os.makedirs(os.path.dirname(PLAYLIST_CACHE_FILE ), exist_ok=True)
            with open(PLAYLIST_CACHE_FILE , 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            return Response("Error fetching data from YouTube API.", status=400)
    else:
        if os.path.exists(PLAYLIST_CACHE_FILE ):
            with open(PLAYLIST_CACHE_FILE , 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            return Response("No cached data found and no token provided.", status=404)

    base_url = request.url_root.rstrip('/')
    xml_output = build_xml_template(data, base_url, oauth_token)
    return Response(xml_output, mimetype='text/plain')
    

# ========== UTILS ==========

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def save_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_text_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def file_exists(path):
    return os.path.isfile(path)

# ========== YOUTUBE DATA ==========

def get_dislike_count(video_id):
    url = f"https://returnyoutubedislikeapi.com/votes?videoId={video_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            path = f"./assets/cache/dislike"
            ensure_dir(path)
            save_json(data, f"{path}/{video_id}.json")
            return data.get('dislikes', 0)
        return 0
    except:
        return 0

def build_playlist_xml(videos_info, base_url):
    xml = ["""<?xml version='1.0' encoding='UTF-8'?>
<feed
	xmlns='http://www.w3.org/2005/Atom'
	xmlns:app='http://www.w3.org/2007/app'
	xmlns:media='http://search.yahoo.com/mrss/'
	xmlns:openSearch='http://a9.com/-/spec/opensearch/1.1/'
	xmlns:gd='http://schemas.google.com/g/2005'
	xmlns:yt='{e(base_url)}/schemas/2007' gd:etag='W/&quot;DUECRn47eCp7I2A9WhJVEkU.&quot;'>
	<id>tag:youtube.com,2008:playlist:5A4E6E3F17B78FA1</id>
	<updated>2012-08-30T00:47:47.000Z</updated>
	<category scheme='http://schemas.google.com/g/2005#kind' term='{e(base_url)}/schemas/2007#playlist'/>
	<title>Website</title>
	<subtitle>New Vybe Videos</subtitle>
	<logo>http://www.gstatic.com/youtube/img/logo.png</logo>
	<link rel='alternate' type='text/html' href='http://www.youtube.com/playlist?list=PL5A4E6E3F17B78FA1'/>
	<link rel='http://schemas.google.com/g/2005#feed' type='application/atom+xml' href='{e(base_url)}/feeds/api/playlists/5A4E6E3F17B78FA1?v=2'/>
	<link rel='http://schemas.google.com/g/2005#batch' type='application/atom+xml' href='{e(base_url)}/feeds/api/playlists/5A4E6E3F17B78FA1/batch?v=2'/>
	<link rel='self' type='application/atom+xml' href='{e(base_url)}/feeds/api/playlists/5A4E6E3F17B78FA1?start-index=1&amp;max-results=25&amp;v=2'/>
	<link rel='service' type='application/atomsvc+xml' href='{e(base_url)}/feeds/api/playlists/5A4E6E3F17B78FA1?alt=atom-service&amp;v=2'/>
	<author>
		<name>NEWVYBE</name>
		<uri>{e(base_url)}/feeds/api/users/NEWVYBE</uri>
		<yt:userId>2rGyD633KCNs0jn3ifYH5g</yt:userId>
	</author>
	<generator version='2.1' uri='{e(base_url)}'>YouTube data API</generator>
	<openSearch:totalResults>6</openSearch:totalResults>
	<openSearch:startIndex>1</openSearch:startIndex>
	<openSearch:itemsPerPage>25</openSearch:itemsPerPage>
	<media:group>
		<media:content url='http://www.youtube.com/p/PL5A4E6E3F17B78FA1' type='application/x-shockwave-flash' yt:format='5'/>
		<media:description type='plain'>New Vybe Videos</media:description>
		<media:thumbnail url='http://i.ytimg.com/vi/0grd767X4Jg/default.jpg' height='90' width='120' yt:name='default'/>
		<media:thumbnail url='http://i.ytimg.com/vi/0grd767X4Jg/mqdefault.jpg' height='180' width='320' yt:name='mqdefault'/>
		<media:thumbnail url='http://i.ytimg.com/vi/0grd767X4Jg/hqdefault.jpg' height='360' width='480' yt:name='hqdefault'/>
		<media:title type='plain'>Website</media:title>
	</media:group>
	<yt:playlistId>PL5A4E6E3F17B78FA1</yt:playlistId>"""]
    for video in videos_info:
        def e(t): return clean_xml_text(t)
        xml.append(f"""    <entry>
        <id>{e(video.get('video_id'))}</id>
        <updated>2010-06-30T22:34:43.880Z</updated>
        <title>{e(video.get('title'))}</title>
        <link rel='alternate' type='text/html' href='http://www.youtube.com/watch?v={e(video.get('video_id'))}&amp;feature=youtube_gdata'/>
        <link rel='{e(base_url)}/schemas/2007#video.responses' type='application/atom+xml' href='{e(base_url)}/feeds/api/videos/{e(video.get('video_id'))}/responses?v=2'/>
        <link rel='{e(base_url)}/schemas/2007#video.related' type='application/atom+xml' href='{e(base_url)}/feeds/api/videos/{e(video.get('video_id'))}/related?v=2'/>
        <link rel='related' type='application/atom+xml' href='{e(base_url)}/feeds/api/videos/{e(video.get('video_id'))}?v=2'/>
        <link rel='self' type='application/atom+xml' href='{e(base_url)}/feeds/api/playlists/0A7ED544A0D9877D/00A37F607671690E?v=2'/>
		<author>
			<name>{e(video.get('author_user_id'))}</name>
			<uri>{e(base_url)}/feeds/api/users/{e(video.get('author_user_id'))}</uri>
			<yt:userId>ee{e(video.get('author_user_id'))}</yt:userId>
		</author>
        <yt:accessControl action='comment' permission='allowed'/>
        <yt:accessControl action='commentVote' permission='allowed'/>
        <yt:accessControl action='videoRespond' permission='moderated'/>
        <yt:accessControl action='rate' permission='allowed'/>
        <yt:accessControl action='embed' permission='allowed'/>
        <yt:accessControl action='syndicate' permission='allowed'/>
        <yt:accessControl action='list' permission='allowed'/>
        <gd:comments>
            <gd:feedLink href='{e(base_url)}/feeds/api/videos/{e(video.get('video_id'))}/comments?v=2' countHint='1'/>
        </gd:comments>
        <media:group>
            <media:content url='{e(base_url)}/get_video?video_id={e(video.get('video_id'))}/mp4' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='3'/>
            <media:credit role='uploader' scheme='urn:youtube' yt:display='{e(video.get('author_name'))}'>{e(video.get('author_user_id'))}</media:credit>
            <media:description type='plain'>{e(video.get('description'))}</media:description>
            <media:keywords>-</media:keywords>
            <media:player url='http://www.youtube.com/watch?v={e(video.get('video_id'))}&amp;feature=youtube_gdata'/>
            <media:thumbnail yt:name='hqdefault' url='http://i.ytimg.com/vi/{e(video.get('video_id'))}/hqdefault.jpg' height='240' width='320' time='00:00:00'/>
            <media:thumbnail yt:name='poster' url='http://i.ytimg.com/vi/{e(video.get('video_id'))}/0.jpg' height='240' width='320' time='00:00:00'/>
            <media:thumbnail yt:name='default' url='http://i.ytimg.com/vi/{e(video.get('video_id'))}/0.jpg' height='240' width='320' time='00:00:00'/>
            <media:title type='plain'>{e(video.get('title'))}</media:title>
            <yt:duration seconds='{e(video.get('duration_seconds'))}'/>
            <yt:uploaded>{e(video.get('published_at'))}</yt:uploaded>
			<yt:uploaderId>EE{e(video.get('author_user_id'))}</yt:uploaderId>
			<yt:videoid>{e(video.get('video_id'))}</yt:videoid>
        </media:group>
		<gd:rating average='4.2' max='5' min='1' numRaters='5' rel='http://schemas.google.com/g/2005#overall'/>
		<yt:statistics favoriteCount='0' viewCount='{e(video.get('view_count'))}'/>
		<yt:rating numDislikes='{e(video.get('dislike_count'))}' numLikes='{e(video.get('like_count'))}'/>
		<yt:position>{e(video.get('position'))}</yt:position>
    </entry>""")
    xml.append('</feed>')
    return '\n'.join(xml)

def get_playlist_videos_details(access_token, playlist_id):
    creds = Credentials(token=access_token)
    youtube = build('youtube', 'v3', credentials=creds)

    playlist_path = f"./assets/cache/users/playlists"
    videos_path = f"{playlist_path}/videos"
    ensure_dir(playlist_path)
    ensure_dir(videos_path)

    all_playlist_items = []
    videos_info = []
    next_page_token = None

    while True:
        playlist_response = youtube.playlistItems().list(
            part='snippet,contentDetails',
            playlistId=playlist_id,
            maxResults=25,
            pageToken=next_page_token
        ).execute()

        all_playlist_items.extend(playlist_response.get('items', []))
        video_ids = [i['contentDetails']['videoId'] for i in playlist_response['items']]
        positions = [i['snippet']['position'] for i in playlist_response['items']]

        video_response = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=','.join(video_ids)
        ).execute()

        channel_ids = list({v['snippet']['channelId'] for v in video_response.get('items', [])})
        channel_response = youtube.channels().list(
            part='snippet',
            id=','.join(channel_ids)
        ).execute()

        channel_map = {
            ch['id']: ch['snippet'].get('customUrl') or ch['snippet'].get('title')
            for ch in channel_response.get('items', [])
        }

        for i, video in enumerate(video_response.get('items', [])):
            snippet = video['snippet']
            stats = video.get('statistics', {})
            content = video.get('contentDetails', {})

            duration = int(isodate.parse_duration(content['duration']).total_seconds())
            dislikes = get_dislike_count(video['id'])

            video_info = {
                'playlist_id': playlist_id,
                'video_id': video['id'],
                'published_at': snippet['publishedAt'],
                'title': snippet['title'],
                'author_name': snippet['channelTitle'],
                'author_handle': channel_map.get(snippet['channelId'], ''),
                'author_user_id': snippet['channelId'],
                'description': snippet.get('description', ''),
                'duration_seconds': duration,
                'view_count': int(stats.get('viewCount', 0)),
                'like_count': int(stats.get('likeCount', 0)),
                'dislike_count': dislikes,
                'position': positions[i]
            }

            save_json(video, f"{videos_path}/{video['id']}.json")
            videos_info.append(video_info)

        next_page_token = playlist_response.get('nextPageToken')
        if not next_page_token:
            break

    save_json(all_playlist_items, f"{playlist_path}/{playlist_id}.json")
    return videos_info

# ========== FLASK ROUTE ==========

@app.route("/feeds/mobile/api/playlists/<playlist_id>")
def playlist_route(playlist_id):
    oauth_token = request.args.get('oauth_token')
    base_url = request.host_url.rstrip('/') + '/'
    
    xml_file_path = f"./assets/cache/users/playlists/{playlist_id}.xml"
    json_file_path = f"./assets/cache/users/playlists/{playlist_id}.json"

    if oauth_token:
        # 🔄 Fetch fresh data from API using token
        try:
            videos_info = get_playlist_videos_details(oauth_token, playlist_id)
            xml_content = build_playlist_xml(videos_info, base_url)

            with open(xml_file_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            return Response(xml_content, mimetype='application/xml')
        except Exception as e:
            return abort(500, f"Failed to fetch and cache playlist: {e}")
    else:
        # 🔁 No token provided — serve from cache if possible
        if file_exists(xml_file_path):
            # ✅ Use existing XML file
            return Response(load_text_file(xml_file_path), mimetype='application/xml')
        elif file_exists(json_file_path):
            try:
                # 🔁 Rebuild XML from cached JSON
                with open(json_file_path, 'r', encoding='utf-8') as jf:
                    cached_items = json.load(jf)

                videos_info = []
                for item in cached_items:
                    snippet = item.get('snippet', {})
                    content = item.get('contentDetails', {})
                    video_id = content.get('videoId')
                    position = snippet.get('position', 0)

                    video_json_path = f"./assets/cache/users/playlists/videos/{video_id}.json"
                    if not file_exists(video_json_path):
                        continue

                    with open(video_json_path, 'r', encoding='utf-8') as vf:
                        video = json.load(vf)

                    stats = video.get('statistics', {})
                    snippet_v = video.get('snippet', {})
                    content_v = video.get('contentDetails', {})

                    try:
                        duration = int(isodate.parse_duration(content_v['duration']).total_seconds())
                    except:
                        duration = 0

                    dislike_path = f"./assets/cache/dislike/{video_id}.json"
                    dislike_count = 0
                    if file_exists(dislike_path):
                        with open(dislike_path, 'r', encoding='utf-8') as df:
                            dislike_data = json.load(df)
                            dislike_count = dislike_data.get('dislikes', 0)

                    videos_info.append({
                        'playlist_id': playlist_id,
                        'video_id': video_id,
                        'published_at': snippet_v.get('publishedAt'),
                        'title': snippet_v.get('title'),
                        'author_name': snippet_v.get('channelTitle'),
                        'author_handle': '',  # No handle from cache
                        'author_user_id': snippet_v.get('channelId'),
                        'description': snippet_v.get('description', ''),
                        'duration_seconds': duration,
                        'view_count': int(stats.get('viewCount', 0)),
                        'like_count': int(stats.get('likeCount', 0)),
                        'dislike_count': dislike_count,
                        'position': position
                    })

                xml_content = build_playlist_xml(videos_info, base_url)

                with open(xml_file_path, 'w', encoding='utf-8') as f:
                    f.write(xml_content)

                return Response(xml_content, mimetype='application/xml')

            except Exception as e:
                return abort(500, f"Failed to rebuild XML from cache: {e}")
        else:
            return abort(400, "Missing oauth_token and no cached data available")

@app.route("/feeds/api/videos/<video_id>")
def get_video_xml(video_id):
    baseurl = request.host
    cache_path = os.path.join(CACHE_DIR, f"{video_id}.json")

    # Load from cache or fetch from YouTubei
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        yt_url = "https://www.youtube.com/youtubei/v1/player"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Youtube-Client-Name": "1",
            "X-Youtube-Client-Version": "2.20201021.03.00"
        }
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20201021.03.00"
                }
            },
            "videoId": video_id
        }
        r = requests.post(yt_url, headers=headers, data=json.dumps(payload))
        data = r.json()
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Extract metadata
    title = data.get("videoDetails", {}).get("title", "")
    description = data.get("videoDetails", {}).get("shortDescription", "")
    author = data.get("videoDetails", {}).get("author", "")
    view_count = data.get("videoDetails", {}).get("viewCount", "0")
    duration = data.get("videoDetails", {}).get("lengthSeconds", "0")
    publish_date = data.get("microformat", {}).get("playerMicroformatRenderer", {}).get("publishDate", "")
    like_count = data.get("videoDetails", {}).get("likeCount", "0")
    dislike_count = data.get("videoDetails", {}).get("dislikeCount", "0")
    # Attempt to extract both date and upload time if possible
    upload_date = data.get("microformat", {}).get("playerMicroformatRenderer", {}).get("uploadDate", "")
    publish_time_str = data.get("microformat", {}).get("playerMicroformatRenderer", {}).get("publishDate", "")
    title_esc = escape(title)
    description_esc = escape(description)
    author_esc = escape(author)
    view_count_esc = escape(view_count)
    duration_esc = escape(duration)


    # Combine with a default time if no time is given
    if publish_time_str:
        # Fallback: assume noon UTC if time not provided
        try:
            published_dt = datetime.strptime(publish_time_str, "%Y-%m-%d").replace(hour=12, minute=0, second=0, tzinfo=timezone.utc)
        except ValueError:
            published_dt = datetime.now(timezone.utc)
    else:
        published_dt = datetime.now(timezone.utc)

    # Format as RFC3339 (ISO 8601)
    published_time = published_dt.isoformat().replace("+00:00", "Z")

# Use escaped variables inside the XML string:
    xmlcontent = f"""<?xml version='1.0' encoding='UTF-8'?>
    <entry>
        <id>http://{baseurl}/feeds/api/videos/{video_id}</id>
        <youTubeId id='{video_id}'>{video_id}</youTubeId>
        <published>{published_time}</published>
        <updated>{published_time}</updated>
        <category scheme="http://gdata.youtube.com/schemas/2007/categories.cat" label="People &amp; Blogs" term="People &amp; Blogs">People &amp; Blogs</category>
        <title type='text'>{title_esc}</title>
        <content type='text'>{description_esc}</content>
        <link rel="http://gdata.youtube.com/schemas/2007#video.related" href="http://{baseurl}/feeds/api/videos/{video_id}/related"/>
        <author>
            <name>{author_esc}</name>
            <uri>http://{baseurl}/feeds/api/users/{author_esc}</uri>
        </author>
        <gd:comments>
            <gd:feedLink href='http://{baseurl}/feeds/api/videos/{video_id}/comments' countHint='530'/>
        </gd:comments>
        <media:group>
            <media:category label='People &amp; Blogs' scheme='http://gdata.youtube.com/schemas/2007/categories.cat'>People &amp; Blogs</media:category>
            <media:content url='http://{baseurl}/channel_fh264_getvideo?v={video_id}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='3'/>
            <media:content url='http://{baseurl}/get_480?video_id={video_id}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='14'/>
            <media:description type='plain'>{description_esc}</media:description>
            <media:keywords>-</media:keywords>
            <media:player url='http://www.youtube.com/watch?v={video_id}'/>
            <media:thumbnail yt:name='hqdefault' url='http://i.ytimg.com/vi/{video_id}/hqdefault.jpg' height='240' width='320' time='00:00:00'/>
            <media:thumbnail yt:name='poster' url='http://i.ytimg.com/vi/{video_id}/0.jpg' height='240' width='320' time='00:00:00'/>
            <media:thumbnail yt:name='default' url='http://i.ytimg.com/vi/{video_id}/0.jpg' height='240' width='320' time='00:00:00'/>
            <yt:duration seconds='{duration_esc}'/>
            <yt:videoid id='{video_id}'>{video_id}</yt:videoid>
            <youTubeId id='{video_id}'>{video_id}</youTubeId>
            <media:credit role='uploader' name='{author_esc}'>{author_esc}</media:credit>
        </media:group>
        <gd:rating average='5' max='5' min='1' numRaters='4' rel='http://schemas.google.com/g/2005#overall'/>
        <yt:statistics favoriteCount="17" viewCount="{view_count_esc}"/>
        <yt:rating numLikes="153" numDislikes="16"/>
    </entry>"""

    return Response(xmlcontent, mimetype="application/xml")


class GetVideoInfoWii:
    WII_GET_VIDEO_INFO = "./assets/cache/videoinfo"

    def build(self, videoId):
        os.makedirs(self.WII_GET_VIDEO_INFO, exist_ok=True)
        cache_path = os.path.join(self.WII_GET_VIDEO_INFO, f"{videoId}.json")

        # Try loading from cache
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        else:
            # Fetch from API
            streamUrl = f"https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8&videoId={videoId}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            payload = {
                "context": {
                    "client": {
                        "hl": "en",
                        "gl": "US",
                        "clientName": "WEB",
                        "clientVersion": "2.20210714.01.00"
                    }
                },
                "videoId": videoId,
                "params": ""
            }

            response = requests.post(streamUrl, json=payload, headers=headers)
            if response.status_code != 200:
                return f"Error retrieving video info: {response.status_code}", response.status_code
            
            json_data = response.json()

            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f)

        try:
            title = json_data['videoDetails']['title']
            length_seconds = json_data['videoDetails']['lengthSeconds']
            author = json_data['videoDetails']['author']
        except KeyError as e:
            return f"Missing key: {e}", 400

        fmtList = "43/854x480/9/0/115"
        fmtStreamMap = f"43|"
        fmtMap = "43/0/7/0/0"
        thumbnailUrl = f"http://i.ytimg.com/vi/{videoId}/mqdefault.jpg"
        
        response_str = (
            f"status=ok&"
            f"length_seconds={length_seconds}&"
            f"keywords=a&"
            f"vq=None&"
            f"muted=0&"
            f"avg_rating=5.0&"
            f"thumbnailUrl={thumbnailUrl}&"
            f"allow_ratings=1&"
            f"hl=en&"
            f"ftoken=&"
            f"allow_embed=1&"
            f"fmtMap={fmtMap}&"
            f"fmt_url_map={fmtStreamMap}&"
            f"token=null&"
            f"plid=null&"
            f"track_embed=0&"
            f"author={author}&"
            f"title={title}&"
            f"videoId={videoId}&"
            f"fmtList={fmtList}&"
            f"fmtStreamMap={fmtStreamMap.split()[0]}"
        )
        return Response(response_str, content_type='text/plain')

	
@app.route('/get_video_info', methods=['GET'])
def get_video_info():
    video_id = request.args.get('video_id')
    if not video_id:
        return jsonify({"error": "Missing video_id parameter"}), 400

    video_info = GetVideoInfoWii().build(video_id)
    return video_info  # Ensure this returns a valid response

# Ensure 'assets' folder exists
if not os.path.exists("assets"):
    os.makedirs("assets")

# Ensure the assets folder exists
ASSETS_FOLDER = 'assets'
os.makedirs(ASSETS_FOLDER, exist_ok=True)

def get_video_orientation(file_path):
    """Checks if a video is vertical (height > width)"""
    probe_cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height', '-of', 'json', file_path
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    width = data['streams'][0]['width']
    height = data['streams'][0]['height']
    return "vertical" if height > width else "standard"

@app.route('/get_webm', methods=['GET'])
def get_video():
    video_id = request.args.get('video_id')
    if not video_id:
        return "Missing video_id parameter", 400

    file_path = os.path.join(ASSETS_FOLDER, f"{video_id}.mp4")
    processed_file = os.path.join(ASSETS_FOLDER, f"{video_id}.webm")

    if os.path.exists(processed_file):
        return send_file(processed_file, as_attachment=True)

    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        stream = yt.streams.get_highest_resolution()
        stream.download(output_path=ASSETS_FOLDER, filename=f"{video_id}.mp4")
    except Exception as e:
        return f"Error downloading video: {str(e)}", 500

    if not os.path.exists(file_path):
        return "Download failed, file not found", 500

    # Detect orientation
    orientation = get_video_orientation(file_path)

    # Apply correct FFmpeg processing
    if orientation == "vertical":  # Convert vertical videos properly
        ffmpeg_cmd = [
            'ffmpeg', '-i', file_path,
            '-vf', 'scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2',
            '-c:v', 'libvpx', '-b:v', '300k', '-cpu-used', '8',
            '-pix_fmt', 'yuv420p', '-c:a', 'libvorbis', '-b:a', '128k',
            '-r', '30', '-g', '30', processed_file
        ]
    else:  # Keep standard videos unchanged
        ffmpeg_cmd = [
            'ffmpeg', '-i', file_path, '-c:v', 'libvpx', '-b:v', '300k',
            '-cpu-used', '8', '-pix_fmt', 'yuv420p', '-c:a', 'libvorbis', '-b:a', '128k',
            '-r', '30', '-g', '30', processed_file
        ]

    subprocess.run(ffmpeg_cmd)

    return send_file(processed_file, as_attachment=True) if os.path.exists(processed_file) else "Processing failed", 500


SUBSCRIPTIONS_CACHE_PATH = "./assets/cache/users/subscriptions.xml"
os.makedirs(os.path.dirname(SUBSCRIPTIONS_CACHE_PATH), exist_ok=True)

def escape_xml(text):
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))

def build_xml(subscriptions, base_url, oauth_token):
    xml_template = f"""<?xml version='1.0' encoding='UTF-8'?>
<feed>
{{channels}}
</feed>
"""

    channel_template = """<entry>
    <category scheme='http://gdata.youtube.com/schemas/2007/subscriptiontypes.cat' term='channel'/>
    <content type='application/atom+xml;type=feed' src='http://{base_url}/feeds/api/users/{channel_id}/videos'/>
    <link rel='edit' href='http://{base_url}/edit'/>
    <yt:username>{username}</yt:username>
    <y9id>{channel_id}</y9id>
    <yt:channelId>{channel_id}</yt:channelId>
</entry>"""

    channel_entries = []
    for item in subscriptions:
        snippet = item.get("snippet", {})
        resource = snippet.get("resourceId", {})

        if snippet and resource:
            channel_id = resource.get("channelId", "")
            
            # Fetch channel details using oauth_token to get the custom URL (handle)
            if channel_id:
                # YouTube API request to get channel info using oauth_token in headers
                channel_url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}"
                headers = {
                    "Authorization": f"Bearer {oauth_token}"
                }
                response = requests.get(channel_url, headers=headers)
                channel_data = response.json()
                
                # Extract the custom URL (channel handle) from the response
                username = "Unknown"
                if 'items' in channel_data and len(channel_data['items']) > 0:
                    custom_url = channel_data['items'][0].get('snippet', {}).get('customUrl', '')
                    if custom_url:
                        username = custom_url  # Use the custom URL as the channel handle
                    else:
                        # Fallback to channelTitle if no custom URL is available
                        username = channel_data['items'][0].get('snippet', {}).get('title', '')
            
            # Format the username without the @ symbol
            entry = channel_template.format(
                username=escape_xml(username),  # This is the channel handle (without @)
                channel_id=channel_id,
                base_url=base_url
            )

            channel_entries.append(entry)

    return xml_template.format(channels="\n".join(channel_entries))


SUBSCRIPTIONS_CACHE_PATH = "./assets/cache/users/subscriptions.xml"
CHANNELS_CACHE_PATH = "./assets/cache/users/subscriptionsinfos"
os.makedirs(os.path.dirname(SUBSCRIPTIONS_CACHE_PATH), exist_ok=True)
os.makedirs(CHANNELS_CACHE_PATH, exist_ok=True)

CACHE_LIFETIME = 24 * 60 * 60  # 24 hours in seconds

def escape_xml(text):
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))

def get_channel_info(channel_id, oauth_token):
    # Path to save the channel info
    channel_cache_path = os.path.join(CHANNELS_CACHE_PATH, f"{channel_id}.json")

    # Check if the cache file exists and if it's older than 24 hours
    if os.path.isfile(channel_cache_path):
        file_creation_time = os.path.getmtime(channel_cache_path)
        if time.time() - file_creation_time < CACHE_LIFETIME:
            # Cache is valid, read and return the cached data
            with open(channel_cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

    # Cache is outdated or does not exist, fetch the data from YouTube API
    channel_url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}"
    headers = {
        "Authorization": f"Bearer {oauth_token}"
    }
    response = requests.get(channel_url, headers=headers)
    channel_data = response.json()

    # Extract the custom URL (channel handle) or fallback to channel title
    username = "Unknown"
    if 'items' in channel_data and len(channel_data['items']) > 0:
        custom_url = channel_data['items'][0].get('snippet', {}).get('customUrl', '')
        if custom_url:
            username = custom_url  # Use the custom URL as the channel handle
        else:
            # Fallback to channelTitle if no custom URL is available
            username = channel_data['items'][0].get('snippet', {}).get('title', '')

    # Save the channel data to cache for later use
    with open(channel_cache_path, "w", encoding="utf-8") as f:
        json.dump(channel_data, f, ensure_ascii=False, indent=4)

    return channel_data

def build_xml(subscriptions, base_url, oauth_token):
    xml_template = f"""<?xml version='1.0' encoding='UTF-8'?>
<feed>
{{channels}}
</feed>
"""

    channel_template = """<entry>
    <category scheme='http://gdata.youtube.com/schemas/2007/subscriptiontypes.cat' term='channel'/>
    <content type='application/atom+xml;type=feed' src='http://{base_url}/feeds/api/users/{channel_id}/videos'/>
    <link rel='edit' href='http://{base_url}/edit'/>
    <yt:username>{username}</yt:username>
    <y9id>{channel_id}</y9id>
    <yt:channelId>{channel_id}</yt:channelId>
</entry>"""

    channel_entries = []
    for item in subscriptions:
        snippet = item.get("snippet", {})
        resource = snippet.get("resourceId", {})

        if snippet and resource:
            channel_id = resource.get("channelId", "")
            
            # Fetch channel details using oauth_token
            if channel_id:
                channel_data = get_channel_info(channel_id, oauth_token)

                # Extract the username (channel handle) without '@' symbol
                username = "Unknown"
                if 'items' in channel_data and len(channel_data['items']) > 0:
                    custom_url = channel_data['items'][0].get('snippet', {}).get('customUrl', '')
                    if custom_url:
                        username = custom_url.lstrip('@')  # Remove '@' symbol
                    else:
                        # Fallback to channelTitle if no custom URL is available
                        username = channel_data['items'][0].get('snippet', {}).get('title', '')
            
            # Format the username without the @ symbol
            entry = channel_template.format(
                username=escape_xml(username),  # This is the channel handle (without @)
                channel_id=channel_id,
                base_url=base_url
            )

            channel_entries.append(entry)

    return xml_template.format(channels="\n".join(channel_entries))

@app.route("/feeds/api/users/default/subscriptions", methods=["GET"])
def subscriptions_xml():
    oauth_token = request.args.get("oauth_token")
    base_url = request.host
    MAX_RESULTS_TOTAL = 40

    if oauth_token:
        try:
            subscriptions = []
            next_page_token = None

            while True:
                url = f"https://www.googleapis.com/youtube/v3/subscriptions?part=snippet&mine=true&maxResults=20"
                headers = {
                    "Authorization": f"Bearer {oauth_token}"
                }
                if next_page_token:
                    url += f"&pageToken={next_page_token}"

                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                items = data.get("items", [])
                subscriptions.extend(items)

                # Stop if reached or exceeded max total
                if len(subscriptions) >= MAX_RESULTS_TOTAL:
                    subscriptions = subscriptions[:MAX_RESULTS_TOTAL]
                    break

                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    break

            xml_data = build_xml(subscriptions, base_url, oauth_token)

            # Cache XML for fallback
            with open(SUBSCRIPTIONS_CACHE_PATH, "w", encoding="utf-8") as f:
                f.write(xml_data)

            return Response(xml_data, mimetype="application/xml")

        except Exception as e:
            # Serve cached data if available
            if os.path.isfile(SUBSCRIPTIONS_CACHE_PATH):
                with open(SUBSCRIPTIONS_CACHE_PATH, "r", encoding="utf-8") as f:
                    cached_xml = f.read()
                return Response(cached_xml, mimetype="application/xml", status=200)
            else:
                return Response(f"<error>{escape_xml(str(e))}</error>", mimetype="application/xml", status=500)

    else:
        # No token: serve cached or error
        if os.path.isfile(SUBSCRIPTIONS_CACHE_PATH):
            with open(SUBSCRIPTIONS_CACHE_PATH, "r", encoding="utf-8") as f:
                cached_xml = f.read()

            # Update base_url in cached XML if present or add if missing
            cached_xml = re.sub(r'base_url="[^"]*"', f'base_url="{base_url}"', cached_xml)
            if 'base_url="' not in cached_xml:
                cached_xml = cached_xml.replace('<subscriptions>', f'<subscriptions base_url="{base_url}">')

            return Response(cached_xml, mimetype="application/xml")
        else:
            return Response("<error>No cached data available and no oauth_token provided.</error>",
                            mimetype="application/xml", status=400)



# Register namespaces globally for proper XML prefix handling
ET.register_namespace("media", "http://search.yahoo.com/mrss/")
ET.register_namespace("yt", "http://gdata.youtube.com/schemas/2007")
ET.register_namespace("gd", "http://schemas.google.com/g/2005")

DISLIKE_CACHE_PATH = "./assets/cache/dislike"
CACHE_TTL_SECONDS = 3600  # 1 hour


def get_channel_uploads(channel_id, oauth_token):
    creds = Credentials(token=oauth_token)
    service = build("youtube", "v3", credentials=creds)

    # Get channel name
    channel_response = service.channels().list(
        part="snippet",
        id=channel_id
    ).execute()

    items = channel_response.get("items", [])
    if not items:
        return [], "Unknown Channel"

    channel_name = items[0]["snippet"]["title"]

    # Get uploads playlist ID
    uploads_playlist_id = service.channels().list(
        part="contentDetails",
        id=channel_id
    ).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Get videos from playlist
    playlist_response = service.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=uploads_playlist_id,
        maxResults=25
    ).execute()

    videos = []
    video_ids = []

    for item in playlist_response.get("items", []):
        video_id = item["contentDetails"]["videoId"]
        snippet = item["snippet"]
        video_ids.append(video_id)

        videos.append({
            "id": f"yt:video:{video_id}",
            "videoid": video_id,
            "published": snippet["publishedAt"],
            "updated": snippet["publishedAt"],
            "title": snippet["title"],
            "description": snippet.get("description", ""),
            "uploader": channel_name,
            "duration": 0,
            "view_count": "0",
            "like_count": "0",
            "dislike_count": "0",
            "channel_id": channel_id,
        })

    # Get durations, stats, dislikes
    durations = get_video_durations(video_ids, oauth_token)
    stats = get_video_stats(video_ids, oauth_token)

    for video in videos:
        vid = video["videoid"]
        video["duration"] = durations.get(vid, 0)
        video["view_count"] = stats.get(vid, {}).get("viewCount", "0")
        video["like_count"] = stats.get(vid, {}).get("likeCount", "0")
        video["dislike_count"] = get_dislike_count(vid)

    return videos, channel_name


def get_video_durations(video_ids, oauth_token):
    creds = Credentials(token=oauth_token)
    service = build("youtube", "v3", credentials=creds)

    response = service.videos().list(
        part="contentDetails",
        id=",".join(video_ids)
    ).execute()

    durations = {}
    for item in response.get("items", []):
        video_id = item["id"]
        iso_duration = item["contentDetails"]["duration"]
        durations[video_id] = int(isodate.parse_duration(iso_duration).total_seconds())

    return durations


def get_video_stats(video_ids, oauth_token):
    creds = Credentials(token=oauth_token)
    service = build("youtube", "v3", credentials=creds)

    response = service.videos().list(
        part="statistics",
        id=",".join(video_ids)
    ).execute()

    stats = {}
    for item in response.get("items", []):
        video_id = item["id"]
        statistics = item.get("statistics", {})
        stats[video_id] = {
            "viewCount": statistics.get("viewCount", "0"),
            "likeCount": statistics.get("likeCount", "0")
        }

    return stats


def get_dislike_count(video_id):
    os.makedirs(DISLIKE_CACHE_PATH, exist_ok=True)
    cache_file = os.path.join(DISLIKE_CACHE_PATH, f"{video_id}.json")

    if os.path.exists(cache_file):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if datetime.now() - file_mtime < timedelta(seconds=CACHE_TTL_SECONDS):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return str(data.get("dislikes", "0"))
            except (json.JSONDecodeError, IOError):
                # Corrupted cache or file reading issue, ignore and fetch fresh
                pass

    try:
        url = f"https://returnyoutubedislikeapi.com/votes?videoId={video_id}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return str(data.get("dislikes", "0"))
    except requests.RequestException:
        # Network issue, timeout, etc.
        pass
    except (json.JSONDecodeError, IOError):
        # Issues reading/writing cache or parsing JSON from response
        pass

    return "0"
    
def create_xml_feed(videos, channel_id, channel_name, base_url):
    # Ensure no trailing slash
    base_url = base_url.rstrip("/")

    feed = ET.Element("feed", {
        "xmlns": "http://www.w3.org/2005/Atom",
        "xmlns:media": "http://search.yahoo.com/mrss/",
        "xmlns:yt": "http://gdata.youtube.com/schemas/2007",
        "xmlns:gd": "http://schemas.google.com/g/2005"
    })

    ET.SubElement(feed, "id").text = "http://gdata.youtube.com/feeds/api/channel/uploads"
    ET.SubElement(feed, "updated").text = videos[0]["published"] if videos else ""
    ET.SubElement(feed, "title").text = channel_name

    author = ET.SubElement(feed, "author")
    ET.SubElement(author, "name").text = channel_name
    ET.SubElement(author, "uri").text = f"http://www.youtube.com/channel/{channel_id}"

    for vid in videos:
        entry = ET.SubElement(feed, "entry")

        ET.SubElement(entry, "id").text = vid["id"]
        ET.SubElement(entry, "youTubeId", {"id": vid["videoid"]}).text = vid["videoid"]
        ET.SubElement(entry, "published").text = vid["published"]
        ET.SubElement(entry, "updated").text = vid["updated"]

        ET.SubElement(entry, "category", {
            "scheme": "http://gdata.youtube.com/schemas/2007/categories.cat",
            "label": "-",
            "term": "-"
        }).text = "-"

        ET.SubElement(entry, "title", {"type": "text"}).text = vid["title"]
        ET.SubElement(entry, "content", {"type": "text"}).text = vid["description"]

        ET.SubElement(entry, "link", {
            "rel": "http://gdata.youtube.com/schemas/2007#video.related",
            "href": f"{base_url}/feeds/api/videos/{vid['videoid']}/related"
        })

        author = ET.SubElement(entry, "author")
        ET.SubElement(author, "name").text = vid["uploader"]
        ET.SubElement(author, "uri").text = f"{base_url}/feeds/api/users/{vid['uploader']}"
        ET.SubElement(author, "yt:userId").text = f"EE{vid['channel_id']}"
        
        comments = ET.SubElement(entry, "gd:comments")
        ET.SubElement(comments, "gd:feedLink", {
            "href": f"{base_url}/feeds/api/videos/{vid['videoid']}/comments",
            "countHint": "530"
        })

        media_group = ET.SubElement(entry, "media:group")
        ET.SubElement(media_group, "media:category", {
            "label": "-",
            "scheme": "http://gdata.youtube.com/schemas/2007/categories.cat"
        }).text = "-"

        ET.SubElement(media_group, "media:content", {
            "url": f"{base_url}/channel_fh264_getvideo?v={vid['videoid']}",
            "type": "video/3gpp",
            "medium": "video",
            "expression": "full",
            "duration": str(vid["duration"]),
            "yt:format": "3"
        })

        ET.SubElement(media_group, "media:description", {"type": "plain"}).text = vid["description"]
        ET.SubElement(media_group, "media:keywords").text = "-"

        ET.SubElement(media_group, "media:player", {
            "url": f"http://www.youtube.com/watch?v={vid['videoid']}"
        })

        for thumbnail_type in ["hqdefault", "poster", "default"]:
            ET.SubElement(media_group, "media:thumbnail", {
                "yt:name": thumbnail_type,
                "url": f"http://i.ytimg.com/vi/{vid['videoid']}/{thumbnail_type}.jpg",
                "height": "240",
                "width": "320",
                "time": "00:00:00"
            })

        ET.SubElement(media_group, "yt:duration", {
            "seconds": str(vid["duration"])
        })
        ET.SubElement(media_group, "yt:videoid", {"id": vid["videoid"]}).text = vid["videoid"]
        ET.SubElement(media_group, "youTubeId", {"id": vid["videoid"]}).text = vid["videoid"]
        ET.SubElement(media_group, "yt:uploaderId").text = f"EE{vid['channel_id']}"


        ET.SubElement(media_group, "media:credit", {
            "role": "uploader",
            "scheme": "urn:youtube",
            "yt:display": channel_name,
            "yt:type": "partner"
        }).text = channel_id

        ET.SubElement(entry, "gd:rating", {
            "average": "5",
            "max": "5",
            "min": "1",
            "numRaters": "25",
            "rel": "http://schemas.google.com/g/2005#overall"
        })

        ET.SubElement(entry, "yt:statistics", {
            "favoriteCount": "0",
            "viewCount": vid.get("view_count", "0")
        })

        ET.SubElement(entry, "yt:rating", {
            "numLikes": vid.get("like_count", "0"),
            "numDislikes": vid.get("dislike_count", "0")
        })

    return ET.tostring(feed, encoding="utf-8").decode("utf-8")

@app.route('/feeds/viitube/users/<channel_id>/uploads')
def uploads(channel_id):
    oauth_token = request.args.get("oauth_token")
    if not oauth_token:
        return Response("<error>OAuth token is required</error>", status=400, mimetype="application/xml")

    if channel_id == "me":
        creds = Credentials(token=oauth_token)
        service = build("youtube", "v3", credentials=creds)
        response = service.channels().list(part="id", mine=True).execute()
        items = response.get("items", [])
        if not items:
            return Response("<error>Cannot retrieve channel ID from token</error>", status=400, mimetype="application/xml")
        channel_id = items[0]["id"]

    videos, channel_name = get_channel_uploads(channel_id, oauth_token)

    # Use request.url_root to get dynamic base URL
    base_url = request.url_root.rstrip("/")

    xml_response = create_xml_feed(videos, channel_id, channel_name, base_url)

    return Response(xml_response, mimetype="application/xml")

FAVORITES_CACHE_PATH = "./assets/cache/users/favorites.json"

# Helper to fetch dislike + view count from Return YouTube Dislike API
def get_dislike_and_views(video_id):
    try:
        resp = requests.get("https://returnyoutubedislikeapi.com/votes", params={'videoId': video_id})
        resp.raise_for_status()
        data = resp.json()
        return int(data.get('dislikes', 0)), int(data.get('viewCount', 0))
    except Exception:
        return 0, 0

# Fetch liked videos and return as XML string
def fetch_liked_videos_xml(oauth_token, base_url):
    creds = Credentials(token=oauth_token)
    youtube = build('youtube', 'v3', credentials=creds)

    # Step 1: Get playlistItems (liked videos)
    pl_response = youtube.playlistItems().list(
        part='snippet',
        playlistId='LL',
        maxResults=25
    ).execute()

    video_ids = [item['snippet']['resourceId']['videoId'] for item in pl_response.get('items', [])]
    if not video_ids:
        return "<?xml version=\"1.0\" encoding=\"UTF-8\"?><videos></videos>"

    # Step 2: Get video details
    vid_response = youtube.videos().list(
        part='snippet,contentDetails,statistics',
        id=','.join(video_ids)
    ).execute()

    xml_items = []
    for item in vid_response.get('items', []):
        sn = item['snippet']
        cd = item['contentDetails']
        stats = item.get('statistics', {})

        published_at = sn.get('publishedAt', '')
        date_only = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ").date()
        published = f"{date_only}T00:00:00"
        
        from xml.sax.saxutils import escape

        author_name = sn.get('channelTitle', 'Unknown')
        escaped_author_name = escape(author_name, {"'": "&apos;", "\"": "&quot;"})
        duration_seconds = int(isodate.parse_duration(cd.get('duration')).total_seconds())
        like_count = int(stats.get('likeCount', 0))
        view_count = int(stats.get('viewCount', 0))
        dislike_count, _ = get_dislike_and_views(item['id'])

        xml_items.append(f"""<entry gd:etag='W/&quot;CUYDQ347eCp7I2A9XRdVGEs.&quot;'>
		<id>tag:youtube.com,2008:video:{item['id']}</id>
		<published>{published}</published>
		<updated>{published}</updated>
		<category scheme='http://schemas.google.com/g/2005#kind' term='{base_url}/schemas/2007#video'/>
		<category scheme='{base_url}/schemas/2007/categories.cat' term='News' label='News &amp; Politics'/>
		<title>{sn.get('title')}</title>
		<content type='application/x-shockwave-flash' src='http://www.youtube.com/v/{item['id']}?version=3&amp;f=user_uploads&amp;app=youtube_gdata'/>
		<link rel='alternate' type='text/html' href='http://www.youtube.com/watch?v={item['id']}&amp;feature=youtube_gdata'/>
		<link rel='{base_url}/schemas/2007#video.related' type='application/atom+xml' href='{base_url}/feeds/api/videos/{item['id']}/related?v=2'/>
		<link rel='{base_url}/schemas/2007#mobile' type='text/html' href='http://m.youtube.com/details?v={item['id']}'/>
		<link rel='{base_url}/schemas/2007#uploader' type='application/atom+xml' href='{base_url}/feeds/api/users/9yMWgQf2_xMhbdKPo7Ljrw?v=2'/>
		<link rel='self' type='application/atom+xml' href='{base_url}/feeds/api/users/19cachicha/uploads/{item['id']}?v=2'/>
		<author>
			<name>{sn.get('channelTitle')}</name>
			<uri>{base_url}/feeds/api/users/19cachicha</uri>
			<yt:userId>RR{sn.get('channelId')}</yt:userId>
		</author>
		<yt:accessControl action='comment' permission='allowed'/>
		<yt:accessControl action='commentVote' permission='allowed'/>
		<yt:accessControl action='videoRespond' permission='moderated'/>
		<yt:accessControl action='rate' permission='allowed'/>
		<yt:accessControl action='embed' permission='allowed'/>
		<yt:accessControl action='list' permission='allowed'/>
		<yt:accessControl action='autoPlay' permission='allowed'/>
		<yt:accessControl action='syndicate' permission='allowed'/>
		<gd:comments>
			<gd:feedLink rel='{base_url}/schemas/2007#comments' href='{base_url}/feeds/api/videos/{item['id']}/comments?v=2' countHint='24'/>
		</gd:comments>
		<media:group>
			<media:category label='News &amp; Politics' scheme='{base_url}/schemas/2007/categories.cat'>News</media:category>
			<media:content url='http://www.youtube.com/v/{item['id']}?version=3&amp;f=user_uploads&amp;app=youtube_gdata' type='application/x-shockwave-flash' medium='video' isDefault='true' expression='full' duration='2506' yt:format='5'/>
			<media:content url='rtsp://r5---sn-jc47eu7k.c.youtube.com/CigLENy73wIaHwm6igMVojTENRMYDSANFEgGUgx1c2VyX3VwbG9hZHMM/0/0/0/video.3gp' type='video/3gpp' medium='video' expression='full' duration='2506' yt:format='1'/>
			<media:content url='rtsp://r5---sn-jc47eu7k.c.youtube.com/CigLENy73wIaHwm6igMVojTENRMYESARFEgGUgx1c2VyX3VwbG9hZHMM/0/0/0/video.3gp' type='video/3gpp' medium='video' expression='full' duration='2506' yt:format='6'/>
			<media:credit role='uploader' scheme='urn:youtube' yt:display="{escaped_author_name}" yt:type='partner'>19cachicha</media:credit>
			<media:description type='plain'/>
			<media:keywords/>
			<media:license type='text/html' href='http://www.youtube.com/t/terms'>youtube</media:license>
			<media:player url='http://www.youtube.com/watch?v={item['id']}&amp;feature=youtube_gdata_player'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{item['id']}/default.jpg' height='90' width='120' time='00:20:53' yt:name='default'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{item['id']}/mqdefault.jpg' height='180' width='320' yt:name='mqdefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{item['id']}/hqdefault.jpg' height='360' width='480' yt:name='hqdefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{item['id']}/sddefault.jpg' height='480' width='640' yt:name='sddefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{item['id']}/1.jpg' height='90' width='120' time='00:10:26.500' yt:name='start'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{item['id']}/2.jpg' height='90' width='120' time='00:20:53' yt:name='middle'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{item['id']}/3.jpg' height='90' width='120' time='00:31:19.500' yt:name='end'/>
			<media:title type='plain'>{sn.get('title')}</media:title>
			<yt:duration seconds='{duration_seconds}'/>
			<yt:uploaded>{published}</yt:uploaded>
			<yt:uploaderId>EE{sn.get('channelId')}</yt:uploaderId>
			<yt:videoid>{item['id']}</yt:videoid>
		</media:group>
		<gd:rating average='4.151515' max='5' min='1' numRaters='99' rel='http://schemas.google.com/g/2005#overall'/>
		<yt:statistics favoriteCount='0' viewCount='{view_count}'/>
		<yt:rating numDislikes='{dislike_count}' numLikes='{like_count}'/>
	</entry>""".strip())

    # Wrap in XML root
    xml_output = f"""<?xml version='1.0' encoding='UTF-8'?>
<feed
	xmlns='http://www.w3.org/2005/Atom'
	xmlns:gd='http://schemas.google.com/g/2005'
	xmlns:yt='{base_url}/schemas/2007'
	xmlns:openSearch='http://a9.com/-/spec/opensearch/1.1/'
	xmlns:media='http://search.yahoo.com/mrss/' gd:etag='W/&quot;CEIMR384cSp7I2A9XRdUE0Q.&quot;'>
	<id>tag:youtube.com,2008:user:19cachicha:uploads</id>
	<updated>2014-12-01T00:09:46.139Z</updated>
	<category scheme='http://schemas.google.com/g/2005#kind' term='{base_url}/schemas/2007#video'/>
	<title>Uploads by {sn.get('channelTitle')}</title>
	<logo>http://www.gstatic.com/youtube/img/logo.png</logo>
	<link rel='related' type='application/atom+xml' href='{base_url}/feeds/api/users/19cachicha?v=2'/>
	<link rel='alternate' type='text/html' href='http://www.youtube.com/channel/UC9yMWgQf2_xMhbdKPo7Ljrw/videos'/>
	<link rel='hub' href='http://pubsubhubbub.appspot.com'/>
	<link rel='http://schemas.google.com/g/2005#feed' type='application/atom+xml' href='{base_url}/feeds/api/users/19cachicha/uploads?v=2'/>
	<link rel='http://schemas.google.com/g/2005#batch' type='application/atom+xml' href='{base_url}/feeds/api/users/19cachicha/uploads/batch?v=2'/>
	<link rel='self' type='application/atom+xml' href='{base_url}/feeds/api/users/19cachicha/uploads?start-index=1&amp;max-results=25&amp;v=2'/>
	<link rel='service' type='application/atomsvc+xml' href='{base_url}/feeds/api/users/19cachicha/uploads?alt=atom-service&amp;v=2'/>
	<link rel='next' type='application/atom+xml' href='{base_url}/feeds/api/users/19cachicha/uploads?start-index=26&amp;max-results=25&amp;v=2'/>
	<author>
		<name>{sn.get('channelTitle')}</name>
		<uri>{base_url}/feeds/api/users/19cachicha</uri>
		<yt:userId>9yMWgQf2_xMhbdKPo7Ljrw</yt:userId>
	</author>
	<generator version='2.1' uri='{base_url}'>YouTube data API</generator>
{chr(10).join(xml_items)}
</feed>"""

    # Also save to cache as JSON
    os.makedirs(os.path.dirname(FAVORITES_CACHE_PATH), exist_ok=True)
    with open(FAVORITES_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"xml": xml_output}, f, ensure_ascii=False, indent=2)

    return xml_output

@app.route("/feeds/api/users/default/favorites")
def favorites():
    oauth_token = request.args.get("oauth_token")
    base_url = request.host_url.strip("/")  # e.g., http://127.0.0.1:5000

    if oauth_token:
        try:
            xml_data = fetch_liked_videos_xml(oauth_token, base_url)
            return Response(xml_data, mimetype="application/xml")
        except Exception as e:
            return {"error": str(e)}, 500
    else:
        # No token — fallback to cache
        if os.path.exists(FAVORITES_CACHE_PATH):
            with open(FAVORITES_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Response(data.get("xml", ""), mimetype="application/xml")
        else:
            return Response("<videos></videos>", mimetype="application/xml")

CACHE_PATH = os.path.join(os.getcwd(), "assets", "cache", "users", "uploads.xml")



def get_channel_id_from_api(oauth_token):
    headers = {"Authorization": f"Bearer {oauth_token}"}
    response = requests.get("https://www.googleapis.com/youtube/v3/channels?part=id&mine=true", headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data["items"][0]["id"] if "items" in data else None
    return None

@app.route('/feeds/api/users/default/uploads')
def extract_channel_id_and_forward():
    oauth_token = request.args.get("oauth_token")

    # ✅ If no token, try to serve the cached file
    if not oauth_token:
        if os.path.exists(CACHE_PATH):
            return send_file(CACHE_PATH, mimetype="application/xml")
        else:
            return Response("<error>Cached file not found</error>", status=404, mimetype="application/xml")

    # ✅ Decode token to get channel_id, or fallback to API
    try:
        payload = jwt.decode(oauth_token, options={"verify_signature": False})
        channel_id = payload.get("channel_id")
    except Exception:
        channel_id = None

    if not channel_id:
        channel_id = get_channel_id_from_api(oauth_token)
        if not channel_id:
            return Response("<error>Failed to retrieve channel ID</error>", status=400, mimetype="application/xml")

    # ✅ Build internal URL
    query_params = request.args.to_dict()
    query_params["oauth_token"] = oauth_token  # Ensure it's present
    query_string = urlencode(query_params)
    internal_path = f"/feeds/viitube/users/{channel_id}/uploads"
    internal_url = urljoin(request.host_url, f"{internal_path}?{query_string}")

    try:
        # ✅ Make internal request
        resp = requests.get(internal_url)
        content = resp.content
        status_code = resp.status_code
        content_type = resp.headers.get("Content-Type", "application/xml")

        # ✅ Save to cache file
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "wb") as f:
            f.write(content)

        return Response(content, status=status_code, content_type=content_type)

    except requests.RequestException:
        return Response("<error>Internal fetch failed</error>", status=500, mimetype="application/xml")

    
WATCH_LATER_CACHE_PATH = "./assets/cache/watch_later.json"
CACHE_EXPIRATION = 5 * 3600  # 5 hours (in seconds)
YOUTUBEI_URL = "https://www.youtube.com/youtubei/v1/browse"

def fetch_watch_later(oauth_token):
    """Retrieve YouTube Watch Later list using OAuth authentication and save to cache."""
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "context": {
        "client": {
            "screenWidthPoints": 1912,
            "screenHeightPoints": 829,
            "utcOffsetMinutes": 120,
            "hl": "en",
            "gl": "US",
            "remoteHost": "2a01:cb08:6af:1000:88e6:55a2:5954:3a0d",
            "deviceMake": "Samsung",
            "deviceModel": "SmartTV",
            "visitorData": "CgtMMHJQTEJxSmxLQSjNrsfEBjInCgJGUhIhEh0SGwsMDg8QERITFBUWFxgZGhscHR4fICEiIyQlJiAy",
            "userAgent": "Mozilla/5.0 (SMART-TV; LINUX; Tizen 5.5) AppleWebKit/537.36 (KHTML, like Gecko) 69.0.3497.106.1/5.5 TV Safari/537.36,gzip(gfe)",
            "clientName": "TVHTML5",
            "clientVersion": "7.20250731.17.00",
            "osName": "Tizen",
            "osVersion": "5.5",
            "originalUrl": "https://www.youtube.com/tv",
            "theme": "CLASSIC",
            "platform": "TV",
            "clientFormFactor": "UNKNOWN_FORM_FACTOR",
            "webpSupport": False,
            "configInfo": {
                "appInstallData": "CM2ux8QGELvZzhwQgc3OHBDJ968FEJvXzxwQ0-GvBRCd0LAFEObJzxwQ2vfOHBCw188cEOCCgBMQioKAExC9tq4FELnZzhwQ_tjPHBDy2M8cEPSegBMQ79TPHBCZjbEFELjkzhwQ7dXPHBCYuc8cEL3QzxwQy5rOHBCZmLEFEParsAUQibDOHBC82c8cEKHXzxwQxcPPHBCvhs8cEN68zhwQt-r-EhCkiIATEJehgBMQvZmwBRDM364FEKmZgBMQlP6wBRDw4s4cEOLKzxwQvoqwBRDOrM8cEMXLzxwQ9svPHBCIh7AFEK7WzxwQhtnPHBCHrM4cEPyyzhwQ477PHBCsz88cEM61zxwQkdLPHBC7jYATKiRDQU1TRnhVVS1acS1EUHJpRWVfejdBdUJsUTB5b0t3RUF4MEg%3D",
            },
            "tvAppInfo": {
                "appQuality": "TV_APP_QUALITY_LIMITED_ANIMATION",
                "cobaltAppVersion": "69.0.3497.106.1",
                "voiceCapability": {
                    "hasSoftMicSupport": False,
                    "hasHardMicSupport": False,
                },
                "supportsNativeScrolling": False,
            },
            "timeZone": "Europe/Paris",
            "browserName": "TV Safari",
            "browserVersion": "537.36",
            "acceptHeader": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "deviceExperimentId": "ChxOelV6TlRBeU9EWTBOemMzT0RNMk9EUTBOZz09EM2ux8QGGKKZx8QG",
            "rolloutToken": "CMCMyfGO1dXP7AEQnN--qILzjgMY6N-dwp3zjgM%3D",
            "screenDensityFloat": 1,
        },
        "user": {
            "enableSafetyMode": False
        },
        "request": {
            "internalExperimentFlags": [],
            "consistencyTokenJars": []
        },
        "clickTracking": {
            "clickTrackingParams": "CNUCEOGWCxgBIhMI_qmM37XzjgMVC0z-BR350SZK"
        }
    },
    "browseId": "FEmy_youtube",
    "params": "cAc%3D",
    "mdxContext": {
        "mdxReceiverContext": {
            "mdxConnectedDevices": []
        }
    }
}

    response = requests.post(YOUTUBEI_URL, headers=headers, json=payload)

    if response.status_code == 200:
        watch_later_data = response.json()
        save_watch_later_cache(watch_later_data)
        return watch_later_data
    else:
        return None

def save_watch_later_cache(data):
    """Save Watch Later list to cache with timestamp."""
    os.makedirs(os.path.dirname(WATCH_LATER_CACHE_PATH), exist_ok=True)
    cache_content = {"timestamp": time.time(), "data": data}
    with open(WATCH_LATER_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache_content, f, indent=4)

def load_watch_later_cache(oauth_token):
    """Load cached Watch Later, checking expiration and refreshing if needed."""
    if os.path.exists(WATCH_LATER_CACHE_PATH):
        with open(WATCH_LATER_CACHE_PATH, "r", encoding="utf-8") as f:
            try:
                cache_content = json.load(f)
            except json.JSONDecodeError:
                return fetch_watch_later(oauth_token)

            if "timestamp" not in cache_content or "data" not in cache_content:
                return fetch_watch_later(oauth_token)

            if time.time() - cache_content["timestamp"] > CACHE_EXPIRATION:
                return fetch_watch_later(oauth_token)

            return cache_content["data"]
    
    return fetch_watch_later(oauth_token)

def extract_watch_later_video_ids(watch_later_data):
    """Extract unique video IDs ordered by most recent addition to Watch Later."""
    video_entries = set()

    def recursive_search(data):
        """Recursively search for video IDs."""
        if isinstance(data, dict):
            if "videoId" in data:
                video_entries.add(data["videoId"])
            for value in data.values():
                recursive_search(value)
        elif isinstance(data, list):
            for item in data:
                recursive_search(item)

    recursive_search(watch_later_data)
    return list(video_entries)

def fetch_watch_later_video_details(video_ids, oauth_token):
    """Retrieve video details using YouTube API v3 with OAuth token."""
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id={','.join(video_ids)}"
    headers = {"Authorization": f"Bearer {oauth_token}"}

    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None


@app.route('/feeds/api/users/default/watch_later', methods=['GET'])
def get_watch_later_xml():
    """API endpoint returning ordered Watch Later list with full metadata."""
    oauth_token = request.args.get('oauth_token')
    if not oauth_token:
        return Response('<error>Missing OAuth token</error>', mimetype='application/xml')

    watch_later_data = load_watch_later_cache(oauth_token)
    if not watch_later_data:
        return Response('<error>Failed to retrieve Watch Later list</error>', mimetype='application/xml')

    video_ids = extract_watch_later_video_ids(watch_later_data)
    if not video_ids:
        return Response('<error>No Watch Later videos found</error>', mimetype='application/xml')

    video_details = fetch_watch_later_video_details(video_ids, oauth_token)
    if not video_details:
        return Response('<error>Failed to retrieve video details</error>', mimetype='application/xml')

    # Generate XML response
    xml_string = '<?xml version="1.0" encoding="UTF-8"?><feed>'
    for item in video_details.get("items", []):
        video_id = item["id"]
        title = item["snippet"]["title"]
        author_name = item["snippet"]["channelTitle"]
        uploader_id = item["snippet"]["channelId"]
        thumbnail_url = item["snippet"]["thumbnails"]["medium"]["url"]
        published_date = item["snippet"].get("publishedAt", "null")
        view_count = item["statistics"].get("viewCount", "0")
        
        # Convert duration to seconds
        duration_iso = item.get("contentDetails", {}).get("duration", "PT0S")
        duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())

        xml_string += f'''
        <entry>
            <id>http://localhost:5000/api/videos/{video_id}</id>
            <published>{published_date}</published>
            <title type="text">{title}</title>
            <link rel="alternate" href="http://localhost:5000/api/videos/{video_id}/related"/>
            <author>
                <name>{author_name}</name>
                <uri>https://www.youtube.com/channel/{uploader_id}</uri>
                <yt:userId>EE{uploader_id}</yt:userId>
            </author>
            <media:group>
                <media:thumbnail url="http://i.ytimg.com/vi/{video_id}/mqdefault.jpg" height="240" width="320"/>
                <yt:duration seconds="{duration_seconds}"/>
                <yt:videoid id="{video_id}">{video_id}</yt:videoid>
                <media:credit role="uploader" name="{author_name}">{author_name}</media:credit>
                <yt:uploaderId>EE{uploader_id}</yt:uploaderId>
            </media:group>
            <yt:statistics favoriteCount="0" viewCount="{view_count}"/>
        </entry>'''
    
    xml_string += '</feed>'
    return Response(xml_string, mimetype='application/xml')
    
VIITUBE_SEARCH_DIR = "./assets/cache/search"
VIITUBE_VIDEO_CACHE_DIR = "./assets/cache/videoinfo"
YOUTUBE_SEARCH_DISLIKE_API = "https://returnyoutubedislikeapi.com/votes?videoId="

os.makedirs(VIITUBE_SEARCH_DIR, exist_ok=True)
os.makedirs(VIITUBE_VIDEO_CACHE_DIR, exist_ok=True)

YOUTUBEI_SEARCH_QUERY_LINK = "https://www.youtube.com/youtubei/v1/search?key=YOUR_API_KEY"
YOUTUBEI_VIDEOMETA_URL = "https://www.youtube.com/youtubei/v1/player?key=YOUR_API_KEY"

def cache_path(cache_dir, key):
    safe_key = "".join(c if c.isalnum() else "_" for c in key)
    return os.path.join(cache_dir, f"{safe_key}.json")

def is_cache_valid(path, max_age_seconds=48*3600):
    if not os.path.exists(path):
        return False

    abs_video_dir = os.path.abspath(VIITUBE_VIDEO_CACHE_DIR)
    abs_path = os.path.abspath(path)

    if abs_path.startswith(abs_video_dir):
        return True  # never expire video cache

    return (time.time() - os.path.getmtime(path)) < max_age_seconds


def save_cache(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_cache(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        os.remove(path)  # delete broken file
        return None
    except Exception as e:
        return None


def request_youtube_search(query, limit=20):
    cache_file = cache_path(VIITUBE_SEARCH_DIR, query)
    cached = load_cache(cache_file)
    if cached:
        return cached
    # proceed with API request if cache is missing or corrupted...

    
    payload = {
        "context": {
            "client": {
                "hl": "en",
                "clientName": "WEB",
                "clientVersion": "2.20230816.00.00"
            }
        },
        "query": query,
        "params": "EgIQAQ%3D%3D",  # param for videos only
        "pageSize": limit
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    resp = requests.post(YOUTUBEI_SEARCH_QUERY_LINK, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    save_cache(cache_file, data)
    return data

def request_youtube_player(video_id):
    cache_file = cache_path(VIITUBE_VIDEO_CACHE_DIR, video_id)
    cached = load_cache(cache_file)
    if cached:
        return cached
    # proceed with API request if cache is missing or corrupted...

    
    payload = {
        "context": {
            "client": {
                "hl": "en",
                "clientName": "WEB",
                "clientVersion": "2.20230816.00.00"
            }
        },
        "videoId": video_id
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    resp = requests.post(YOUTUBEI_VIDEOMETA_URL, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    save_cache(cache_file, data)
    return data

def get_dislike_info(video_id):
    try:
        resp = requests.get(YOUTUBE_SEARCH_DISLIKE_API + video_id, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"likes": 0, "dislikes": 0}

def parse_upload_date(date_str):
    try:
        dt = parser.isoparse(date_str)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None

def enrich_video_data(video):
    video_id = video.get("video_id") or video.get("externalVideoId") or video.get("videoId")
    if not video_id:
        return None
    info = request_youtube_player(video_id)
    rtd_info = get_dislike_info(video_id)
    try:
        details = info.get("videoDetails", {})
        microformat = info.get("microformat", {}).get("playerMicroformatRenderer", {})

        video["description"] = details.get("shortDescription", "")
        video["duration_seconds"] = int(details.get("lengthSeconds", 0))
        video["likes"] = int(rtd_info.get("likes", 0))
        video["dislikes"] = int(rtd_info.get("dislikes", 0))
        video["view_count"] = int(details.get("viewCount", 0))

        upload_date = None
        for d in [
            microformat.get("uploadDate"),
            microformat.get("publishDate"),
            details.get("uploadDate"),
            details.get("publishDate")
        ]:
            if d:
                parsed = parse_upload_date(d)
                if parsed:
                    upload_date = parsed
                    break
        if upload_date:
            video["upload_date"] = upload_date

        owner_profile_url = microformat.get("ownerProfileUrl", "")
        channel_handle = ""
        if owner_profile_url and "/@" in owner_profile_url:
            channel_handle = owner_profile_url.split("/@")[-1]
        video["channel_handle"] = channel_handle

        video["channel_name"] = microformat.get("ownerChannelName", "") or details.get("author", "")
        video["channel_id"] = microformat.get("externalChannelId", "") or details.get("channelId", "")
        video["view_count"] = int(details.get("viewCount", 0))

    except Exception:
        pass

    return video



def build_xml_response(videos, baseurl):
    def esc(text):
        return html.escape(text or "", quote=True)
    
    baseurl_escaped = esc(baseurl)
    items_xml = []
    
    for v in videos:
        video_id = v.get("video_id") or v.get("externalVideoId") or v.get("videoId", "")
        title = esc(v.get("title", ""))
        channel_name = esc(v.get("channel_name", ""))
        channel_handle = esc(v.get("channel_handle", ""))
        description = esc(v.get("description", ""))
        likes = v.get("likes", 0)
        dislikes = v.get("dislikes", 0)
        duration = v.get("duration_seconds", 0)
        upload_date = v.get("upload_date")
        publish_date_tag = f"<published>{esc(upload_date)}.000Z</published>" if upload_date else ""
        updated_date_tag = f"<updated>{esc(upload_date)}.000Z</updated>" if upload_date else ""
        ytpublish_date_tag = f"<yt:uploaded>{esc(upload_date)}.000Z</yt:uploaded>" if upload_date else ""
        canonical_url = esc(v.get("canonicalUrl", f"https://www.youtube.com/watch?v={video_id}"))
        channel_id = esc(v.get("channel_id", ""))
        view_count = v.get("view_count", 0)

        item_xml = f"""	<entry gd:etag='W/&quot;CUYDQ347eCp7I2A9XRdVGEs.&quot;'>
		<id>tag:youtube.com,2008:video:{video_id}</id>
        {publish_date_tag}
        {updated_date_tag}
		<category scheme='http://schemas.google.com/g/2005#kind' term='{baseurl_escaped}/schemas/2007#video'/>
		<category scheme='{baseurl_escaped}/schemas/2007/categories.cat' term='News' label='News &amp; Politics'/>
		<title>{title}</title>
		<content type='application/x-shockwave-flash' src='http://www.youtube.com/v/{video_id}?version=3&amp;f=user_uploads&amp;app=youtube_gdata'/>
		<link rel='alternate' type='text/html' href='http://www.youtube.com/watch?v={video_id}&amp;feature=youtube_gdata'/>
        <link rel='http://gdata.youtube.com/schemas/2007#video.related' type='application/atom+xml' href='{baseurl_escaped}/feeds/api/videos/{video_id}/related'/>
        <link rel='http://gdata.youtube.com/schemas/2007#video.captionTracks' type='application/xml' href='{baseurl_escaped}/timedtext/{video_id}/related'/>
        <link rel="http://gdata.youtube.com/schemas/2007#video.related" href="{baseurl_escaped}/feeds/api/videos/{video_id}/related"/>
		<link rel='{baseurl_escaped}/schemas/2007#mobile' type='text/html' href='http://m.youtube.com/details?v={video_id}'/>
		<link rel='{baseurl_escaped}/schemas/2007#uploader' type='applicatio0tom+xml' href='{baseurl_escaped}/feeds/api/users/{channel_id}?v=2'/>
		<link rel='self' type='applicatio0tom+xml' href='{baseurl_escaped}/feeds/api/users/{channel_id}/uploads/{video_id}?v=2'/>
		<author>
			<name>{channel_name}</name>
			<uri>{baseurl_escaped}/feeds/api/users/{channel_id}</uri>
			<yt:userId>EE{channel_id}</yt:userId>
		</author>
		<yt:accessControl action='comment' permission='allowed'/>
		<yt:accessControl action='commentVote' permission='allowed'/>
		<yt:accessControl action='videoRespond' permission='moderated'/>
		<yt:accessControl action='rate' permission='allowed'/>
		<yt:accessControl action='embed' permission='allowed'/>
		<yt:accessControl action='list' permission='allowed'/>
		<yt:accessControl action='autoPlay' permission='allowed'/>
		<yt:accessControl action='syndicate' permission='allowed'/>
		<gd:comments>
			<gd:feedLink rel='{baseurl_escaped}/schemas/2007#comments' href='{baseurl_escaped}/feeds/api/videos/{video_id}/comments?v=2' countHint='24'/>
		</gd:comments>
		<media:group>
			<media:category label='News &amp; Politics' scheme='{baseurl_escaped}/schemas/2007/categories.cat'>News</media:category>
			<media:content url='http://www.youtube.com/v/{video_id}?version=3&amp;f=user_uploads&amp;app=youtube_gdata' type='application/x-shockwave-flash' medium='video' isDefault='true' expression='full' duration='2506' yt:format='5'/>
            <media:content url='{baseurl_escaped}/channel_fh264_getvideo?v={video_id}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='3'/><media:content url='{baseurl_escaped}/get_480?video_id={video_id}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='14'/><media:content url='{baseurl_escaped}/exp_hd?video_id={video_id}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='8'/>
			<media:credit role='uploader' scheme='urn:youtube' yt:display='{channel_name}' yt:type='partner'>{channel_id}</media:credit>
			<media:description type='plain'>{description}</media:description>
			<media:keywords/>
			<media:license type='text/html' href='http://www.youtube.com/t/terms'>youtube</media:license>
			<media:player url='http://www.youtube.com/watch?v={video_id}&amp;feature=youtube_gdata_player'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{video_id}/default.jpg' height='90' width='120' time='00:20:53' yt:name='default'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{video_id}/mqdefault.jpg' height='180' width='320' yt:name='mqdefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{video_id}/hqdefault.jpg' height='360' width='480' yt:name='hqdefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{video_id}/sddefault.jpg' height='480' width='640' yt:name='sddefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{video_id}/1.jpg' height='90' width='120' time='00:10:26.500' yt:name='start'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{video_id}/2.jpg' height='90' width='120' time='00:20:53' yt:name='middle'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{video_id}/3.jpg' height='90' width='120' time='00:31:19.500' yt:name='end'/>
			<media:title type='plain'>{title}</media:title>
			<yt:duration seconds='{duration}'/>
            <yt:caption status="serving" />
	        {ytpublish_date_tag}
			<yt:uploaderId>EE{channel_id}</yt:uploaderId>
			<yt:videoid>{video_id}</yt:videoid>
		</media:group>
		<gd:rating average='4.151515' max='5' min='1' numRaters='99' rel='http://schemas.google.com/g/2005#overall'/>
		<yt:statistics favoriteCount='0' viewCount='{view_count}'/>
		<yt:rating numDislikes='{dislikes}' numLikes='{likes}'/>
		<yt:cc>1</yt:cc>
	</entry>"""
        items_xml.append(item_xml.strip())
    
    xml_response = f"""<?xml version='1.0' encoding='UTF-8'?>
<feed
	xmlns='http://www.w3.org/2005/Atom'
	xmlns:gd='http://schemas.google.com/g/2005'
	xmlns:yt='{baseurl_escaped}/schemas/2007'
	xmlns:openSearch='http://a9.com/-/spec/opensearch/1.1/'
	xmlns:media='http://search.yahoo.com/mrss/' gd:etag='W/&quot;CEIMR384cSp7I2A9XRdUE0Q.&quot;'>
	<id>tag:youtube.com,2008:user:19cachicha:uploads</id>
	<updated>2014-12-01T00:09:46.139Z</updated>
	<category scheme='http://schemas.google.com/g/2005#kind' term='{baseurl_escaped}/schemas/2007#video'/>
	<title>Search results</title>
	<logo>http://www.gstatic.com/youtube/img/logo.png</logo>
	<link rel='alternate' type='text/html' href='http://www.youtube.com/channel/UC9yMWgQf2_xMhbdKPo7Ljrw/videos'/>
	<link rel='hub' href='http://pubsubhubbub.appspot.com'/>
	<author>
		<name>Youtube</name>
		<uri>{baseurl_escaped}/feeds/api/users/Youtube</uri>
		<yt:userId>null</yt:userId>
	</author>
	<generator version='2.1' uri='{baseurl_escaped}'>YouTube data API</generator>
	<openSearch:totalResults>9955</openSearch:totalResults>
	<openSearch:startIndex>1</openSearch:startIndex>
	<openSearch:itemsPerPage>20</openSearch:itemsPerPage>
    {''.join(items_xml)}
</feed>"""
    
    return xml_response
    

@app.route("/feeds/api/videos")
def search():
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", "20")
    try:
        limit = int(limit)
        if limit < 1 or limit > 50:
            limit = 20
    except Exception:
        limit = 20
    
    if not q:
        return Response("Missing 'q' parameter", status=400)
    
    baseurl = request.url_root.rstrip('/')
    search_data = request_youtube_search(q, limit)
    
    videos = []
    contents = search_data.get("contents", {}).get("twoColumnSearchResultsRenderer", {})\
        .get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
    for content in contents:
        item_section = content.get("itemSectionRenderer", {}).get("contents", [])
        for item in item_section:
            video_renderer = item.get("videoRenderer")
            if video_renderer:
                video = {
                    "video_id": video_renderer.get("videoId"),
                    "title": video_renderer.get("title", {}).get("runs", [{}])[0].get("text", ""),
                }
                videos.append(video)
    
    enriched_videos = []
    for v in videos[:limit]:
        enriched = enrich_video_data(v)
        if enriched:
            enriched_videos.append(enriched)
    
    xml_resp = build_xml_response(enriched_videos, baseurl)
    return Response(xml_resp, content_type="application/xml; charset=utf-8")

def iso8601_duration_to_seconds(duration):
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration)
    if not match:
        return 0
    hours, minutes, seconds = match.groups(default='0')
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

def escape_xml(text):
    if not text:
        return ""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))

os.makedirs("./assets/cache/channelsearch", exist_ok=True)
os.makedirs("./assets/cache/uploads", exist_ok=True)
os.makedirs("./assets/cache/videoinfo", exist_ok=True)

YOUTUBE_API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"

def get_video_info_cache_path(video_id):
    return f"./assets/cache/videoinfo/{video_id.replace('/', '_')}.json"

def fetch_video_details(video_id):
    cache_path = get_video_info_cache_path(video_id)
    if os.path.exists(cache_path) and time.time() - os.path.getmtime(cache_path) < 86400:
        try:
            return json.load(open(cache_path, "r", encoding="utf-8"))
        except Exception as e:
            pass
    url = f"https://www.youtube.com/youtubei/v1/player?key={YOUTUBE_API_KEY}"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    payload = {
        "context": {
            "client": {
                "hl": "en", "gl": "US", "clientName": "WEB", "clientVersion": "2.20210714.01.00"
            }
        },
        "videoId": video_id
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        data = r.json()
        try:
            json.dump(data, open(cache_path, "w", encoding="utf-8"), indent=2)
        except Exception as e:
            pass
        return data
    else:
        pass
        if os.path.exists(cache_path):
            try:
                return json.load(open(cache_path, "r", encoding="utf-8"))
            except:
                pass
    return None

def build_rss_video_data_from_video_details(video_id):
    data = fetch_video_details(video_id)
    if not data:
        return {}

    vd = data.get("videoDetails", {})
    length = int(vd.get("lengthSeconds", 0))
    mf = data.get("microformat", {}).get("microformatDataRenderer", {})

    # Get publishDate from microformat if possible
    publish_date = mf.get("publishDate")
    if publish_date:
        # If publish_date contains 'T', assume time info is included
        if "T" in publish_date:
            published_at = publish_date
        else:
            published_at = f"{publish_date}T00:00:00"
    else:
        # Fallback to videoDetails publishDate if available
        publish_date_vd = vd.get("publishDate")
        if publish_date_vd:
            if "T" in publish_date_vd:
                published_at = publish_date_vd
            else:
                published_at = f"{publish_date_vd}T00:00:00"
        else:
            # If no publish date info, fallback to current UTC time
            published_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "videoId": vd.get("videoId", video_id),
        "title": vd.get("title", ""),
        "description": vd.get("shortDescription", ""),
        "channelId": vd.get("channelId", ""),
        "thumbnailUrl": mf.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", ""),
        "lengthSeconds": length,
        "viewCount": int(vd.get("viewCount", 0)),
        "likeCount": 0,
        "dislikeCount": 0,
        "publishedAt": published_at,
        "duration": f"PT{length}S",
    }


def get_channel_search_cache_path(query):
    safe = query.replace(" ", "_").replace("@", "")
    return f"./assets/cache/channelsearch/{safe}.json"

def get_uploads_cache_path(channel_id):
    return f"./assets/cache/uploads/{channel_id}.json"

def save_json(path, data):
    try:
        json.dump(data, open(path, "w", encoding="utf-8"), indent=2)
    except Exception as e:
        pass
        
def load_json(path):
    try:
        return json.load(open(path, "r", encoding="utf-8"))
    except Exception as e:
        pass
        return None

def fetch_channel_search(query):
    cache_path = get_channel_search_cache_path(query)
    if os.path.exists(cache_path):
        return load_json(cache_path)
    url = f"https://www.youtube.com/youtubei/v1/search?key={YOUTUBE_API_KEY}"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    payload = {
        "context": {
            "client": {
                "hl": "en", "gl": "US", "clientName": "WEB", "clientVersion": "2.20210714.01.00"
            }
        },
        "query": query
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        data = r.json()
        save_json(cache_path, data)
        return data
    return None

def resolve_handle_to_channelid(handle):
    data = fetch_channel_search(handle)
    if not data:
        return None, None, None
    try:
        sections = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"]
        for sec in sections:
            items = sec.get("itemSectionRenderer", {}).get("contents", [])
            for it in items:
                cr = it.get("channelRenderer")
                if cr:
                    cid = cr.get("channelId")
                    author = "".join([r["text"] for r in cr.get("title", {}).get("runs", [])])
                    urlpart = cr.get("navigationEndpoint", {}).get("browseEndpoint", {}).get("canonicalBaseUrl", "")
                    if not urlpart.startswith("/@") and "handle" in cr:
                        urlpart = cr.get("handle", "")
                    handle_url = f"https://www.youtube.com{urlpart}" if urlpart else ""
                    return cid, author, handle_url
    except Exception as e:
        pass
    return None, None, None

def fetch_uploads(channel_id):
    path = get_uploads_cache_path(channel_id)
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 86400:
        return load_json(path)
    url = f"https://www.youtube.com/youtubei/v1/browse?key={YOUTUBE_API_KEY}&browseId={channel_id}"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    payload = {"context": {"client": {"hl": "en","gl": "US","clientName": "WEB","clientVersion": "2.20210714.01.00"}}}
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        data = r.json()
        save_json(path, data)
        return data
    elif os.path.exists(path):
        return load_json(path)
    return None

def extract_microformat_info(data):
    try:
        mf = data.get("microformat", {}).get("microformatDataRenderer", {})
        thumbs = mf.get("thumbnail", {}).get("thumbnails", [])
        return {
            "urlCanonical": mf.get("urlCanonical", ""),
            "title": mf.get("title", ""),
            "thumbnailUrl": thumbs[-1]["url"] if thumbs else ""
        }
    except Exception as e:
        pass
        return {"urlCanonical": "", "title": "", "thumbnailUrl": ""}

def extract_additional_info(vid):
    info = {}
    info["shortViewCount"] = vid.get("shortViewCountText", {}).get("simpleText", "") or vid.get("viewCountText", {}).get("simpleText", "")
    thumbs = vid.get("thumbnail", {}).get("thumbnails", [])
    info["thumbnailUrl"] = thumbs[-1]["url"] if thumbs else ""
    info["duration"] = ""
    for ov in vid.get("thumbnailOverlays", []):
        if "thumbnailOverlayTimeStatusRenderer" in ov:
            info["duration"] = ov["thumbnailOverlayTimeStatusRenderer"].get("text", {}).get("simpleText", "")
            break
    info["publishedTime"] = vid.get("publishedTimeText", {}).get("simpleText", "")
    return info

def extract_videos(data):
    vids = []
    try:
        shelves = data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"]
        for shelf in shelves:
            if "itemSectionRenderer" in shelf:
                for cont in shelf["itemSectionRenderer"].get("contents", []):
                    if "shelfRenderer" in cont:
                        for itm in cont["shelfRenderer"]["content"]["horizontalListRenderer"]["items"]:
                            if "gridVideoRenderer" in itm:
                                v = itm["gridVideoRenderer"]
                                vid = {
                                    "videoId": v.get("videoId", ""),
                                    "title": v.get("title", {}).get("simpleText", ""),
                                    "publishedTime": v.get("publishedTimeText", {}).get("simpleText", ""),
                                    "viewCount": v.get("viewCountText", {}).get("simpleText", "")
                                }
                                vid.update(extract_additional_info(v))
                                vids.append(vid)
    except Exception as e:
        pass
    return vids

@app.route("/feeds/api/users/<string:identifier>/uploads")
def channel_rss(identifier):
    base_url = request.host_url  # This is dynamic based on caller's request
    if identifier.startswith("@"):
        channel_id, author, handle_url = resolve_handle_to_channelid(identifier)
    elif identifier.startswith("UC") and len(identifier) == 24:
        channel_id, author, handle_url = identifier, None, None
    else:
        channel_id, author, handle_url = resolve_handle_to_channelid(identifier)

    if not channel_id:
        return jsonify({"error": "Channel not found"}), 404

    uploads = fetch_uploads(channel_id)
    if not uploads:
        return jsonify({"error": "Failed to fetch uploads"}), 500

    micro = extract_microformat_info_events(uploads)
    videos = extract_videos_event(uploads)
    enriched = []
    for v in videos[:15]:
        if not v.get("videoId"):
            continue
        data = build_rss_video_data_from_video_details_events(v["videoId"])
        if data:
            enriched.append(data)

    channel_title = escape_xml_events(micro.get("title") or author or "YouTube Channel")
    channel_link = escape_xml_events(micro.get("urlCanonical") or handle_url or f"{base_url}channel/{channel_id}")


    rss_items = ""
    for v in enriched:
        video_url = f"https://www.youtube.com/watch?v={v['videoId']}"
        duration_sec = iso8601_duration_to_seconds(v.get("duration", ""))
        rss_items += f"""<entry gd:etag='W/&quot;CUYDQ347eCp7I2A9XRdVGEs.&quot;'>
		<id>tag:youtube.com,2008:video:{escape_xml(v.get("videoId", ""))}</id>
		<published>{escape_xml(v.get("publishedAt", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")))}</published>
		<updated>{escape_xml(v.get("publishedAt", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")))}</updated>
		<category scheme='http://schemas.google.com/g/2005#kind' term='{base_url}schemas/2007#video'/>
		<category scheme='{base_url}schemas/2007/categories.cat' term='News' label='News &amp; Politics'/>
		<title>{escape_xml(v.get("title", ""))}</title>
		<content type='application/x-shockwave-flash' src='http://www.youtube.com/v/{escape_xml(v.get("videoId", ""))}?version=3&amp;f=user_uploads&amp;app=youtube_gdata'/>
		<link rel='alternate' type='text/html' href='http://www.youtube.com/watch?v={escape_xml(v.get("videoId", ""))}&amp;feature=youtube_gdata'/>
		<link rel='{base_url}schemas/2007#video.related' type='applicatio0tom+xml' href='{base_url}feeds/api/videos/{escape_xml(v.get("videoId", ""))}/related?v=2'/>
		<link rel='{base_url}schemas/2007#mobile' type='text/html' href='http://m.youtube.com/details?v={escape_xml(v.get("videoId", ""))}'/>
		<link rel='{base_url}schemas/2007#uploader' type='applicatio0tom+xml' href='{base_url}feeds/api/users/{escape_xml(channel_id)}?v=2'/>
		<link rel='self' type='applicatio0tom+xml' href='{base_url}feeds/api/users/{escape_xml(channel_id)}/uploads/{escape_xml(v.get("videoId", ""))}?v=2'/>
		<author>
			<name>{channel_title}</name>
			<uri>{base_url}feeds/api/users/{escape_xml(channel_id)}</uri>
			<yt:userId>EE{escape_xml(channel_id)}</yt:userId>
		</author>
		<yt:accessControl action='comment' permission='allowed'/>
		<yt:accessControl action='commentVote' permission='allowed'/>
		<yt:accessControl action='videoRespond' permission='moderated'/>
		<yt:accessControl action='rate' permission='allowed'/>
		<yt:accessControl action='embed' permission='allowed'/>
		<yt:accessControl action='list' permission='allowed'/>
		<yt:accessControl action='autoPlay' permission='allowed'/>
		<yt:accessControl action='syndicate' permission='allowed'/>
		<gd:comments>
			<gd:feedLink rel='{base_url}schemas/2007#comments' href='{base_url}feeds/api/videos/{escape_xml(v.get("videoId", ""))}/comments?v=2' countHint='24'/>
		</gd:comments>
		<media:group>
			<media:category label='News &amp; Politics' scheme='{base_url}schemas/2007/categories.cat'>News</media:category>
			<media:content url='http://www.youtube.com/v/{escape_xml(v.get("videoId", ""))}?version=3&amp;f=user_uploads&amp;app=youtube_gdata' type='application/x-shockwave-flash' medium='video' isDefault='true' expression='full' duration='2506' yt:format='5'/>
            <media:content url='{base_url}channel_fh264_getvideo?v={escape_xml(v.get("videoId", ""))}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='3'/><media:content url='{base_url}get_480?video_id={escape_xml(v.get("videoId", ""))}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='14'/><media:content url='{base_url}exp_hd?video_id={escape_xml(v.get("videoId", ""))}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='8'/>
			<media:credit role='uploader' scheme='urn:youtube' yt:display='{channel_title}' yt:type='partner'>{escape_xml(channel_id)}</media:credit>
			<media:description type='plain'>{escape_xml(v.get("description", ""))}</media:description>
			<media:keywords/>
			<media:license type='text/html' href='http://www.youtube.com/t/terms'>youtube</media:license>
			<media:player url='http://www.youtube.com/watch?v={escape_xml(v.get("videoId", ""))}&amp;feature=youtube_gdata_player'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{escape_xml(v.get("videoId", ""))}/default.jpg' height='90' width='120' time='00:20:53' yt:name='default'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{escape_xml(v.get("videoId", ""))}/mqdefault.jpg' height='180' width='320' yt:name='mqdefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{escape_xml(v.get("videoId", ""))}/hqdefault.jpg' height='360' width='480' yt:name='hqdefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{escape_xml(v.get("videoId", ""))}/sddefault.jpg' height='480' width='640' yt:name='sddefault'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{escape_xml(v.get("videoId", ""))}/1.jpg' height='90' width='120' time='00:10:26.500' yt:name='start'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{escape_xml(v.get("videoId", ""))}/2.jpg' height='90' width='120' time='00:20:53' yt:name='middle'/>
			<media:thumbnail url='http://i.ytimg.com/vi/{escape_xml(v.get("videoId", ""))}/3.jpg' height='90' width='120' time='00:31:19.500' yt:name='end'/>
			<media:title type='plain'>{escape_xml(v.get("title", ""))}</media:title>
			<yt:duration seconds='{duration_sec}'/>
	        <yt:uploaded>{escape_xml(v.get("publishedAt", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")))}</yt:uploaded>
			<yt:uploaderId>EE{escape_xml(channel_id)}</yt:uploaderId>
			<yt:videoid>{escape_xml(v.get("videoId", ""))}</yt:videoid>
		</media:group>
		<gd:rating average='4.151515' max='5' min='1' numRaters='99' rel='http://schemas.google.com/g/2005#overall'/>
		<yt:statistics favoriteCount='0' viewCount='{v.get("viewCount", 0)}'/>
		<yt:rating numDislikes='0' numLikes='{v.get("likeCount", 0)}'/>
	</entry>"""

    channel_title = escape_xml(micro.get("title") or author or "YouTube Channel")
    channel_link = escape_xml(micro.get("urlCanonical") or handle_url or f"{base_url}channel/{channel_id}")

    rss_feed = f"""<?xml version='1.0' encoding='UTF-8'?>
<feed
	xmlns='http://www.w3.org/2005/Atom'
	xmlns:gd='http://schemas.google.com/g/2005'
	xmlns:yt='{base_url}/schemas/2007'
	xmlns:openSearch='http://a9.com/-/spec/opensearch/1.1/'
	xmlns:media='http://search.yahoo.com/mrss/' gd:etag='W/&quot;CEIMR384cSp7I2A9XRdUE0Q.&quot;'>
	<id>tag:youtube.com,2008:user:19cachicha:uploads</id>
	<updated>2014-12-01T00:09:46.139Z</updated>
	<category scheme='http://schemas.google.com/g/2005#kind' term='{base_url}/schemas/2007#video'/>
	<title>Search results</title>
	<logo>http://www.gstatic.com/youtube/img/logo.png</logo>
	<link rel='alternate' type='text/html' href='http://www.youtube.com/channel/UC9yMWgQf2_xMhbdKPo7Ljrw/videos'/>
	<link rel='hub' href='http://pubsubhubbub.appspot.com'/>
	<author>
		<name>Youtube</name>
		<uri>{base_url}/feeds/api/users/Youtube</uri>
		<yt:userId>null</yt:userId>
	</author>
	<generator version='2.1' uri='{base_url}'>YouTube data API</generator>
	<openSearch:totalResults>9955</openSearch:totalResults>
	<openSearch:startIndex>1</openSearch:startIndex>
	<openSearch:itemsPerPage>20</openSearch:itemsPerPage>
    {rss_items}
</feed>"""

    return Response(rss_feed.strip(), mimetype="application/rss+xml")

VIITUBE_HISTORY_PATH = "./assets/cache/history.json"
VIITUBE_HISTORY_CACHE_EXPIRATION = 5 * 3600  # 5 hours (in seconds)

def viitube_fetch_watch_history(oauth_token):
    """Retrieve YouTube watch history using OAuth authentication and save to cache."""
    url = "https://www.youtube.com/youtubei/v1/browse"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth_token}"
    }
    payload = {
        "context": {
            "client": {
                "hl": "en",
                "gl": "en",
                "clientName": "TVHTML5",
                "clientVersion": "7.20250528.14.00",
                "platform": "TV"
            }
        },
        "browseId": "FEhistory"
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        history_data = response.json()
        viitube_save_cache_History(history_data)  # Save response to cache
        return history_data
    return None

def viitube_save_cache_History(data):
    """Save watch history to cache with timestamp."""
    os.makedirs(os.path.dirname(VIITUBE_HISTORY_PATH), exist_ok=True)
    cache_content = {"timestamp": time.time(), "data": data}
    with open(VIITUBE_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(cache_content, f, indent=4)

def load_history_cache(oauth_token):
    """Load cached history, checking expiration and refreshing if needed."""
    if os.path.exists(VIITUBE_HISTORY_PATH):
        with open(VIITUBE_HISTORY_PATH, "r", encoding="utf-8") as f:
            cache_content = json.load(f)

        # Validate cache structure
        if "timestamp" not in cache_content or "data" not in cache_content:
            return viitube_fetch_watch_history(oauth_token)

        # If cache is older than 5 hours, refresh it at next request
        if time.time() - cache_content["timestamp"] > VIITUBE_HISTORY_CACHE_EXPIRATION:
            return viitube_fetch_watch_history(oauth_token)

        return cache_content["data"]  # Use cached data if valid
    return viitube_fetch_watch_history(oauth_token)  # No cache found, fetch fresh data


def extract_history_video_ids(history_data):
    """Extract unique video IDs ordered by most recent watch time."""
    video_entries = set()

    def recursive_search(data):
        """Recursively search for video IDs and timestamps."""
        if isinstance(data, dict):
            if "videoId" in data:
                timestamp = data.get("publishedTimeText", {}).get("simpleText", "0")
                video_entries.add((timestamp, data["videoId"]))
            for value in data.values():
                recursive_search(value)
        elif isinstance(data, list):
            for item in data:
                recursive_search(item)

    recursive_search(history_data)
    return [video_id for _, video_id in sorted(video_entries, reverse=True, key=lambda x: x[0])]

def fetch_video_details_history(video_ids, oauth_token):
    """Retrieve video details using YouTube API v3 with OAuth token."""
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id={','.join(video_ids)}"
    headers = {"Authorization": f"Bearer {oauth_token}"}

    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

@app.route('/feeds/api/users/default/watch_history', methods=['GET'])
def get_watch_history_xml():
    """API endpoint returning ordered watch history with full metadata."""
    oauth_token = request.args.get('oauth_token')
    if not oauth_token:
        return Response('<error>Missing OAuth token</error>', mimetype='application/xml')

    # Load cache, refresh ONLY IF expired (older than 5 hours)
    history_data = load_history_cache(oauth_token)
    if not history_data:
        return Response('<error>Failed to retrieve watch history</error>', mimetype='application/xml')

    # Extract unique video IDs in reverse chronological order
    video_ids = extract_history_video_ids(history_data)
    if not video_ids:
        return Response('<error>No video history found</error>', mimetype='application/xml')

    # Fetch video details using OAuth
    video_details = fetch_video_details_history(video_ids, oauth_token)
    if not video_details:
        return Response('<error>Failed to retrieve video details</error>', mimetype='application/xml')

    # Generate XML response
    xml_string = '<?xml version="1.0" encoding="UTF-8"?><feed>'
    for item in video_details.get("items", []):
        video_id = item["id"]
        title = item["snippet"]["title"]
        author_name = item["snippet"]["channelTitle"]
        uploader_id = item["snippet"]["channelId"]
        thumbnail_url = item["snippet"]["thumbnails"]["medium"]["url"]
        published_date = item["snippet"].get("publishedAt", "null")
        view_count = item["statistics"].get("viewCount", "0")
        
        # Convert duration to seconds
        duration_iso = item.get("contentDetails", {}).get("duration", "PT0S")
        duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())

        xml_string += f'''
        <entry>
            <id>http://localhost:5000/api/videos/{video_id}</id>
            <published>{published_date}</published>
            <title type="text">{title}</title>
            <link rel="alternate" href="http://localhost:5000/api/videos/{video_id}/related"/>
            <author>
                <name>{author_name}</name>
                <uri>https://www.youtube.com/channel/{uploader_id}</uri>
                <yt:userId>EE{uploader_id}</yt:userId>
            </author>
            <media:group>
                <media:thumbnail url="http://i.ytimg.com/vi/{video_id}/mqdefault.jpg" height="240" width="320"/>
                <yt:duration seconds="{duration_seconds}"/>
                <yt:uploaderId>EE{uploader_id}</yt:uploaderId>
                <yt:videoid id="{video_id}">{video_id}</yt:videoid>
                <media:credit role="uploader" name="{author_name}">{author_name}</media:credit>
            </media:group>
            <yt:statistics favoriteCount="0" viewCount="{view_count}"/>
        </entry>'''
    
    xml_string += '</feed>'
    return Response(xml_string, mimetype='application/xml')

def iso8601_duration_to_seconds_events(duration):
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration)
    if not match:
        return 0
    hours, minutes, seconds = match.groups(default='0')
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

def escape_xml_events(text):
    if not text:
        return ""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))

os.makedirs("./assets/cache/channelsearch", exist_ok=True)
os.makedirs("./assets/cache/uploads", exist_ok=True)
os.makedirs("./assets/cache/videoinfo", exist_ok=True)

YOUTUBE_API_KEY_EVENTS = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"

def get_video_info_cache_path_events(video_id):
    return f"./assets/cache/videoinfo/{video_id.replace('/', '_')}.json"

def fetch_video_details_events(video_id):
    cache_path = get_video_info_cache_path_events(video_id)
    if os.path.exists(cache_path) and time.time() - os.path.getmtime(cache_path) < 86400:
        try:
            return json.load(open(cache_path, "r", encoding="utf-8"))
        except Exception as e:
            pass
    url = f"https://www.youtube.com/youtubei/v1/player?key={YOUTUBE_API_KEY_EVENTS}"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    payload = {
        "context": {
            "client": {
                "hl": "en", "gl": "US", "clientName": "WEB", "clientVersion": "2.20210714.01.00"
            }
        },
        "videoId": video_id
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        data = r.json()
        try:
            json.dump(data, open(cache_path, "w", encoding="utf-8"), indent=2)
        except Exception as e:
            pass
        return data
    else:
        pass
        if os.path.exists(cache_path):
            try:
                return json.load(open(cache_path, "r", encoding="utf-8"))
            except:
                pass
    return None

def build_rss_video_data_from_video_details_events(video_id):
    data = fetch_video_details_events(video_id)
    if not data:
        return {}

    vd = data.get("videoDetails", {})
    length = int(vd.get("lengthSeconds", 0))
    mf = data.get("microformat", {}).get("microformatDataRenderer", {})

    # Get publishDate from microformat if possible
    publish_date = mf.get("publishDate")
    if publish_date:
        # If publish_date contains 'T', assume time info is included
        if "T" in publish_date:
            published_at = publish_date
        else:
            published_at = f"{publish_date}T00:00:00"
    else:
        # Fallback to videoDetails publishDate if available
        publish_date_vd = vd.get("publishDate")
        if publish_date_vd:
            if "T" in publish_date_vd:
                published_at = publish_date_vd
            else:
                published_at = f"{publish_date_vd}T00:00:00"
        else:
            # If no publish date info, fallback to current UTC time
            published_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "videoId": vd.get("videoId", video_id),
        "title": vd.get("title", ""),
        "description": vd.get("shortDescription", ""),
        "channelId": vd.get("channelId", ""),
        "thumbnailUrl": mf.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", ""),
        "lengthSeconds": length,
        "viewCount": int(vd.get("viewCount", 0)),
        "likeCount": 0,
        "dislikeCount": 0,
        "publishedAt": published_at,
        "duration": f"PT{length}S",
    }


def get_channel_search_cache_path_events(query):
    safe = query.replace(" ", "_").replace("@", "")
    return f"./assets/cache/channelsearch/{safe}.json"

def get_uploads_cache_path_events(channel_id):
    return f"./assets/cache/uploads/{channel_id}.json"

def save_json_events(path, data):
    try:
        json.dump(data, open(path, "w", encoding="utf-8"), indent=2)
    except Exception as e:
        pass
        
def load_json_events(path):
    try:
        return json.load(open(path, "r", encoding="utf-8"))
    except Exception as e:
        pass
        return None

def fetch_channel_search_events(query):
    cache_path = get_channel_search_cache_path_events(query)
    if os.path.exists(cache_path):
        return load_json_events(cache_path)
    url = f"https://www.youtube.com/youtubei/v1/search?key={YOUTUBE_API_KEY_EVENTS}"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    payload = {
        "context": {
            "client": {
                "hl": "en", "gl": "US", "clientName": "WEB", "clientVersion": "2.20210714.01.00"
            }
        },
        "query": query
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        data = r.json()
        save_json_events(cache_path, data)
        return data
    return None

def resolve_handle_to_channelid_events(handle):
    data = fetch_channel_search_events(handle)
    if not data:
        return None, None, None
    try:
        sections = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"]
        for sec in sections:
            items = sec.get("itemSectionRenderer", {}).get("contents", [])
            for it in items:
                cr = it.get("channelRenderer")
                if cr:
                    cid = cr.get("channelId")
                    author = "".join([r["text"] for r in cr.get("title", {}).get("runs", [])])
                    urlpart = cr.get("navigationEndpoint", {}).get("browseEndpoint", {}).get("canonicalBaseUrl", "")
                    if not urlpart.startswith("/@") and "handle" in cr:
                        urlpart = cr.get("handle", "")
                    handle_url = f"https://www.youtube.com{urlpart}" if urlpart else ""
                    return cid, author, handle_url
    except Exception as e:
        pass
    return None, None, None

def fetch_uploads_events(channel_id):
    path = get_uploads_cache_path_events(channel_id)
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 86400:
        return load_json_events(path)
    url = f"https://www.youtube.com/youtubei/v1/browse?key={YOUTUBE_API_KEY_EVENTS}&browseId={channel_id}"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    payload = {"context": {"client": {"hl": "en","gl": "US","clientName": "WEB","clientVersion": "2.20210714.01.00"}}}
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        data = r.json()
        save_json_events(path, data)
        return data
    elif os.path.exists(path):
        return load_json_events(path)
    return None

def extract_microformat_info_events(data):
    try:
        mf = data.get("microformat", {}).get("microformatDataRenderer", {})
        thumbs = mf.get("thumbnail", {}).get("thumbnails", [])
        return {
            "urlCanonical": mf.get("urlCanonical", ""),
            "title": mf.get("title", ""),
            "thumbnailUrl": thumbs[-1]["url"] if thumbs else ""
        }
    except Exception as e:
        pass
        return {"urlCanonical": "", "title": "", "thumbnailUrl": ""}

def extract_additional_info_event(vid):
    info = {}
    info["shortViewCount"] = vid.get("shortViewCountText", {}).get("simpleText", "") or vid.get("viewCountText", {}).get("simpleText", "")
    thumbs = vid.get("thumbnail", {}).get("thumbnails", [])
    info["thumbnailUrl"] = thumbs[-1]["url"] if thumbs else ""
    info["duration"] = ""
    for ov in vid.get("thumbnailOverlays", []):
        if "thumbnailOverlayTimeStatusRenderer" in ov:
            info["duration"] = ov["thumbnailOverlayTimeStatusRenderer"].get("text", {}).get("simpleText", "")
            break
    info["publishedTime"] = vid.get("publishedTimeText", {}).get("simpleText", "")
    return info

def extract_videos_event(data):
    vids = []
    try:
        shelves = data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"]
        for shelf in shelves:
            if "itemSectionRenderer" in shelf:
                for cont in shelf["itemSectionRenderer"].get("contents", []):
                    if "shelfRenderer" in cont:
                        for itm in cont["shelfRenderer"]["content"]["horizontalListRenderer"]["items"]:
                            if "gridVideoRenderer" in itm:
                                v = itm["gridVideoRenderer"]
                                vid = {
                                    "videoId": v.get("videoId", ""),
                                    "title": v.get("title", {}).get("simpleText", ""),
                                    "publishedTime": v.get("publishedTimeText", {}).get("simpleText", ""),
                                    "viewCount": v.get("viewCountText", {}).get("simpleText", "")
                                }
                                vid.update(extract_additional_info_event(v))
                                vids.append(vid)
    except Exception as e:
        pass
    return vids

@app.route("/feeds/api/events")
def channel_rss_event():
    identifier = request.args.get("author")
    if not identifier:
        return jsonify({"error": "Missing required parameter: identifier"}), 400

    base_url = request.host_url

    if identifier.startswith("@"):
        channel_id, author, handle_url = resolve_handle_to_channelid_events(identifier)
    elif identifier.startswith("UC") and len(identifier) == 24:
        channel_id, author, handle_url = identifier, None, None
    else:
        channel_id, author, handle_url = resolve_handle_to_channelid_events(identifier)

    if not channel_id:
        return jsonify({"error": "Channel not found"}), 404

    uploads = fetch_uploads_events(channel_id)
    if not uploads:
        return jsonify({"error": "Failed to fetch uploads"}), 500


    micro = extract_microformat_info_events(uploads)
    videos = extract_videos_event(uploads)
    enriched = []
    for v in videos[:15]:
        if not v.get("videoId"):
            continue
        data = build_rss_video_data_from_video_details_events(v["videoId"])
        if data:
            enriched.append(data)

    channel_title = escape_xml_events(micro.get("title") or author or "YouTube Channel")
    channel_link = escape_xml_events(micro.get("urlCanonical") or handle_url or f"{base_url}channel/{channel_id}")

    rss_items = ""
    for v in enriched:
        video_url = f"https://www.youtube.com/watch?v={v['videoId']}"
        duration_sec = iso8601_duration_to_seconds_events(v.get("duration", ""))
        rss_items += f"""    <entry>
		<id>tag:youtube.com,2008:video:{escape_xml_events(v.get("videoId", ""))}</id>
		<updated>{escape_xml_events(v.get("publishedAt", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")))}</updated>
		<category scheme='http://schemas.google.com/g/2005#kind' term='http://http://gdata.youtube.com/schemas/2007#userEvent'/>
		<category scheme='http://gdata.youtube.com/schemas/2007/userevents.cat' term='video_uploaded'/>
		<title>{escape_xml_events(v.get("title", ""))}</title>
		<yt:videoid>{escape_xml_events(v.get("videoId", ""))}</yt:videoid>
        <yt:username>{escape_xml_events(v.get("videoId", ""))}</yt:username>
        <yt:groupId>0</yt:groupId>
        <author>
			<name>{channel_title}</name>
			<uri>{base_url}feeds/api/users/{channel_title}</uri>
		</author>
        <link rel='http://gdata.youtube.com/schemas/2007#video' href='{base_url}feeds/api/videos/{escape_xml_events(v.get("videoId", ""))}'>
            
        <entry>
            <id>{base_url}feeds/api/videos/{escape_xml_events(v.get("videoId", ""))}</id>
            <youTubeId id='{escape_xml_events(v.get("videoId", ""))}'>{escape_xml_events(v.get("videoId", ""))}</youTubeId>
            <published>{escape_xml_events(v.get("publishedAt", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")))}</published>
            <updated>{escape_xml_events(v.get("publishedAt", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")))}</updated>
            <category scheme="http://gdata.youtube.com/schemas/2007/categories.cat" label="-" term="-">-</category>
            <title type='text'>{escape_xml_events(v.get("title", ""))}</title>
            <content type='text'>-</content>
            <link rel="http://gdata.youtube.com/schemas/2007#video.related" href="{base_url}feeds/api/videos/{escape_xml_events(v.get("videoId", ""))}/related"/>
            <author>
                <name>{escape_xml_events(channel_id)}</name>
                <uri>{base_url}feeds/api/users/{escape_xml_events(channel_id)}</uri>
            </author>
            <gd:comments>
                <gd:feedLink href='{base_url}feeds/api/videos/{escape_xml_events(v.get("videoId", ""))}/comments' countHint='530'/>
            </gd:comments>
            <media:group>
                <media:category label='-' scheme='http://gdata.youtube.com/schemas/2007/categories.cat'>-</media:category>
                <media:content url='{base_url}channel_fh264_getvideo?v={escape_xml_events(v.get("videoId", ""))}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='3'/>
                <media:description type='plain'>{escape_xml_events(v.get("description", ""))}</media:description>
                <media:keywords>-</media:keywords>
                <media:player url='http://www.youtube.com/watch?v={escape_xml_events(v.get("videoId", ""))}'/>
                <media:thumbnail yt:name='hqdefault' url='http://i.ytimg.com/vi/{escape_xml_events(v.get("videoId", ""))}/hqdefault.jpg' height='240' width='320' time='00:00:00'/>
                <media:thumbnail yt:name='poster' url='http://i.ytimg.com/vi/{escape_xml_events(v.get("videoId", ""))}/0.jpg' height='240' width='320' time='00:00:00'/>
                <media:thumbnail yt:name='default' url='http://i.ytimg.com/vi/{escape_xml_events(v.get("videoId", ""))}/0.jpg' height='240' width='320' time='00:00:00'/>
                <yt:duration seconds='{duration_sec}'/>
                <yt:videoid id='{escape_xml_events(v.get("videoId", ""))}'>{escape_xml_events(v.get("videoId", ""))}</yt:videoid>
                <youTubeId id='{escape_xml_events(v.get("videoId", ""))}'>{escape_xml_events(v.get("videoId", ""))}</youTubeId>
                <media:credit role='uploader' scheme='urn:youtube' yt:display='{channel_title}' yt:type='partner'>{escape_xml_events(channel_id)}</media:credit>
            </media:group>
		<gd:rating average='4.151515' max='5' min='1' numRaters='99' rel='http://schemas.google.com/g/2005#overall'/>
		<yt:statistics favoriteCount='0' viewCount='{v.get("viewCount", 0)}'/>
		<yt:rating numDislikes='0' numLikes='{v.get("likeCount", 0)}'/>
		</entry>
        </link>
	</entry>"""

    channel_title = escape_xml_events(micro.get("title") or author or "YouTube Channel")
    channel_link = escape_xml_events(micro.get("urlCanonical") or handle_url or f"{base_url}channel/{channel_id}")

    rss_feed = f"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'
xmlns:media='http://search.yahoo.com/mrss/'
xmlns:openSearch='http://a9.com/-/spec/opensearchrss/1.0/'
xmlns:gd='http://schemas.google.com/g/2005'
xmlns:yt='http://gdata.youtube.com/schemas/2007'>
    <id>http://gdata.youtube.com/feeds/api/standardfeeds/us/recently_featured</id>
    <updated>2010-12-21T18:59:58.000-08:00</updated>
    <category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#video'/>
    <title type='text'> </title>
    <logo>http://www.youtube.com/img/pic_youtubelogo_123x63.gif</logo>
    <author>
        <name>YouTube</name>
        <uri>http://www.youtube.com/</uri>
    </author>
    <generator version='2.0' uri='http://gdata.youtube.com/'>YouTube data API</generator>
    <openSearch:totalResults>25</openSearch:totalResults>
    <openSearch:startIndex>1</openSearch:startIndex>
    <openSearch:itemsPerPage>25</openSearch:itemsPerPage>
    {rss_items}
</feed>"""

    return Response(rss_feed.strip(), mimetype="application/atom+xml")

@app.route('/feeds/api/users/<channelfavorites>/favorites')
def channelfavorites(channelfavorites):
    return send_file('mobile/blank.xml')


@app.route('/feeds/api/charts/live/events/<region>')
def live(region):
    return send_file('Mobile/blank.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_viewed')
def most_viewed(region):
    return send_file('Mobile/most_viewed.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Education')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Education')
def most_viewed_Education(region):
    return send_file('Mobile/most_viewed_Education.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Comedy')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Comedy')
def most_viewed_Comedy(region):
    return send_file('Mobile/most_viewed_Comedy.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Tech')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Tech')
def most_viewed_Tech(region):
    return send_file('Mobile/most_viewed_Tech.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Entertainment')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Entertainment')
def most_viewed_Entertainment(region):
    return send_file('Mobile/most_viewed_Entertainment.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Animals')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Animals')
def most_viewed_Animals(region):
    return send_file('Mobile/most_viewed_Animals.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Music')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Music')
def most_viewed_Music(region):
    return send_file('Mobile/most_viewed_Music.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Film')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Film')
def most_viewed_Film(region):
    return send_file('Mobile/most_viewed_Film.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Autos')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Autos')
def most_viewed_Autos(region):
    return send_file('Mobile/most_viewed_Autos.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_News')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_News')
def most_viewed_News(region):
    return send_file('Mobile/most_viewed_News.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Howto')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Howto')
def most_viewed_Howto(region):
    return send_file('Mobile/most_viewed_Howto.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Games')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Games')
def most_viewed_Games(region):
    return send_file('Mobile/most_viewed_Games.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_People')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_People')
def most_viewed_People(region):
    return send_file('Mobile/most_viewed_People.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Travel')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Travel')
def most_viewed_Travel(region):
    return send_file('Mobile/most_viewed_Travel.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Sports')
@app.route('/feeds/api/standardfeeds/<region>/most_viewed_Sports')
def most_viewed_Sports(region):
    return send_file('Mobile/most_viewed_Sports.xml')
	
@app.route('/feeds/api/standardfeeds/<region>/most_discussed')
def most_discussed(region):
    return send_file('Mobile/most_discussed.xml')
    
@app.route('/feeds/api/standardfeeds/<region>/most_popular')
def most_popular(region):
    return send_file('Mobile/most_popular.xml')
	
@app.route('/feeds/api/standardfeeds/<region>/recently_featured')
def recently_featured(region):
    return send_file('Mobile/recently_featured.xml')

# 📁 Define storage paths
MOBILE_VIDEO_DIR = os.path.dirname(os.path.abspath(__file__))
MOBILE_VIDEO_SAVE_DIR= os.path.join(MOBILE_VIDEO_DIR, "assets")
MOBILE_VIDEO_CACHE_DIR = os.path.join(MOBILE_VIDEO_DIR, "assets", "cache", "videoinfo")

os.makedirs(MOBILE_VIDEO_DIR, exist_ok=True)
os.makedirs(MOBILE_VIDEO_CACHE_DIR, exist_ok=True)  

# ✅ Helper class to fetch video info
class MobileVideoInfo:
    def MobilePlayback(self, video_id):
        cache_file = os.path.join(MOBILE_VIDEO_CACHE_DIR, f"{video_id}.json")

        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

        # 🌐 Fetch from YouTube internal API
        url = "https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }
        payload = {
            "context": {
                "client": {
                    "hl": "en",
                    "gl": "US",
                    "clientName": "WEB",
                    "clientVersion": "2.20210714.01.00"
                }
            },
            "videoId": video_id
        }

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            return {"error": "Failed to fetch video info"}

        try:
            data = response.json()
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except Exception as e:
            return {"error": str(e)}


# 🎥 Download video and fetch info
def mobiledownloadvideo(video_id):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    yt = YouTube(video_url)

    video_filename = f"{video_id}.mp4"
    video_path = os.path.join(MOBILE_SAVE_DIR, video_filename)

    if not os.path.exists(video_path):
        stream = yt.streams.get_highest_resolution()
        stream.download(MOBILE_SAVE_DIR, filename=video_filename)

    # 💾 Also get video info
    MobileVideoInfo().MobilePlayback(video_id)

    return video_path


# 🔍 Extract clean video ID
def mobile_get_clean_video_id():
    raw_id = request.args.get("video_id", "") or request.args.get("v", "")
    match = re.match(r"^[A-Za-z0-9_-]{11}", raw_id)
    return match.group(0) if match else None


# 📡 All endpoints below
@app.route('/get_480', methods=['GET'])
@app.route('/exp_hd', methods=['GET'])
@app.route('/channel_fh264_getvideo', methods=['GET'])
@app.route('/geeeeeeeeeeeeet_video', methods=['GET'])
@app.route('/geeeeeeeeeeeet_video', methods=['GET'])
@app.route('/get_video', methods=['GET'])
@app.route('/geeeeeeeeeeeeeet_video', methods=['GET'])
def mobile_serve_video():
    video_id = mobile_get_clean_video_id()

    if not video_id:
        return "Missing or invalid video_id parameter", 400

    try:
        video_path = mobiledownloadvideo(video_id)
        return send_file(video_path, as_attachment=True)
    except Exception as e:
        return "Internal server error", 500
    

VIITUBE_MOBILE_PLAYLIST_URL = "https://www.youtube.com/youtubei/v1/browse"
SEARCH_VIITUBE_MOBILE_PLAYLIST_URL = "https://www.youtube.com/youtubei/v1/search"
MOBILE_PLAYLIST_API_KEY = "YOUR_MOBILE_PLAYLIST_API_KEY_HERE"  # Replace with your YouTube API key
MOBILE_PLAYLIST_DIR = "./assets/cache/playlists/users"
MOBILE_PLAYLIST_SEARCH_DIR = "./assets/cache/channelsearch"

CONTEXT = {
    "client": {
        "screenWidthPoints": 1361,
        "screenHeightPoints": 962,
        "utcOffsetMinutes": 120,
        "hl": "en",
        "gl": "US",
        "deviceMake": "Samsung",
        "deviceModel": "SmartTV",
        "clientName": "TVHTML5",
        "clientVersion": "7.20250805.16.00",
        "osName": "Tizen",
        "osVersion": "5.5",
        "platform": "TV",
    },
    "user": {"enableSafetyMode": False},
    "request": {},
    "clickTracking": {}
}

def mobile_felsh_playlist_data(MOBILE_PLAYLIST_API_KEY, browse_id):
    cache_file = f"{MOBILE_PLAYLIST_DIR}/{browse_id}.json"
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"{VIITUBE_MOBILE_PLAYLIST_URL}?key={MOBILE_PLAYLIST_API_KEY}"
    payload = {"browseId": browse_id, "context": CONTEXT}
    headers = {"Content-Type": "application/json"}

    r = requests.post(url, headers=headers, json=payload)
    if r.status_code == 200:
        data = r.json()
        os.makedirs(MOBILE_PLAYLIST_DIR, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    else:
        return None

def playlist_search_channel_id(query):
    cache_file = f"{MOBILE_PLAYLIST_SEARCH_DIR}/{query}.json"
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        payload = {
            "context": CONTEXT,
            "query": query,
            "params": "EgZjaGFubmVs"  # Base64 encoded param to filter channels
        }
        headers = {"Content-Type": "application/json"}
        url = f"{SEARCH_VIITUBE_MOBILE_PLAYLIST_URL}?key={MOBILE_PLAYLIST_API_KEY}"

        r = requests.post(url, headers=headers, json=payload)
        if r.status_code != 200:
            return None
        data = r.json()
        os.makedirs(MOBILE_PLAYLIST_SEARCH_DIR, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    try:
        sections = data["contents"]["sectionListRenderer"]["contents"]
        for section in sections:
            shelf = section.get("shelfRenderer")
            if not shelf:
                continue
            horizontal_list = shelf.get("content", {}).get("horizontalListRenderer", {})
            items = horizontal_list.get("items", [])
            for item in items:
                tile = item.get("tileRenderer")
                if tile and tile.get("contentType") == "TILE_CONTENT_TYPE_CHANNEL":
                    return tile.get("contentId")
    except (KeyError, TypeError):
        pass

    # Fallback to old method if needed
    try:
        sections = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"]
        for section in sections:
            item_section = section.get("itemSectionRenderer")
            if not item_section:
                continue
            items = item_section.get("contents", [])
            for item in items:
                channel_renderer = item.get("channelRenderer")
                if channel_renderer:
                    return channel_renderer.get("channelId")
    except (KeyError, TypeError):
        pass

    return None

def playlist_find_playlist_tiles(obj):
    results = []

    if isinstance(obj, dict):
        if "tileRenderer" in obj:
            tile = obj["tileRenderer"]
            overlays = tile.get("header", {}).get("tileHeaderRenderer", {}).get("thumbnailOverlays", [])
            for overlay in overlays:
                if (
                    "thumbnailOverlayTimeStatusRenderer" in overlay and
                    overlay["thumbnailOverlayTimeStatusRenderer"].get("icon", {}).get("iconType") == "PLAYLISTS"
                ):
                    results.append(tile)
                    break
        else:
            for v in obj.values():
                results.extend(playlist_find_playlist_tiles(v))

    elif isinstance(obj, list):
        for item in obj:
            results.extend(playlist_find_playlist_tiles(item))

    return results

def playlist_extract_playlist_info(tile):
    info = {}

    # Title
    info['title'] = tile.get('metadata', {}).get('tileMetadataRenderer', {}).get('title', {}).get('simpleText')

    # Playlist ID
    on_select = tile.get('onSelectCommand', {}).get('browseEndpoint', {})
    info['playlist_id'] = on_select.get('playlistId') or tile.get('contentId')

    # Thumbnails
    thumbs = []
    try:
        thumbnails = tile['header']['tileHeaderRenderer']['thumbnail']['thumbnails']
        thumbs = [t['url'] for t in thumbnails]
    except (KeyError, TypeError):
        pass
    info['thumbnails'] = thumbs

    # Number of videos (extract number only)
    num_videos = None
    try:
        overlays = tile['header']['tileHeaderRenderer']['thumbnailOverlays']
        for overlay in overlays:
            if 'thumbnailOverlayTimeStatusRenderer' in overlay:
                runs = overlay['thumbnailOverlayTimeStatusRenderer']['text'].get('runs', [])
                raw_num = ''.join(run['text'] for run in runs) if runs else overlay['thumbnailOverlayTimeStatusRenderer']['text'].get('simpleText')
                # Extract only digits
                if raw_num:
                    match = re.search(r'\d+', raw_num)
                    num_videos = match.group(0) if match else raw_num
                break
    except (KeyError, TypeError):
        pass
    info['num_videos'] = num_videos

    # Author Name
    author = None
    try:
        lines = tile['metadata']['tileMetadataRenderer']['lines']
        for line in lines:
            items = line.get('lineRenderer', {}).get('items', [])
            for item in items:
                text_runs = item.get('lineItemRenderer', {}).get('text', {}).get('runs', [])
                if text_runs:
                    author = text_runs[0].get('text')
                    break
            if author:
                break
    except (KeyError, TypeError):
        pass
    info['author'] = author or "Unknown"

    return info

def converting_playlists_to_xml(playlists, base_url=""):
    def esc(text):
        if not text:
            return ""
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&apos;"))

    def playlist_extract_video_id_from_thumb(url):
        # Thumbnail URL pattern: https://i.ytimg.com/vi/<video_id>/hqdefault.jpg
        match = re.search(r"/vi/([^/]+)/", url)
        if match:
            return match.group(1)
        return ""

    playlist_entries = []
    for pl in playlists:
        title = esc(pl.get("title", "") or "")
        playlist_id = esc(pl.get("playlist_id", "") or "")
        num_videos = esc(pl.get("num_videos", "") or "")
        author = esc(pl.get("author", "") or "")

        # Extract video IDs from thumbnail URLs
        thumbnails_xml = "\n".join(
            f"<thumbnail>{esc(playlist_extract_video_id_from_thumb(url))}</thumbnail>" for url in pl.get("thumbnails", [])
        )

        playlist_xml = f"""    <entry>
	    <id>{esc(base_url)}/feeds/api/users/{author}/playlists/{playlist_id}</id>
        <playlistId>{playlist_id}</playlistId>
        <yt:playlistId>{playlist_id}</yt:playlistId>
		<published>2008-08-25T10:05:58.000-07:00</published>
		<updated>2008-08-27T22:37:59.000-07:00</updated>
		<category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#playlistLink'/>
		<title type='text'>{title}</title>
		<content type='text' src='{esc(base_url)}/feeds/api/playlists/{playlist_id}'>None</content>
		<link rel='related' type='application/atom+xml' href='{esc(base_url)}/feeds/api/users/{author}'/>
		<link rel='alternate' type='text/html' href='{esc(base_url)}/view_play_list?p={playlist_id}'/>
		<link rel='self' type='application/atom+xml' href='{esc(base_url)}/feeds/api/users/{author}/playlists/{playlist_id}'/>
		<author>
			<name>{author}</name>
			<uri>{esc(base_url)}/feeds/api/users/{author}</uri>
		</author>
		<gd:feedLink rel='http://gdata.youtube.com/schemas/2007#playlist' href='{esc(base_url)}/feeds/api/playlists/{playlist_id}' countHint='15'/>
		<yt:description>None</yt:description>
        <yt:countHint>{num_videos}</yt:countHint>
		<summary></summary>
	</entry>"""
        playlist_entries.append(playlist_xml)

    xmlresponse = f"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'
xmlns:media='http://search.yahoo.com/mrss/'
xmlns:openSearch='http://a9.com/-/spec/opensearchrss/1.0/'
xmlns:gd='http://schemas.google.com/g/2005'
xmlns:yt='http://gdata.youtube.com/schemas/2007'>
    <id>http://gdata.youtube.com/feeds/api/standardfeeds/us/recently_featured</id>
    <updated>2010-12-21T18:59:58.000-08:00</updated>
    <category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#video'/>
    <title type='text'> </title>
    <logo>http://www.youtube.com/img/pic_youtubelogo_123x63.gif</logo>
    <author>
        <name>YouTube</name>
        <uri>http://www.youtube.com/</uri>
    </author>
    <generator version='2.0' uri='http://gdata.youtube.com/'>YouTube data API</generator>
    <openSearch:totalResults>25</openSearch:totalResults>
    <openSearch:startIndex>1</openSearch:startIndex>
    <openSearch:itemsPerPage>25</openSearch:itemsPerPage>{"".join(playlist_entries)}
</feed>"""

    return xmlresponse


@app.route('/feeds/api/users/<string:channelid>/playlists')
def mobile_get_playlists(channelid):
    base_url = request.url_root  # dynamic base URL, e.g. "http://127.0.0.1:5000/"

    if channelid.startswith("@"):
        channelid = channelid[1:]

    # Validate channel id format or search by username
    if not (channelid.startswith('UC') and len(channelid) == 24):
        searched_channel_id = playlist_search_channel_id(channelid)
        if not searched_channel_id:
            return abort(404, description=f"No channel found for search '{channelid}'")
        channelid = searched_channel_id

    data = mobile_felsh_playlist_data(MOBILE_PLAYLIST_API_KEY, channelid)
    if not data:
        return abort(404, description="Channel not found or failed to fetch data")

    playlist_tiles = playlist_find_playlist_tiles(data)
    all_playlists = [playlist_extract_playlist_info(tile) for tile in playlist_tiles]

    xml_output = converting_playlists_to_xml(all_playlists, base_url=base_url)
    return Response(xml_output, content_type="application/xml; charset=utf-8")

# Define the URLs and headers for fetching related videos and video details
related_url_next = "https://www.youtube.com/youtubei/v1/next"
related_url_player = "https://www.youtube.com/youtubei/v1/player"
headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Define the payloads for the requests
def related_create_next_payload(video_id):
    return {
        "context": {
            "client": {
                "hl": "en",
                "gl": "US",
                "clientName": "WEB",
                "clientVersion": "2.20210714.01.00"
            }
        },
        "videoId": video_id
    }

def related_create_player_payload(video_id):
    return {
        "context": {
            "client": {
                "hl": "en",
                "gl": "US",
                "clientName": "WEB",
                "clientVersion": "2.20210714.01.00"
            }
        },
        "videoId": video_id,
        "tinnedMediaPlayback": True
    }

# Define paths for saving and loading cached responses
cache_dir_related = 'assets/cache/related'
cache_dir_videoinfo = 'assets/cache/videoinfo'

# Save response to a file in the cache directory
def related_save_response_to_file(response_json, video_id, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    file_path = os.path.join(cache_dir, f"{video_id}.json")
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(response_json, file, ensure_ascii=False, indent=4)
    print(f"Response saved to {file_path}")

# Load cached response if available
def related_load_cached_response(video_id, cache_dir):
    cache_path = os.path.join(cache_dir, f"{video_id}.json")
    if os.path.exists(cache_path):
        print(f"Cache found for video ID {video_id}. Loading from cache...")
        with open(cache_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        return None

# Recursively find all video IDs in the JSON response
def related_find_all_video_ids_in_json(json_obj):
    video_ids = []

    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            if key == 'videoId':
                video_ids.append(value)
            elif isinstance(value, (dict, list)):
                video_ids.extend(related_find_all_video_ids_in_json(value))

    elif isinstance(json_obj, list):
        for item in json_obj:
            video_ids.extend(related_find_all_video_ids_in_json(item))

    return video_ids

# Fetch related videos or use cached response
def related_fetch_related_videos(video_id):
    try:
        # Check cache first
        print("Checking for cached data for related videos...")
        cached_response = related_load_cached_response(video_id, cache_dir_related)

        if cached_response:
            # Use cached response
            response_json = cached_response
            print("Using cached related videos response.")
        else:
            # If no cache, make API request
            print("Sending request to YouTube API for related videos...")
            response = requests.post(related_url_next, headers=headers, json=related_create_next_payload(video_id))

            if response.status_code == 200:
                response_json = response.json()
                related_save_response_to_file(response_json, video_id, cache_dir_related)
                print("Response fetched from API and saved to cache.")
            else:
                print(f"Request failed with status code: {response.status_code}")
                return []

        # Find all video IDs in the response
        video_ids = related_find_all_video_ids_in_json(response_json)

        # Remove duplicates by converting to a set
        unique_video_ids = set(video_ids)

        if unique_video_ids:
            print("\nUnique related video IDs found:")
            for vid in unique_video_ids:
                print(vid)
            return unique_video_ids
        else:
            print("No videoId found in the response.")
            return []

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return []

# Fetch video details by video ID or use cached response
def related_fetch_video_details(video_id):
    cached_response = related_load_cached_response(video_id, cache_dir_videoinfo)

    if cached_response:
        print(f"Using cached details for video ID {video_id}")
        return cached_response
    else:
        print(f"Fetching video details for {video_id} from API...")
        response = requests.post(related_url_player, headers=headers, json=related_create_player_payload(video_id))

        if response.status_code == 200:
            response_json = response.json()
            related_save_response_to_file(response_json, video_id, cache_dir_videoinfo)
            print(f"Details for video {video_id} fetched and saved to cache.")
            return response_json
        else:
            print(f"Request failed for video ID {video_id} with status code: {response.status_code}")
            return None

# Convert video details to XML format, with error handling for missing keys
def related_convert_to_xml(video_id, video_details, base_url):
    try:
        video_data = video_details.get('videoDetails', {})
        microformat_data = video_details.get('microformat', {}).get('playerMicroformatRenderer', {})

        # Escape special characters using xml.sax.saxutils.escape
        title = escape(video_data.get('title', 'N/A'))
        description = escape(video_data.get('shortDescription', 'N/A'))
        author = escape(video_data.get('author', 'N/A'))
        view_count = escape(str(video_data.get('viewCount', 'N/A')))
        length_seconds = escape(str(video_data.get('lengthSeconds', 'N/A')))
        publish_date = escape(microformat_data.get('publishDate', 'Not available'))
        channel_id = escape(microformat_data.get('externalChannelId', 'N/A'))
        like_count = escape(str(microformat_data.get('likeCount', 'N/A')))
        dislike_count = escape(str(microformat_data.get('dislikeCount', 'N/A')))

        # Return formatted XML
        xml_response = f"""  <entry>
  <id>{escape(base_url)}feeds/api/videos/{escape(video_id)}</id>
  <published>{publish_date}</published>
  <updated>{publish_date}</updated>
  <category scheme="http://gdata.youtube.com/schemas/2007/categories" label="Music" term="Music">Music</category>
  <title type='text'>{title}</title>
  <content type='text'>{description}</content>
  <link rel='http://gdata.youtube.com/schemas/2007#video.in-response-to' type='application/atom+xml' href='{escape(base_url)}feeds/api/videos/{escape(video_id)}'/>
  <link rel='alternate' type='text/html' href='http://vidtape.lol/watch?v={escape(video_id)}&amp;feature=youtube_gdata'/>
  <link rel='http://gdata.youtube.com/schemas/2007#video.responses' type='application/atom+xml' href='{escape(base_url)}feeds/api/videos/{escape(video_id)}/responses'/>
  <link rel='http://gdata.youtube.com/schemas/2007#video.related' type='application/atom+xml' href='{escape(base_url)}feeds/api/videos/{escape(video_id)}/related'/>
  <link rel='http://gdata.youtube.com/schemas/2007#video.captionTracks' type='application/xml' href='{escape(base_url)}timedtext{escape(video_id)}/related'/>
  <link rel='http://gdata.youtube.com/schemas/2007#mobile' type='text/html' href='http://vidtape.lol/details?v={escape(video_id)}'/>
  <link rel='self' type='application/atom+xml' href='{escape(base_url)}feeds/api/videos/{escape(video_id)}'/>
      <author>
        <name>{channel_id}</name>
        <uri>{escape(base_url)}feeds/api/users/{channel_id}</uri>
        <yt:userId>EE{channel_id}</yt:userId>
    </author>
  <gd:comments>
    <gd:feedLink href='{escape(base_url)}feeds/api/videos/{escape(video_id)}/comments' countHint='530'/>
  </gd:comments>
  <yt:hd/>
  <media:group>
    <media:category label='Music' scheme='http://gdata.youtube.com/schemas/2007/categories.cat'>Music</media:category>
    <media:content url='{escape(base_url)}channel_fh264_getvideo?v={escape(video_id)}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='3'/><media:content url='{escape(base_url)}get_480?video_id={escape(video_id)}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='14'/><media:content url='{escape(base_url)}exp_hd?video_id={escape(video_id)}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='8'/>	
	<media:title type='plain'>{title}</media:title>
    <media:description type='plain'>{description}</media:description>
    <media:keywords></media:keywords>
    <media:player url='http://vidtape.lol/get_video?video_id={escape(video_id)}'/>
    <media:thumbnail yt:name='hqdefault' url='http://i.ytimg.com/vi/{escape(video_id)}/hqdefault.jpg' height='240' width='320' time='00:00:00'/>
    <media:thumbnail yt:name='poster' url='http://i.ytimg.com/vi/{escape(video_id)}/hqdefault.jpg' height='240' width='320' time='00:00:00'/>
    <media:thumbnail yt:name='default' url='http://i.ytimg.com/vi/{escape(video_id)}/hqdefault.jpg' height='240' width='320' time='00:00:00'/>
    <yt:duration seconds='{length_seconds}'/>
    <yt:videoid>{escape(video_id)}</yt:videoid>
    <media:credit role='uploader' scheme='urn:youtube' yt:display="{author}" yt:type='partner'>{channel_id}</media:credit>
    <yt:uploaderId>EE{channel_id}</yt:uploaderId>
  </media:group>
  <gd:rating average='5' max='5' min='1' numRaters='5828' rel='http://schemas.google.com/g/2005#overall'/>
  <yt:statistics favoriteCount="{like_count}" viewCount="{view_count}"/>
  <yt:rating numLikes="{like_count}" numDislikes="{dislike_count}"/>
</entry>"""
        return xml_response.strip()

    except Exception as e:
        print(f"Error processing video {video_id}: {e}")
        return f"<video><title>Error fetching details for {video_id}</title></video>"

# Fetch and display video details for all related videos
def related_fetch_and_display_related_videos(video_id, base_url):
    related_video_ids = related_fetch_related_videos(video_id)
    xml_responses = []

    for related_video_id in related_video_ids:
        video_details = related_fetch_video_details(related_video_id)
        if video_details:
            xml_response = related_convert_to_xml(related_video_id, video_details, base_url)
            xml_responses.append(xml_response)

    xml_final_response = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:media="http://search.yahoo.com/mrss/"
      xmlns:gd="http://schemas.google.com/g/2005"
      xmlns:openSearch="http://a9.com/-/spec/opensearch/1.1/">
  <id>http://gdata.youtube.com/feeds/api/videos</id>
  <category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#video'/>
  <title type='text'>YouTube Videos</title>
  <logo>http://www.youtube.com/img/pic_youtubelogo_123x63.gif</logo>
  <link rel='alternate' type='text/html' href='http://www.youtube.com'/>
  <link rel='http://schemas.google.com/g/2005#feed' type='application/atom+xml' href='http://gdata.youtube.com/feeds/api/videos'/>
  <link rel='http://schemas.google.com/g/2005#batch' type='application/atom+xml' href='http://gdata.youtube.com/feeds/api/videos/batch'/>
  <author><name>YouTube/yt2009</name><uri>http://www.youtube.com/</uri></author>
  <generator version='2.0' uri='http://gdata.youtube.com/'>YouTube data API</generator>
  <openSearch:totalResults>5360034</openSearch:totalResults>
  <openSearch:startIndex>1</openSearch:startIndex>
  <openSearch:itemsPerPage>6</openSearch:itemsPerPage>""" + "\n".join(xml_responses) + """\n</feed>"""
    return xml_final_response

# Define the Flask route to fetch related videos in XML format, using the base URL '/api'
@app.route('/feeds/api/videos/<video_id>/related', methods=['GET'])
def related_get_related_videos(video_id):
    try:
        base_url = request.host_url  # Get the base URL of the request
        xml_response = related_fetch_and_display_related_videos(video_id, base_url)
        return xml_response, 200, {'Content-Type': 'application/xml'}
    except Exception as e:
        print(f"Error: {e}")
        return "<error>Error fetching related videos</error>", 500, {'Content-Type': 'application/xml'}
    
    
# === Run ===
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)