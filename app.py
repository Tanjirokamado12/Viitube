import os
import re
import json
import time
import random
import string
import threading
import subprocess
from datetime import datetime, timedelta
import requests
import jwt              # pip install PyJWT
import isodate          # pip install isodate
from flask import Flask, request, Response, send_file, jsonify, redirect
from pytubefix import YouTube
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from urllib.parse import unquote, urlparse
import html

OAUTH2_DEVICE_CODE_URL = 'https://oauth2.googleapis.com/device/code'
OAUTH2_TOKEN_URL = 'https://oauth2.googleapis.com/token'
CLIENT_ID = '627431331381.apps.googleusercontent.com'
CLIENT_SECRET = 'O_HOjELPNFcHO_n_866hamcO'
REDIRECT_URI = ''
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/channels"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "assets", "cache", "search")

app = Flask(__name__)

# Constants
YOUTUBEI_SEARCH_URL = "https://www.googleapis.com/youtubei/v1/search"
YOUTUBEI_PLAYER_URL = "https://www.googleapis.com/youtubei/v1/player"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}
PAYLOAD_TEMPLATE = {
    "query": "",
    "context": {
        "client": {
            "clientName": "WEB",
            "clientVersion": "2.20231221"
        }
    }
}

class GetVideoInfo:
    def build(self, videoId):
        cache_path = f"./assets/cache/videoinfo/{videoId}.json"

        # 🗂️ Check if cached response exists
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as cache_file:
                json_data = json.load(cache_file)
        else:
            # 🌐 Fetch from YouTube
            streamUrl = f"https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8&videoId={videoId}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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

            try:
                json_data = response.json()

                # 💾 Save response to cache
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as cache_file:
                    json.dump(json_data, cache_file, ensure_ascii=False, indent=2)
            except Exception as e:
                return f"Failed to parse or save response: {str(e)}", 500

        # 📦 Extract desired video info
        try:
            title = json_data['videoDetails']['title']
            length_seconds = json_data['videoDetails']['lengthSeconds']
            author = json_data['videoDetails']['author']
        except KeyError as e:
            return f"Missing key: {e}", 400

        # 📤 Format response string
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
    
# Flask Routes
@app.route('/wiitv')
def wiitv():
    return send_file('swf/leanbacklite_wii.swf', mimetype='application/x-shockwave-flash')

# Flask Routes
@app.route('/tv')
def tv():
    return send_file('swf/leanbacklite_v3.swf', mimetype='application/x-shockwave-flash')

@app.route('/complete/search')
def completesearch():
    return send_file('search.js')

# Flask Routes
@app.route('/swf/subtitle_module.swf')
def subtitlemodule():
    return send_file('swf/subtitle_module.swf', mimetype='application/x-shockwave-flash')


@app.route('/apiplayer-loader')
def apiplayerloader():
    return send_file('swf/loader.swf', mimetype='application/x-shockwave-flash')
    
@app.route('/videoplayback')
def apiplayer():
    return send_file('swf/apiplayer.swf', mimetype='application/x-shockwave-flash')


@app.route('/player_204')
def player_204():
    return ""
    
@app.route('/leanback_ajax')
def leanback_ajax():
    return send_file('leanback_ajax')

@app.route('/get_video_info', methods=['GET'])
def get_video_info():
    video_id = request.args.get('video_id')
    if not video_id:
        return jsonify({"error": "Missing video_id parameter"}), 400

    video_info = GetVideoInfo().build(video_id)
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

@app.route('/get_video', methods=['GET'])
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
    #print(message)
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

@app.route('/feeds/ytwii/users/default', methods=["GET"])
def get_youtube_info():
    access_token = request.args.get("oauth_token")

    if not access_token:
        return Response("<?xml version='1.0' encoding='UTF-8'?><error>Access token is required</error>", status=400, content_type="application/xml")

    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "part": "snippet,statistics",
        "mine": "true"
    }

    response = requests.get(YOUTUBE_API_URL, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if "items" in data and data["items"]:
            channel = data["items"][0]
            snippet = channel["snippet"]
            statistics = channel["statistics"]

            channel_name = snippet.get("title", "Unknown Channel")
            thumbnail_url = snippet.get("thumbnails", {}).get("high", {}).get("url", "")

            # Root XML entry
            root = ET.Element("entry", {
                "xmlns": "http://www.w3.org/2005/Atom",
                "xmlns:media": "http://search.yahoo.com/mrss/",
                "xmlns:gd": "http://schemas.google.com/g/2005",
                "xmlns:yt": "http://gdata.youtube.com/schemas/2007"
            })

            ET.SubElement(root, "id").text = "http://192.168.1.18:80/feeds/ytwii/users/default"
            ET.SubElement(root, "published").text = "2010-05-28T09:21:19.000-07:00"
            ET.SubElement(root, "updated").text = "2011-02-09T03:27:42.000-08:00"

            ET.SubElement(root, "category", {
                "scheme": "http://schemas.google.com/g/2005#kind",
                "term": "http://gdata.youtube.com/schemas/2007#userProfile"
            })
            ET.SubElement(root, "category", {
                "scheme": "http://gdata.youtube.com/schemas/2007/channeltypes.cat",
                "term": ""
            })

            ET.SubElement(root, "title", {"type": "text"}).text = channel_name
            ET.SubElement(root, "content", {"type": "text"}).text = ""

            ET.SubElement(root, "link", {
                "rel": "self",
                "type": "application/atom+xml",
                "href": "http://gdata.youtube.com/feeds/ytwii/users/default"
            })

            author = ET.SubElement(root, "author")
            ET.SubElement(author, "name").text = channel_name
            ET.SubElement(author, "uri").text = "http://gdata.youtube.com/feeds/ytwii/users/default"

            ET.SubElement(root, "yt:age").text = "1"
            ET.SubElement(root, "yt:description").text = snippet.get("description", "")

            ET.SubElement(root, "gd:feedLink", {
                "rel": "http://gdata.youtube.com/schemas/2007#user.uploads",
                "href": "http://gdata.youtube.com/feeds/ytwii/users/default/uploads",
                "countHint": "0"
            })

            ET.SubElement(root, "yt:statistics", {
                "lastWebAccess": "2011-02-01T12:45:18.000-08:00",
                "subscriberCount": statistics.get("subscriberCount", "0"),
                "videoWatchCount": "1",
                "viewCount": statistics.get("viewCount", "0"),
                "totalUploadViews": "0"
            })

            thumbnail_url = snippet.get("thumbnails", {}).get("high", {}).get("url", "").replace("https://", "http://")
            ET.SubElement(root, "media:thumbnail", {"url": thumbnail_url})
            ET.SubElement(root, "yt:username").text = channel_name
            ET.SubElement(root, "yt:channelId").text = channel.get("id", "")

            # Convert XML tree to string with proper header
            xml_response = "<?xml version='1.0' encoding='UTF-8'?>\n" + ET.tostring(root, encoding="utf-8").decode("utf-8")
            return Response(xml_response, content_type="application/xml")

        else:
            return Response("<?xml version='1.0' encoding='UTF-8'?><error>No channel found</error>", status=404, content_type="application/xml")

    return Response(f"<?xml version='1.0' encoding='UTF-8'?><error>Invalid token or API request failed</error>", status=response.status_code, content_type="application/xml")

def escape_xml(text):
    return ET.Element("dummy").text if text is None else ET.Element("dummy", {"text": text}).attrib["text"]

def build_subscriptions(ip, port, oauth_token):
    creds = Credentials(oauth_token)
    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.subscriptions().list(
        part="snippet",
        mine=True,
        maxResults=50
    )
    response = request.execute()

    xml_string = '<?xml version="1.0" encoding="UTF-8"?>'
    xml_string += '<feed xmlns:openSearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:media="http://search.yahoo.com/mrss/" xmlns:yt="http://www.youtube.com/xml/schemas/2015">'
    xml_string += f'<link>http://{ip}:{port}/feeds/ytwii/users/default/subscriptions?oauth_token={oauth_token}</link>'
    xml_string += '<title type="text">Subscriptions</title>'
    xml_string += '<openSearch:totalResults></openSearch:totalResults>'
    xml_string += '<generator ver="1.0" uri="http://kamil.cc/">Viitube data API</generator>'
    xml_string += '<openSearch:startIndex>1</openSearch:startIndex>'
    xml_string += '<openSearch:itemsPerPage>40</openSearch:itemsPerPage>'

    for item in response.get("items", []):
        author_name = item["snippet"]["title"]
        author_id = item["snippet"]["resourceId"]["channelId"]
        unread_count = 0  # Placeholder for unread count if applicable
        xml_string += '<entry>'
        xml_string += f'<yt:username>{escape_xml(author_name)}</yt:username>'
        xml_string += f'<yt:channelId>{escape_xml(author_id)}</yt:channelId>'
        xml_string += f'<yt:unreadCount>{unread_count}</yt:unreadCount>'
        xml_string += '</entry>'

    xml_string += '</feed>'
    return xml_string

@app.route('/feeds/ytwii/users/default/subscriptions', methods=['GET'])
def get_subscriptions():
    ip = request.remote_addr
    port = request.environ.get('SERVER_PORT', '5000')
    oauth_token = request.args.get("oauth_token")

    if not oauth_token:
        return Response("<error>Missing OAuth Token</error>", content_type="application/xml")

    xml_data = build_subscriptions(ip, port, oauth_token)
    return Response(xml_data, content_type='application/xml')


def get_channel_uploads(channel_id, oauth_token):
    """Fetch channel name and videos with correct durations"""
    creds = Credentials(token=oauth_token)
    service = build("youtube", "v3", credentials=creds)

    # Fetch the channel name
    channel_info = service.channels().list(part="snippet", id=channel_id).execute()
    channel_name = channel_info["items"][0]["snippet"]["title"] if "items" in channel_info and channel_info["items"] else "Unknown Channel"

    # Get uploads playlist ID
    response = service.channels().list(part="contentDetails", id=channel_id).execute()
    uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Fetch latest videos
    response = service.playlistItems().list(part="snippet,contentDetails", playlistId=uploads_playlist_id, maxResults=30).execute()
    
    videos = []
    video_ids = []

    for item in response["items"]:
        video_id = item["snippet"]["resourceId"]["videoId"]
        video_ids.append(video_id)

        thumbnail_url = item["snippet"]["thumbnails"]["default"]["url"].replace("https://", "http://")

        videos.append({
            "id": f"http://www.youtube.com/watch?v={video_id}",
            "videoid": video_id,
            "published": item["snippet"]["publishedAt"],
            "updated": item["snippet"]["publishedAt"],
            "title": item["snippet"]["title"],
            "description": item["snippet"].get("description", "No description available"),
            "thumbnail": thumbnail_url, 
            "uploader": channel_name,
            "duration": "N/A",  # Placeholder for now
        })

    # Fetch correct video durations
    durations = get_video_durations(video_ids, oauth_token)
    
    # Merge durations into videos list
    for vid in videos:
        vid["duration"] = durations.get(vid["videoid"], "N/A")

    # Fetch video statistics separately
    stats_response = service.videos().list(part="statistics", id=",".join(video_ids)).execute()
    stats_map = {item["id"]: item["statistics"] for item in stats_response["items"]}

    # Merge statistics with videos (handling missing keys)
    for vid in videos:
        video_stats = stats_map.get(vid["videoid"], {})
        vid["view_count"] = video_stats.get("viewCount", "0")
        vid["like_count"] = video_stats.get("likeCount", "0")
        vid["favorite_count"] = video_stats.get("favoriteCount", "0")

    return videos, channel_name  # Return videos AND channel name

def get_video_durations(video_ids, oauth_token):
    """Fetch actual durations for videos"""
    creds = Credentials(token=oauth_token)
    service = build("youtube", "v3", credentials=creds)
    
    response = service.videos().list(part="contentDetails", id=",".join(video_ids)).execute()
    
    durations = {}
    for item in response.get("items", []):
        video_id = item["id"]
        iso_duration = item["contentDetails"]["duration"]
        durations[video_id] = int(isodate.parse_duration(iso_duration).total_seconds())  # Convert to seconds
    
    return durations

def create_xml_feed(videos, channel_name):
    feed = ET.Element("feed", {
        "xmlns": "http://www.w3.org/2005/Atom",
        "xmlns:media": "http://search.yahoo.com/mrss/",
        "xmlns:yt": "http://gdata.youtube.com/schemas/2007",
        "xmlns:gd": "http://schemas.google.com/g/2005"
    })

    ET.SubElement(feed, "id").text = "http://gdata.youtube.com/feeds/ytwii/channel/uploads"
    ET.SubElement(feed, "updated").text = videos[0]["published"] if videos else ""
    ET.SubElement(feed, "title").text = f"{channel_name}"  

    author = ET.SubElement(feed, "author")
    ET.SubElement(author, "name").text = channel_name
    ET.SubElement(author, "uri").text = f"http://www.youtube.com/channel/{videos[0]['videoid']}" if videos else ""

    # Add video entries
    for vid in videos:
        entry = ET.SubElement(feed, "entry")

        ET.SubElement(entry, "id").text = vid["id"]
        ET.SubElement(entry, "youTubeId", {"id": vid["videoid"]}).text = vid["videoid"]
        ET.SubElement(entry, "published").text = vid["published"]
        ET.SubElement(entry, "updated").text = vid["updated"]

        category = ET.SubElement(entry, "category", {
            "scheme": "http://gdata.youtube.com/schemas/2007/categories.cat",
            "label": "-",
            "term": "-"
        })
        category.text = "-"

        ET.SubElement(entry, "title", {"type": "text"}).text = vid["title"]
        ET.SubElement(entry, "content", {"type": "text"}).text = vid["description"]

        ET.SubElement(entry, "link", {
            "rel": "http://gdata.youtube.com/schemas/2007#video.related",
            "href": f"http://192.168.1.18:80/feeds/ytwii/videos/{vid['videoid']}/related"
        })

        author = ET.SubElement(entry, "author")
        ET.SubElement(author, "name").text = vid["uploader"]
        ET.SubElement(author, "uri").text = f"http://192.168.1.18:80/feeds/ytwii/users/{vid['uploader']}"

        comments = ET.SubElement(entry, "gd:comments")
        ET.SubElement(comments, "gd:feedLink", {
            "href": f"http://192.168.1.18:80/feeds/ytwii/videos/{vid['videoid']}/comments",
            "countHint": "530"
        })

        media_group = ET.SubElement(entry, "media:group")
        ET.SubElement(media_group, "media:category", {
            "label": "-",
            "scheme": "http://gdata.youtube.com/schemas/2007/categories.cat"
        }).text = "-"

        ET.SubElement(media_group, "media:content", {
            "url": f"http://192.168.1.18:80/channel_fh264_getvideo?v={vid['videoid']}",
            "type": "video/3gpp",
            "medium": "video",
            "expression": "full",
            "duration": "999",
            "yt:format": "3"
        })

        ET.SubElement(media_group, "media:description", {"type": "plain"}).text = vid["description"]
        ET.SubElement(media_group, "media:keywords").text = "-"

        ET.SubElement(media_group, "media:player", {"url": f"http://www.youtube.com/watch?v={vid['videoid']}"})

        for thumbnail_type in ["hqdefault", "poster", "default"]:
            ET.SubElement(media_group, "media:thumbnail", {
                "yt:name": thumbnail_type,
                "url": f"http://i.ytimg.com/vi/{vid['videoid']}/{thumbnail_type}.jpg",
                "height": "240",
                "width": "320",
                "time": "00:00:00"
            })

        ET.SubElement(media_group, "yt:duration", {"seconds": str(vid["duration"])})
        ET.SubElement(media_group, "yt:videoid", {"id": vid["videoid"]}).text = vid["videoid"]
        ET.SubElement(media_group, "youTubeId", {"id": vid["videoid"]}).text = vid["videoid"]
        ET.SubElement(media_group, "media:credit", {"role": "uploader", "name": vid["uploader"]}).text = vid["uploader"]

        ET.SubElement(entry, "gd:rating", {
            "average": "5",
            "max": "5",
            "min": "1",
            "numRaters": "25",
            "rel": "http://schemas.google.com/g/2005#overall"
        })

        ET.SubElement(entry, "yt:statistics", {
            "favoriteCount": vid.get("favorite_count", "101"),
            "viewCount": vid.get("view_count", "15292")
        })

        ET.SubElement(entry, "yt:rating", {
            "numLikes": vid.get("like_count", "917"),
            "numDislikes": vid.get("favorite_count", "101")
        })

    return ET.tostring(feed, encoding="utf-8").decode("utf-8")


@app.route('/feeds/ytwii/users/<channel_id>/uploads')
def uploads(channel_id):
    """Endpoint to generate YouTube XML feed"""
    oauth_token = request.args.get("oauth_token")
    if not oauth_token:
        return Response("<error>OAuth token is required</error>", status=400, mimetype="application/xml")

    videos, channel_name = get_channel_uploads(channel_id, oauth_token)  # Fetch data
    xml_response = create_xml_feed(videos, channel_name)  # Generate XML

    return Response(xml_response, mimetype="application/xml")

def get_channel_id_from_api(oauth_token):
    """Fetch Channel ID using YouTube API"""
    headers = {"Authorization": f"Bearer {oauth_token}"}
    response = requests.get("https://www.googleapis.com/youtube/v3/channels?part=id&mine=true", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data["items"][0]["id"] if "items" in data else None
    return None

@app.route('/feeds/ytwii/users/default/uploads')
def extract_channel_id_and_redirect():
    """Extract Channel ID from OAuth token and redirect while preserving query arguments"""
    oauth_token = request.args.get("oauth_token")
    if not oauth_token:
        return Response("<error>OAuth token is required</error>", status=400, mimetype="application/xml")

    # Extract channel_id from OAuth token
    try:
        payload = jwt.decode(oauth_token, options={"verify_signature": False})  # Decode without verification
        channel_id = payload.get("channel_id", None)
    except Exception:
        channel_id = None  # If decoding fails, fallback to API call

    # If channel_id not in token, try YouTube API
    if not channel_id:
        channel_id = get_channel_id_from_api(oauth_token)
        if not channel_id:
            return Response("<error>Failed to retrieve channel ID</error>", status=400, mimetype="application/xml")

    # Preserve all original query arguments
    query_params = request.query_string.decode("utf-8")  # Get full query string
    redirect_url = f"/feeds/ytwii/users/{channel_id}/uploads?{query_params}"  # Append query params

    # Redirect while keeping arguments
    return redirect(redirect_url, code=302)

@app.route('/feeds/ytwii/users/default/favorites', methods=["GET"])
def get_liked_videos():
    try:
        # Get OAuth token from request URL
        oauth_token = request.args.get("oauth_token")
        if not oauth_token:
            return Response("<error>OAuth token missing</error>", mimetype="application/xml", status=400)

        # Fetch liked videos (Playlist "LL")
        video_url = "https://www.googleapis.com/youtube/v3/playlistItems"
        video_params = {
            "part": "snippet,contentDetails",
            "playlistId": "LL",
            "maxResults": 150,
            "access_token": oauth_token
        }
        video_response = requests.get(video_url, params=video_params).json()

        if "items" not in video_response or not video_response["items"]:
            return Response("<error>No liked videos found</error>", mimetype="application/xml", status=400)

        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in video_response["items"]]

        # Fetch real video durations, views, and uploader names from videos.list
        video_details_url = "https://www.googleapis.com/youtube/v3/videos"
        video_details_params = {
            "part": "contentDetails,statistics,snippet",  # Fetch uploader name with 'snippet'
            "id": ",".join(video_ids),
            "access_token": oauth_token
        }
        video_details_response = requests.get(video_details_url, params=video_details_params).json()

        durations = {item["id"]: isodate.parse_duration(item["contentDetails"]["duration"]).total_seconds()
                     for item in video_details_response.get("items", [])}
        views = {item["id"]: item["statistics"]["viewCount"]
                 for item in video_details_response.get("items", [])}
        uploaders = {item["id"]: item["snippet"]["channelTitle"]  # Correct uploader name
                     for item in video_details_response.get("items", [])}

        # Generate XML response
        xml_string = '<?xml version="1.0" encoding="UTF-8"?>'
        xml_string += '<feed xmlns:openSearch="http://a9.com/-/spec/opensearch/1.1/" '
        xml_string += 'xmlns:media="http://search.yahoo.com/mrss/" xmlns:yt="http://www.youtube.com/xml/schemas/2015">'
        xml_string += '<title type="text">Liked Videos</title>'
        xml_string += '<generator ver="1.0" uri="http://kamil.cc/">Viitube data API</generator>'
        xml_string += f'<openSearch:totalResults>{len(video_response.get("items", []))}</openSearch:totalResults>'
        xml_string += '<openSearch:startIndex>1</openSearch:startIndex>'
        xml_string += '<openSearch:itemsPerPage>20</openSearch:itemsPerPage>'

        for item in video_response["items"]:
            video_id = item["snippet"]["resourceId"]["videoId"]
            title = item["snippet"]["title"]
            published = item["snippet"]["publishedAt"]
            uploader = uploaders.get(video_id, "Unknown Uploader")  # Correct uploader name
            thumbnail_url = f"http://i.ytimg.com/vi/{video_id}/mqdefault.jpg"  # Convert HTTPS to HTTP
            duration_seconds = int(durations.get(video_id, 0))  # Real video duration
            view_count = views.get(video_id, "0")  # Fetch views correctly

            xml_string += "<entry>"
            xml_string += f"<id>http://localhost:5000/api/videos/{video_id}</id>"
            xml_string += f"<published>{published}</published>"
            xml_string += f"<title type='text'>{title}</title>"
            xml_string += f"<link rel='http://localhost:5000/api/videos/{video_id}/related'/>"
            xml_string += "<author>"
            xml_string += f"<name>{uploader}</name>"  # Correct uploader name
            xml_string += "</author>"
            xml_string += "<media:group>"
            xml_string += f"<media:thumbnail yt:name='mqdefault' url='{thumbnail_url}' height='240' width='320' time='00:00:00'/>"
            xml_string += f"<yt:duration seconds='{duration_seconds}'/>"  # Real video duration
            xml_string += f"<yt:views>{view_count}</yt:views>"  # Correct view count
            xml_string += f"<yt:videoid id='{video_id}'>{video_id}</yt:videoid>"
            xml_string += "</media:group>"
            xml_string += "</entry>"

        xml_string += "</feed>"

        return Response(xml_string, mimetype="application/xml")

    except Exception as e:
        return Response(f"<error>{e}</error>", mimetype="application/xml")

    except Exception as e:
        return Response(f"<error>{e}</error>", mimetype="application/xml")

@app.route('/feeds/ytwii/users/default/playlists', methods=['GET'])
def get_playlists_v2():
    access_token = request.args.get('oauth_token')

    if not access_token:
        return Response("<error>Missing OAuth2 token</error>", mimetype="application/xml", status=401)

    # Fetch playlists from YouTube API v3
    url = "https://www.googleapis.com/youtube/v3/playlists"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    params = {"part": "snippet", "mine": "true", "maxResults": 30}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        username = "me"  # Placeholder since v3 doesn't provide usernames

        # Create XML root element (mimicking API v2)
        root = ET.Element("feed", {
            "xmlns": "http://www.w3.org/2005/Atom",
            "xmlns:media": "http://search.yahoo.com/mrss/",
            "xmlns:openSearch": "http://a9.com/-/spec/opensearchrss/1.0/",
            "xmlns:gd": "http://schemas.google.com/g/2005",
            "xmlns:yt": "http://gdata.youtube.com/schemas/2007"
        })

        ET.SubElement(root, "id").text = f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}/playlists"
        ET.SubElement(root, "updated").text = datetime.utcnow().isoformat() + "Z"
        ET.SubElement(root, "category", {
            "scheme": "http://schemas.google.com/g/2005#kind",
            "term": "http://gdata.youtube.com/schemas/2007#playlistLink"
        })
        ET.SubElement(root, "title", {"type": "text"}).text = f"Playlists of {username}"
        ET.SubElement(root, "logo").text = "http://www.youtube.com/img/pic_youtubelogo_123x63.gif"

        # Navigation Links
        for rel, href in [
            ("related", f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}"),
            ("alternate", "http://www.youtube.com"),
            ("http://schemas.google.com/g/2005#feed", f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}/playlists"),
            ("http://schemas.google.com/g/2005#batch", f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}/playlists/batch"),
            ("self", f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}/playlists?start-index=1&max-results=25"),
            ("next", f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}/playlists?start-index=26&max-results=25"),
        ]:
            ET.SubElement(root, "link", {"rel": rel, "type": "application/atom+xml", "href": href})

        # Author
        author = ET.SubElement(root, "author")
        ET.SubElement(author, "name").text = username
        ET.SubElement(author, "uri").text = f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}"

        ET.SubElement(root, "generator", {"version": "2.1", "uri": "http://gdata.youtube.com"}).text = "YouTube data API"
        ET.SubElement(root, "openSearch:totalResults").text = str(data.get("pageInfo", {}).get("totalResults", 0))
        ET.SubElement(root, "openSearch:startIndex").text = "1"
        ET.SubElement(root, "openSearch:itemsPerPage").text = "25"

        # Convert API v3 data to v2-like XML entries
        for item in data.get("items", []):
            entry = ET.SubElement(root, "entry")
            ET.SubElement(entry, "id").text = f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}/playlists/{item['id']}"
            ET.SubElement(entry, "playlistId").text = item["id"]
            ET.SubElement(entry, "yt:playlistId").text = item["id"]
            ET.SubElement(entry, "published").text = item["snippet"]["publishedAt"]
            ET.SubElement(entry, "updated").text = item["snippet"]["publishedAt"]

            ET.SubElement(entry, "category", {
                "scheme": "http://schemas.google.com/g/2005#kind",
                "term": "http://gdata.youtube.com/schemas/2007#playlistLink"
            })
            ET.SubElement(entry, "title", {"type": "text"}).text = item["snippet"]["title"]
            ET.SubElement(entry, "content", {
                "type": "text",
                "src": f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}/playlists/{item['id']}"
            }).text = "None"

            ET.SubElement(entry, "link", {"rel": "related", "type": "application/atom+xml", "href": f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}"})
            ET.SubElement(entry, "link", {"rel": "alternate", "type": "text/html", "href": f"http://www.youtube.com/view_play_list?p={item['id']}"})
            ET.SubElement(entry, "link", {"rel": "self", "type": "application/atom+xml", "href": f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}/playlists/{item['id']}"})

            author = ET.SubElement(entry, "author")
            ET.SubElement(author, "name").text = item["snippet"]["channelTitle"]
            ET.SubElement(author, "uri").text = f"http://gdata.youtube.com/feeds/youtubei/v1/users/{username}"

            ET.SubElement(entry, "yt:description").text = "None"
            ET.SubElement(entry, "yt:countHint").text = "5"
            ET.SubElement(entry, "summary")

        xml_data = ET.tostring(root, encoding="utf-8").decode()
        return Response(xml_data, mimetype="application/xml")

    else:
        return Response(f"<error>{response.text}</error>", mimetype="application/xml", status=response.status_code)
        
YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_PLAYLIST_URL = "https://www.googleapis.com/youtube/v3/playlists"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
        
@app.route('/feeds/ytwii/playlists/<playlist_id>', methods=['GET'])
def fetch_playlist_videos(playlist_id):
    oauth_token = request.args.get('oauth_token')

    if not oauth_token:
        return Response("<error>Missing oauth_token</error>", status=400, content_type="application/xml")

    headers = {
        "Authorization": f"Bearer {oauth_token}"
    }

    # Fetch playlist details
    playlist_params = {"part": "snippet", "id": playlist_id}
    playlist_response = requests.get(YOUTUBE_PLAYLIST_URL, headers=headers, params=playlist_params)

    if playlist_response.status_code != 200:
        return Response(f"<error>Failed to retrieve playlist</error>", status=playlist_response.status_code, content_type="application/xml")

    playlist_data = playlist_response.json()["items"][0]["snippet"]

    # Fetch playlist items (videos)
    video_params = {"part": "snippet,contentDetails", "playlistId": playlist_id, "maxResults": 30}
    video_response = requests.get(YOUTUBE_PLAYLIST_ITEMS_URL, headers=headers, params=video_params)

    if video_response.status_code != 200:
        return Response(f"<error>Failed to retrieve playlist videos</error>", status=video_response.status_code, content_type="application/xml")

    video_data = video_response.json().get("items", [])

    if not video_data:
        return Response("<error>No videos found in the playlist</error>", status=400, content_type="application/xml")

    # Extract video IDs for statistics lookup
    video_ids = ",".join([
        item["snippet"]["resourceId"]["videoId"]
        for item in video_data
        if "resourceId" in item["snippet"]
    ])

    # Fetch video statistics and details
    stats_params = {"part": "snippet,contentDetails,statistics", "id": video_ids}
    stats_response = requests.get(YOUTUBE_VIDEO_URL, headers=headers, params=stats_params)

    if stats_response.status_code != 200:
        return Response(f"<error>Failed to retrieve video stats</error>", status=stats_response.status_code, content_type="application/xml")

    video_details = {item["id"]: item for item in stats_response.json().get("items", [])}

    # Construct XML response with playlist metadata
    xml_response = f"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom' xmlns:app='http://purl.org/atom/app#' xmlns:media='http://search.yahoo.com/mrss/' xmlns:openSearch='http://a9.com/-/spec/opensearchrss/1.0/' xmlns:gd='http://schemas.google.com/g/2005' xmlns:yt='http://gdata.youtube.com/schemas/2007'>
    <id>http://192.168.1.18:80/feeds/youtubei/v1/playlists/{playlist_id}</id>
    <updated>{playlist_data['publishedAt']}</updated>
    <category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#playlist'/>
    <title type='text'>{playlist_data['title']}</title>
    <subtitle type='text'>{playlist_data.get('description', '')}</subtitle>
    <logo>http://www.youtube.com/img/pic_youtubelogo_123x63.gif</logo>
    <link rel='alternate' type='text/html' href='http://www.youtube.com/view_play_list?p={playlist_id}'/>
    <author>
        <name>{playlist_data['channelTitle']}</name>
        <uri>http://192.168.1.18:80/feeds/youtubei/v1/users/{playlist_data['channelId']}</uri>
    </author>
    <openSearch:totalResults>{len(video_data)}</openSearch:totalResults>
    <openSearch:startIndex>1</openSearch:startIndex>
    <openSearch:itemsPerPage>50</openSearch:itemsPerPage>
    <yt:playlistId>{playlist_id}</yt:playlistId>"""

    # Manually set position starting at 1
    position_counter = 1

    # Add each video entry with full details
    for item in video_data:
        video_id = item['snippet']['resourceId']['videoId']
        video_info = video_details.get(video_id, {})
        stats = video_info.get("statistics", {})
        content_details = video_info.get("contentDetails", {})
        snippet_details = video_info.get("snippet", {})

        view_count = stats.get("viewCount", "0")
        favorite_count = stats.get("favoriteCount", "0")

        # Convert ISO duration to seconds
        iso_duration = content_details.get('duration', "PT0S")  # Default to 'PT0S'
        parsed_duration = isodate.parse_duration(iso_duration)  # Convert to timedelta
        duration_seconds = int(parsed_duration.total_seconds())  # Convert to seconds

        uploader_name = snippet_details.get("channelTitle", "Unknown Uploader")
        uploader_id = snippet_details.get("channelId", "")

        xml_response += f"""
    <entry>
        <id>{video_id}</id>
        <updated>{item['snippet']['publishedAt']}</updated>
        <title>{item['snippet']['title']}</title>
        <link rel='alternate' type='text/html' href='http://www.youtube.com/watch?v={video_id}&amp;feature=youtube_gdata'/>
        <link rel='http://gdata.youtube.com/schemas/2007#video.responses' type='application/atom+xml' href='http://192.168.1.18:80/feeds/youtubei/v1/videos/{video_id}/responses?v=2'/>
        <link rel='http://gdata.youtube.com/schemas/2007#video.related' type='application/atom+xml' href='http://192.168.1.18:80/feeds/youtubei/v1/videos/{video_id}/related?v=2'/>
        <link rel='related' type='application/atom+xml' href='http://192.168.1.18:80/feeds/youtubei/v1/videos/{video_id}?v=2'/>
        <link rel='self' type='application/atom+xml' href='http://gdata.youtube.com/feeds/youtubei/v1/playlists/0A7ED544A0D9877D/00A37F607671690E?v=2'/>
        <author>
            <name>{item['snippet']['videoOwnerChannelTitle']}</name>
            <uri>http://gdata.youtube.com/feeds/youtubei/v1/users/{item['snippet']['channelId']}</uri>
            <yt:userId>{item['snippet']['channelId']}</yt:userId>
        </author>
        <yt:accessControl action='comment' permission='allowed'/>
        <yt:accessControl action='commentVote' permission='allowed'/>
        <yt:accessControl action='videoRespond' permission='moderated'/>
        <yt:accessControl action='rate' permission='allowed'/>
        <yt:accessControl action='embed' permission='allowed'/>
        <yt:accessControl action='syndicate' permission='allowed'/>
        <yt:accessControl action='list' permission='allowed'/>
        <gd:comments>
            <gd:feedLink href='http://gdata.youtube.com/feeds/youtubei/v1/videos/{video_id}/comments?v=2' countHint='1'/>
        </gd:comments>
        <media:group>
            <media:content url='http://192.168.1.18:80/get_video?video_id={video_id}/mp4' type='video/mp4'/>
            <media:credit role='uploader' scheme='urn:youtube' yt:type='partner'>{item['snippet']['channelTitle']}</media:credit>
            <media:description type='plain'></media:description>
            <media:keywords>-</media:keywords>
            <media:player url='http://www.youtube.com/watch?v={video_id}&amp;feature=youtube_gdata'/>
            <media:thumbnail yt:name='hqdefault' url='http://i.ytimg.com/vi/{video_id}/hqdefault.jpg' height='240' width='320' time='00:00:00'/>
            <media:thumbnail yt:name='poster' url='http://i.ytimg.com/vi/{video_id}/0.jpg' height='240' width='320' time='00:00:00'/>
            <media:thumbnail yt:name='default' url='http://i.ytimg.com/vi/{video_id}/0.jpg' height='240' width='320' time='00:00:00'/>
            <media:title type='plain'>{item['snippet']['title']}</media:title>
            <yt:duration seconds='{duration_seconds}'/>
            <yt:uploaded>{item['snippet']['publishedAt']}</yt:uploaded>
            <yt:videoid>{video_id}</yt:videoid>
        </media:group>
        <gd:rating average='5.0' max='5' min='1' numRaters='1' rel='http://schemas.google.com/g/2005#overall'/>
        <yt:statistics favoriteCount='{favorite_count}' viewCount='{view_count}'/>
        <yt:position>{position_counter}</yt:position>
    </entry>"""

        position_counter += 1  # Increment position for next video

    xml_response += "\n</feed>"

    return Response(xml_response, content_type="application/xml")
    
    
HISTORY_CACHE_PATH = "./assets/cache/user/history.json"
processed_videos = set()  # Track unique entries

def fetch_watch_history(oauth_token):
    """Retrieve YouTube watch history from the internal API."""
    url = "https://www.youtube.com/youtubei/v1/browse"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {oauth_token}"
    }
    payload = {
        "context": {
            "client": {
                "hl": "en",
                "gl": "en",
                "clientName": "TVHTML5",
                "clientVersion": "7.20250528.14.00",
                "deviceMake": "Sony",
                "deviceModel": "BRAVIA 8K UR2",
                "platform": "TV"
            }
        },
        "browseId": "FEhistory"
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()
    return None  # Ensure failures don't return JSON

def load_existing_history():
    """Load cached history from a file."""
    if os.path.exists(HISTORY_CACHE_PATH):
        with open(HISTORY_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_history(history_data):
    """Save watch history to a file."""
    os.makedirs(os.path.dirname(HISTORY_CACHE_PATH), exist_ok=True)
    with open(HISTORY_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=4)

def build_watch_history_xml(json_data, ip, port, lang):
    """Convert YouTube history JSON to XML, scanning ALL sections dynamically."""
    view_count_labels = {
        'en': 'views', 'es': 'visualizaciones', 'fr': 'vues', 'de': 'Aufrufe',
        'ja': '回視聴', 'nl': 'weergaven', 'it': 'visualizzazioni'
    }
    view_count_label = view_count_labels.get(lang, 'views')

    xml_string = '<?xml version="1.0" encoding="UTF-8"?>'
    xml_string += '<feed xmlns:openSearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:media="http://search.yahoo.com/mrss/" xmlns:yt="http://www.youtube.com/xml/schemas/2015">'
    xml_string += '<title type="text">Videos</title>'
    xml_string += '<generator ver="1.0" uri="http://your-api.com/">Your Data API</generator>'

    entries_found = False
    processed_videos = set()  # Track unique entries

    def recursive_search(data, xml_string):
        """Search all nested sections to find videoId and create entries dynamically."""
        if isinstance(data, dict):
            if "videoId" in data:
                xml_string = process_video_entry(data, xml_string)  # Create XML entry
            
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    xml_string = recursive_search(value, xml_string)  # Continue deeper search

        elif isinstance(data, list):
            for item in data:
                xml_string = recursive_search(item, xml_string)

        return xml_string  # Return updated XML content

    def process_video_entry(video_data, xml_string):
        """Generate XML entry, ensuring only one entry per unique videoId unless metadata differs."""
        nonlocal entries_found
        entries_found = True

        video_id = video_data.get("videoId", "")
        title = video_data.get("title", {}).get("runs", [{}])[0].get("text", "")
        length_text = video_data.get("lengthText", {}).get("simpleText", "")
        view_count = video_data.get("viewCountText", {}).get("simpleText", "")
        author_name = video_data.get("longBylineText", {}).get("runs", [{}])[0].get("text", "")
        author_id = video_data.get("longBylineText", {}).get("runs", [{}])[0].get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId", "")

        # Track unique entries using a signature
        video_signature = f"{video_id}-{title}-{length_text}"  
        if video_signature in processed_videos:
            return xml_string  # Ignore if duplicate entry detected
        processed_videos.add(video_signature)

        xml_string += '<entry>'
        xml_string += f'<id>http://{ip}:{port}/api/videos/{video_id}</id>'
        xml_string += f'<published>null</published>'
        xml_string += f'<title type="text">(title)</title>'
        xml_string += f'<link rel="alternate" href="http://{ip}:{port}/api/videos/{video_id}/related"/>'
        xml_string += f'<author><name>(authorName)</name><uri>https://www.youtube.com/channel/{author_id}</uri></author>'
        xml_string += '<media:group>'
        xml_string += f'<media:thumbnail url="http://i.ytimg.com/vi/{video_id}/mqdefault.jpg" height="240" width="320"/>'
        xml_string += f'<yt:duration seconds="{length_text}"/>'
        xml_string += f'<yt:uploaderId id="{author_id}">{author_id}</yt:uploaderId>'
        xml_string += f'<yt:videoid id="{video_id}">{video_id}</yt:videoid>'
        xml_string += f'<media:credit role="uploader" name="(authorName)">(authorName)</media:credit>'
        xml_string += '</media:group>'
        xml_string += f'<yt:statistics favoriteCount="0" viewCount="(viewCount)"/>'
        xml_string += '</entry>'

        return xml_string  # Return modified XML content

    xml_string = recursive_search(json_data, xml_string)

    if not entries_found:
        xml_string += '<error>No watch history found</error>'

    xml_string += '</feed>'
    return xml_string


    def recursive_search(data):
        """Search all nested sections to find videoId and create entries dynamically."""
        if isinstance(data, dict):
            if "videoId" in data:
                process_video_entry(data)  # Create XML entry
            
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    recursive_search(value)  # Continue deeper search

        elif isinstance(data, list):
            for item in data:
                recursive_search(item)

    def process_video_entry(video_data):
        """Generate XML entry, ensuring only one entry per unique videoId unless metadata differs."""
        global xml_string, entries_found
        entries_found = True

        video_id = video_data.get("videoId", "")
        title = video_data.get("title", {}).get("runs", [{}])[0].get("text", "")
        length_text = video_data.get("lengthText", {}).get("simpleText", "")
        view_count = video_data.get("viewCountText", {}).get("simpleText", "")
        author_name = video_data.get("longBylineText", {}).get("runs", [{}])[0].get("text", "")
        author_id = video_data.get("longBylineText", {}).get("runs", [{}])[0].get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId", "")

        # Track unique entries using a signature
        video_signature = f"{video_id}-{title}-{length_text}"  
        if video_signature in processed_videos:
            return  # Ignore if duplicate entry detected
        processed_videos.add(video_signature)

        xml_string += '<entry>'
        xml_string += f'<id>http://{ip}:{port}/api/videos/{video_id}</id>'
        xml_string += f'<title type="text">{title}</title>'
        xml_string += f'<link rel="alternate" href="http://{ip}:{port}/api/videos/{video_id}/related"/>'
        xml_string += f'<author><name>{author_name}</name><uri>https://www.youtube.com/channel/{author_id}</uri></author>'
        xml_string += '<media:group>'
        xml_string += f'<media:thumbnail url="http://i.ytimg.com/vi/{video_id}/mqdefault.jpg" height="240" width="320"/>'
        xml_string += f'<yt:duration seconds="{length_text}"/>'
        xml_string += f'<yt:videoid>{video_id}</yt:videoid>'
        xml_string += f'<media:credit role="uploader" name="{author_name}"/>'
        xml_string += '</media:group>'
        xml_string += f'<yt:statistics viewCount="{view_count}"/>'
        xml_string += '</entry>'

    recursive_search(json_data)

    if not entries_found:
        xml_string += '<error>No watch history found</error>'

    xml_string += '</feed>'
    return xml_string

HISTORY_CACHE_PATH = "./assets/cache/history.json"
CACHE_EXPIRATION = 5 * 3600  # 5 hours (in seconds)

def fetch_watch_history(oauth_token):
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
        save_cache(history_data)  # Save response to cache
        return history_data
    return None

def save_cache(data):
    """Save watch history to cache with timestamp."""
    os.makedirs(os.path.dirname(HISTORY_CACHE_PATH), exist_ok=True)
    cache_content = {"timestamp": time.time(), "data": data}
    with open(HISTORY_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache_content, f, indent=4)

def load_cache(oauth_token):
    """Load cached history, checking expiration and refreshing if needed."""
    if os.path.exists(HISTORY_CACHE_PATH):
        with open(HISTORY_CACHE_PATH, "r", encoding="utf-8") as f:
            cache_content = json.load(f)

        # Validate cache structure
        if "timestamp" not in cache_content or "data" not in cache_content:
            #print("Cache file is invalid or outdated. Refreshing watch history...")
            return fetch_watch_history(oauth_token)

        # If cache is older than 5 hours, refresh it at next request
        if time.time() - cache_content["timestamp"] > CACHE_EXPIRATION:
            #print("Cache expired. Fetching new watch history...")
            return fetch_watch_history(oauth_token)

        return cache_content["data"]  # Use cached data if valid
    return fetch_watch_history(oauth_token)  # No cache found, fetch fresh data


def extract_video_ids(history_data):
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

def fetch_video_details(video_ids, oauth_token):
    """Retrieve video details using YouTube API v3 with OAuth token."""
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id={','.join(video_ids)}"
    headers = {"Authorization": f"Bearer {oauth_token}"}

    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

@app.route('/feeds/ytwii/users/default/watch_history', methods=['GET'])
def get_watch_history_xml():
    """API endpoint returning ordered watch history with full metadata."""
    oauth_token = request.args.get('oauth_token')
    if not oauth_token:
        return Response('<error>Missing OAuth token</error>', mimetype='application/xml')

    # Load cache, refresh ONLY IF expired (older than 5 hours)
    history_data = load_cache(oauth_token)
    if not history_data:
        return Response('<error>Failed to retrieve watch history</error>', mimetype='application/xml')

    # Extract unique video IDs in reverse chronological order
    video_ids = extract_video_ids(history_data)
    if not video_ids:
        return Response('<error>No video history found</error>', mimetype='application/xml')

    # Fetch video details using OAuth
    video_details = fetch_video_details(video_ids, oauth_token)
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
            </author>
            <media:group>
                <media:thumbnail url="http://i.ytimg.com/vi/{video_id}/mqdefault.jpg" height="240" width="320"/>
                <yt:duration seconds="{duration_seconds}"/>
                <yt:uploaderId id="{uploader_id}"/>
                <yt:videoid id="{video_id}">{video_id}</yt:videoid>
                <media:credit role="uploader" name="{author_name}">{author_name}</media:credit>
            </media:group>
            <yt:statistics favoriteCount="0" viewCount="{view_count}"/>
        </entry>'''
    
    xml_string += '</feed>'
    return Response(xml_string, mimetype='application/xml')
    
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
                "hl": "en",
                "gl": "en",
                "clientName": "TVHTML5",
                "clientVersion": "7.20250528.14.00",
                "platform": "TV"
            }
        },
        "browseId": "FEmy_youtube"  # Correct browse ID for Watch Later
    }

    response = requests.post(YOUTUBEI_URL, headers=headers, json=payload)

    if response.status_code == 200:
        watch_later_data = response.json()
        save_watch_later_cache(watch_later_data)
        return watch_later_data
        #print(response.text)
    else:
        #print(f"Error fetching Watch Later list: {response.status_code}")
        #print(response.text)
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
                #print("Cache file corrupted, refreshing data...")
                return fetch_watch_later(oauth_token)

            if "timestamp" not in cache_content or "data" not in cache_content:
                #print("Cache file invalid, refreshing...")
                return fetch_watch_later(oauth_token)

            if time.time() - cache_content["timestamp"] > CACHE_EXPIRATION:
                #print("Cache expired. Fetching new Watch Later data...")
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

@app.route('/feeds/ytwii/users/default/watch_later', methods=['GET'])
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
            </author>
            <media:group>
                <media:thumbnail url="http://i.ytimg.com/vi/{video_id}/mqdefault.jpg" height="240" width="320"/>
                <yt:duration seconds="{duration_seconds}"/>
                <yt:uploaderId id="{uploader_id}"/>
                <yt:videoid id="{video_id}">{video_id}</yt:videoid>
                <media:credit role="uploader" name="{author_name}">{author_name}</media:credit>
            </media:group>
            <yt:statistics favoriteCount="0" viewCount="{view_count}"/>
        </entry>'''
    
    xml_string += '</feed>'
    return Response(xml_string, mimetype='application/xml')

# 🧱 Configuration
API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
RELATED_CACHE_DIR = "./assets/cache/Related"
INFO_CACHE_DIR = "./assets/cache/videoinfo"

# 🧼 XML escape utility
def escape(text):
    return (text or "").replace("&", "&amp;") \
                       .replace("<", "&lt;") \
                       .replace(">", "&gt;") \
                       .replace('"', "&quot;") \
                       .replace("'", "&apos;")

# 📦 Fetch and cache related video IDs
def fetch_related_video_ids(video_id):
    os.makedirs(RELATED_CACHE_DIR, exist_ok=True)
    cache_file = f"{RELATED_CACHE_DIR}/{video_id}.json"

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        url = f"https://www.youtube.com/youtubei/v1/next?key={API_KEY}"
        payload = {
            "context": {
                "client": {
                    "hl": "en",
                    "clientName": "WEB",
                    "clientVersion": "2.20210721.00.00"
                }
            },
            "videoId": video_id
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    related_ids = []
    for item in data.get("contents", {}) \
                    .get("twoColumnWatchNextResults", {}) \
                    .get("secondaryResults", {}) \
                    .get("secondaryResults", {}) \
                    .get("results", []):
        video = item.get("compactVideoRenderer")
        if video:
            related_ids.append(video.get("videoId"))
    return related_ids

# 🎥 Fetch and cache video details
def get_video_details(video_id):
    os.makedirs(INFO_CACHE_DIR, exist_ok=True)
    cache_file = f"{INFO_CACHE_DIR}/{video_id}.json"

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        url = f"https://www.youtube.com/youtubei/v1/player?key={API_KEY}"
        payload = {
            "context": {
                "client": {
                    "hl": "en",
                    "clientName": "WEB",
                    "clientVersion": "2.20210721.00.00"
                }
            },
            "videoId": video_id
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    details = data.get("videoDetails", {})
    publish_date = data.get("microformat", {}).get("playerMicroformatRenderer", {}).get("publishDate", "")
    like_count = details.get("likeCount", "")

    return {
        "videoId": details.get("videoId", video_id),
        "title": details.get("title", ""),
        "description": details.get("shortDescription", ""),
        "uploader": details.get("author", ""),
        "publishedDate": publish_date,
        "durationSeconds": details.get("lengthSeconds", ""),
        "likeCount": like_count
    }

# 🌐 Route: /videos/<videoid>/related
@app.route("/feeds/api/videos/<videoid>/relatede", methods=["GET"])
def related(videoid):
    xml_path = f"{RELATED_CACHE_DIR}/{videoid}.xml"

    # Serve cached XML if it exists
    if os.path.exists(xml_path):
        return send_file(xml_path, mimetype="application/xml")

    # Build fresh XML
    related_ids = fetch_related_video_ids(videoid)
    base_url = request.host_url.rstrip("/")

    video_template = """   <entry>
       <id>{ur2}/feeds/api/videos/{videoId}</id>
       <youTubeId id='{videoId}'>{videoId}</youTubeId>
       <published>{publishedDate}</published>
       <updated>{publishedDate}</updated>
       <category scheme='http://schemas.google.com/g/2005#kind' term='{ur2}/schemas/2007#video'/>
       <category scheme='{ur2}/schemas/2007/categories.cat' term='Music' label='Music'/>
       <title type='text'>{title}</title>
       <content type='text'>{description}</content>
       <link rel='alternate' type='text/html' href='http://www.youtube.com/watch?v={videoId}&amp;feature=youtube_gdata'/>
       <link rel='{ur2}/schemas/2007#video.related' type='application/atom+xml' href='{ur2}/feeds/api/videos/{videoId}/related'/>
       <link rel='{ur2}/schemas/2007#mobile' type='text/html' href='http://m.youtube.com/details?v={videoId}'/>
       <link rel='self' type='application/atom+xml' href='{ur2}/feeds/api/videos/--7MeTMkd4s/related/{videoId}'/>
       <author>
           <name>{uploader}</name>
           <uri>{ur2}/feeds/api/users/{uploader}</uri>
       </author>
       <gd:comments>
           <gd:feedLink rel='{ur2}/schemas/2007#comments' href='{ur2}/feeds/api/videos/{videoId}/comments' countHint='1'/>
       </gd:comments>
       <georss:where>
           <gml:Point>
               <gml:pos>37.0 -122.0</gml:pos>
           </gml:Point>
       </georss:where>
       <yt:hd/>
       <media:group>
           <media:category label='Music' scheme='{ur2}/schemas/2007/categories.cat'>Music</media:category>
	   <media:content url='{ur2}/channel_fh264_getvideo?v={videoId}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='3'/>
           <media:description type='plain'>{description}</media:description>
           <media:keywords/>
           <media:player url='http://www.youtube.com/watch?v={videoId}&amp;feature=youtube_gdata_player'/>
           <media:thumbnail url='http://i.ytimg.com/vi/{videoId}/0.jpg' height='360' width='480' time='00:02:06'/>
           <media:thumbnail url='http://i.ytimg.com/vi/{videoId}/1.jpg' height='90' width='120' time='00:01:03'/>
           <media:thumbnail url='http://i.ytimg.com/vi/{videoId}/2.jpg' height='90' width='120' time='00:02:06'/>
           <media:thumbnail url='http://i.ytimg.com/vi/{videoId}/3.jpg' height='90' width='120' time='00:03:09'/>
           <media:title type='plain'>{title}</media:title>
           <yt:videoid id='{videoId}'>{videoId}</yt:videoid>
           <youTubeId id='{videoId}'>{videoId}</youTubeId>
           <yt:duration seconds='{durationSeconds}'/>
           <media:credit role='uploader' name='{uploader}'>{uploader}</media:credit>
       </media:group>
       <gd:rating average='5.0' max='5' min='1' numRaters='5' rel='http://schemas.google.com/g/2005#overall'/>
       <yt:statistics favoriteCount='0' viewCount='1378'/>
   </entry>"""

    video_blocks = ""
    for vid in related_ids:
        info = get_video_details(vid)
        block = video_template.format(
            videoId=escape(info["videoId"]),
            url=escape(f"{base_url}/watch?v={info['videoId']}"),  # 👈 Dynamic base domain
            ur2=escape(f"{base_url}"),  # 👈 Dynamic base domain
            title=escape(info["title"]),
            description=escape(info["description"]),
            uploader=escape(info["uploader"]),
            publishedDate=escape(info["publishedDate"]),
            durationSeconds=escape(info["durationSeconds"]),
            likeCount=escape(info["likeCount"])
        )
        video_blocks += block + "\n"

    xml_content = f"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom' xmlns:openSearch='http://a9.com/-/spec/opensearchrss/1.0/' xmlns:gd='http://schemas.google.com/g/2005' xmlns:media='http://search.yahoo.com/mrss/' xmlns:yt='http://gdata.youtube.com/schemas/2007' xmlns:app='http://purl.org/atom/app#' xmlns:georss='http://www.georss.org/georss' xmlns:gml='http://www.opengis.net/gml'>
   <id>http://gdata.youtube.com/feeds/api/videos/--7MeTMkd4s/related</id>
   <updated>2015-03-26T00:25:12.448Z</updated>
   <category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#video'/>
   <title type='text'>Videos related to 'Kane: "Rain" In-Studio Music Video'</title>
   <logo>http://www.gstatic.com/youtube/img/logo.png</logo>
   <link rel='alternate' type='text/html' href='http://www.youtube.com/results?search=related&amp;search_query=&amp;v=--7MeTMkd4s'/>
   <link rel='related' type='application/atom+xml' href='http://gdata.youtube.com/feeds/api/videos/--7MeTMkd4s'/>
   <link rel='http://schemas.google.com/g/2005#feed' type='application/atom+xml' href='http://gdata.youtube.com/feeds/api/videos/--7MeTMkd4s/related'/>
   <link rel='http://schemas.google.com/g/2005#batch' type='application/atom+xml' href='http://gdata.youtube.com/feeds/api/videos/--7MeTMkd4s/related/batch'/>
   <link rel='self' type='application/atom+xml' href='http://gdata.youtube.com/feeds/api/videos/--7MeTMkd4s/related?start-index=1&amp;max-results=25'/>
   <author>
       <name>YouTube</name>
       <uri>http://www.youtube.com/</uri>
   </author>
   <generator version='2.1' uri='http://gdata.youtube.com'>YouTube data API</generator>
   <openSearch:totalResults>19</openSearch:totalResults>
   <openSearch:startIndex>1</openSearch:startIndex>
   <openSearch:itemsPerPage>25</openSearch:itemsPerPage>
{video_blocks}</feed>"""

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return Response(xml_content, content_type="application/xml")

CACHE_DIR = "./assets/cache/videoinfo"
os.makedirs(CACHE_DIR, exist_ok=True)

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

    # Build XML content
    xmlcontent = f"""<?xml version='1.0' encoding='UTF-8'?>
        <entry>
            <id>http://{baseurl}/feeds/api/videos/{video_id}</id>
            <youTubeId id='{video_id}'>{video_id}</youTubeId>
            <published>{publish_date}T00:00:00.000Z</published>
            <updated>{publish_date}T00:00:00.000Z</updated>
            <category scheme="http://gdata.youtube.com/schemas/2007/categories.cat" label="People &amp; Blogs" term="People &amp; Blogs">People &amp; Blogs</category>
            <title type='text'>{title}</title>
            <content type='text'>{description}</content>
            <link rel="http://gdata.youtube.com/schemas/2007#video.related" href="http://{baseurl}/feeds/api/videos/{video_id}/related"/>
            <author>
                <name>{author}</name>
                <uri>http://{baseurl}/feeds/api/users/{author}</uri>
            </author>
            <gd:comments>
                <gd:feedLink href='http://{baseurl}/feeds/api/videos/{video_id}/comments' countHint='530'/>
            </gd:comments>
            <media:group>
                <media:category label='People &amp; Blogs' scheme='http://gdata.youtube.com/schemas/2007/categories.cat'>People &amp; Blogs</media:category>
                <media:content url='http://{baseurl}/channel_fh264_getvideo?v={video_id}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='3'/><media:content url='http://{baseurl}/get_480?video_id={video_id}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='14'/><media:content url='http://{baseurl}/exp_hd?video_id={video_id}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='8'/>
                <media:description type='plain'>{description}</media:description>
                <media:keywords>genshin, mihoyo, hoyomix, hoyoverse, genshinost, music, soundtrack, orchestra</media:keywords>
                <media:player url='http://www.youtube.com/watch?v={video_id}'/>
                <media:thumbnail yt:name='hqdefault' url='http://i.ytimg.com/vi/{video_id}/hqdefault.jpg' height='240' width='320' time='00:00:00'/>
                <media:thumbnail yt:name='poster' url='http://i.ytimg.com/vi/{video_id}/0.jpg' height='240' width='320' time='00:00:00'/>
                <media:thumbnail yt:name='default' url='http://i.ytimg.com/vi/{video_id}/0.jpg' height='240' width='320' time='00:00:00'/>
                <yt:duration seconds='{duration}'/>
                <yt:videoid id='{video_id}'>{video_id}</yt:videoid>
                <youTubeId id='{video_id}'>{video_id}</youTubeId>
                <media:credit role='uploader' name='{author}'>{author}</media:credit>
            </media:group>
            <gd:rating average='5' max='5' min='1' numRaters='716' rel='http://schemas.google.com/g/2005#overall'/>
            <yt:statistics favoriteCount="0" viewCount="{view_count}/>
            <yt:rating numLikes="0" numDislikes="0"/>
        </entry>"""

    return Response(xmlcontent, mimetype="application/xml")


@app.route('/deviceregistration/v1/devices', methods=['POST'])
def upload_hex():
    return jsonify({
    "id": "amogus",
    "key": "AP+lc79/lqV58X9FLDdn7SiOzH8hDb1ItXMmm25Cb4YDLWZkI+gXBiwwOvcssAY"
}), 200

def generate_device_id():
    charset = "qwertyuiopasdfghjklzxcvbnm1234567890"
    return ''.join(random.choices(charset, k=7))

@app.route('/youtube/accounts/registerDevice', methods=['POST'])
def register_device():
    device_id = generate_device_id()

    # Simulated check—can be replaced with real logic if needed
    used_device_ids = set()
    while device_id in used_device_ids:
        device_id = generate_device_id()

    # Send response similar to Node.js version
    response_text = f"DeviceId={device_id}\nDeviceKey=ULxlVAAVMhZ2GeqZA/X1GgqEEIP1ibcd3S+42pkWfmk="
    return response_text

@app.route('/schemas/2007/categories.cat')
def categories():
    return send_file('categories.cat')

@app.route('/feeds/api/channels')
def channelssearch():
    return send_file('Test')

CACHE_DIR = os.path.join(os.path.dirname(__file__), "assets", "search")

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

class YouTubeSearchAPI:
    """Handles YouTube API requests."""
    def __init__(self, ip, port):
        self.base_url = "https://www.youtube.com/youtubei/v1/search"
        self.api_key = "YOUR_API_KEY"  # Replace with a valid API key
        self.ip = ip
        self.port = port

    def search(self, query, lang="en"):
        """Fetches search results from YouTube."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        payload = {
            "context": {
                "client": {
                    "hl": lang,
                    "gl": "US",
                    "clientName": "WEB",
                    "clientVersion": "2.20210714.01.00"
                }
            },
            "query": query
        }
        try:
            response = requests.post(f"{self.base_url}?key={self.api_key}", json=payload, headers=headers)
            response.raise_for_status()  # Raise error for non-200 responses
            return response.json()
        except requests.exceptions.RequestException as e:
            #print(f"Error fetching YouTube search results: {e}")
            return None

def get_cached_results(query):
    """Checks if cached results exist."""
    file_path = os.path.join(CACHE_DIR, f"{query}.json")
    if os.path.exists(file_path):
        file_age = time.time() - os.path.getmtime(file_path)
        if file_age < 2 * 24 * 60 * 60:  # 2 days in seconds
            with open(file_path, "r") as file:
                return json.load(file)
    return None

def save_results(query, data):
    """Stores search results."""
    file_path = os.path.join(CACHE_DIR, f"{query}.json")
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

class YouTubeSearchXML:
    """Formats YouTube search results into Atom XML."""
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def escape_xml(self, text):
        """Escapes XML special characters."""
        if not text:
            return ""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

    def parse_relative_date(self, text):
        """Converts relative time ('2 days ago') into ISO 8601 format."""
        now = datetime.utcnow()

        if "ago" in text:
            parts = text.split()
            try:
                value = int(parts[0])
            except ValueError:
                return now.strftime("%Y-%m-%dT%H:%M:%S")  # Handle cases like 'Streamed'

            unit = parts[1].lower()
            if "minute" in unit:
                timestamp = now - timedelta(minutes=value)
            elif "hour" in unit:
                timestamp = now - timedelta(hours=value)
            elif "day" in unit:
                timestamp = now - timedelta(days=value)
            elif "week" in unit:
                timestamp = now - timedelta(weeks=value)
            elif "month" in unit:
                timestamp = now - timedelta(days=value * 30)
            elif "year" in unit:
                timestamp = now - timedelta(days=value * 365)
            else:
                timestamp = now
        else:
            try:
                timestamp = datetime.strptime(text, "%b %d, %Y")
            except ValueError:
                timestamp = now

        return timestamp.strftime("%Y-%m-%dT%H:%M:%S")

    def format_video_entry(self, video_data):
        """Formats video entries in XML."""
        video_id = video_data.get("videoId", "")
        title = self.escape_xml(video_data.get("title", {}).get("runs", [{}])[0].get("text", ""))
        published_text = video_data.get("publishedTimeText", {}).get("simpleText", "")
        formatted_published = self.parse_relative_date(published_text)
        # Extract and clean uploader name
        author_raw = video_data.get("ownerText", {}).get("runs", [{}])[0].get("navigationEndpoint", {}) \
        .get("commandMetadata", {}).get("webCommandMetadata", {}).get("url", "")  # e.g., "/c/L%C3%A9toileNoire01"
        author_name = author_raw.replace("/c/", "").replace("/@", "")  # remove path prefix
        author_name = unquote(author_name)  # decode UTF-8 URL encoding
        author_name = self.escape_xml(author_name)
        author_id = video_data.get("lon<path:subpath>ylineText", {}).get("runs", [{}])[0].get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId", "")
        lengthText = video_data.get("lengthText", {}).get("simpleText", "")
        view_count_raw = video_data.get("viewCountText", {}).get("simpleText", "0")
        view_count_clean = view_count_raw.replace(" views", "").replace(",", "")
        
        return f'''       
        <entry>
            <id>http://{self.ip}:{self.port}/feeds/ytwii/videos/{video_id}</id>
            <youTubeId id='{video_id}'>{video_id}</youTubeId>
            <published>{formatted_published}.000Z</published>  
            <updated>{formatted_published}.000Z</updated>  
            <category scheme="http://{self.ip}:{self.port}/schemas/2007/categories.cat" label="Film &amp; Animation" term="Film &amp; Animation">Film &amp; Animation</category>
            <title type='text'>{title}</title>
            <content type='text'></content>
            <link rel="http://gdata.youtube.com/schemas/2007#video.related" href="http://{self.ip}:{self.port}/feeds/api/videos/{video_id}/related"/>
            <author>
                <name>{author_name}</name>
                <uri>http://{self.ip}:{self.port}/feeds/ytwii/users/{author_name}</uri>
            </author>
            <gd:comments>
                <gd:feedLink href='http://{self.ip}:{self.port}/feeds/ytwii/videos/{video_id}/comments' countHint='530'/>
            </gd:comments>
            <media:group>
                <media:category label='Film &amp; Animation' scheme='http://{self.ip}:{self.port}/schemas/2007/categories.cat'>Film &amp; Animation</media:category>
                <media:content url='http://{self.ip}:{self.port}/channel_fh264_getvideo?v={video_id}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='3'/><media:content url='http://{self.ip}:{self.port}/get_480?video_id={video_id}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='14'/><media:content url='http://{self.ip}:{self.port}/exp_hd?video_id={video_id}' type='video/3gpp' medium='video' expression='full' duration='999' yt:format='8'/>
                <media:description type='plain'></media:description>
                <media:keywords>-</media:keywords>
                <media:player url='http://{self.ip}:{self.port}/watch?v={video_id}'/>
                <media:thumbnail yt:name='hqdefault' url='http://i.ytimg.com/vi/{video_id}/hqdefault.jpg' height='240' width='320' time='00:00:00'/>
                <media:thumbnail yt:name='poster' url='http://i.ytimg.com/vi/{video_id}/0.jpg' height='240' width='320' time='00:00:00'/>
                <media:thumbnail yt:name='default' url='http://i.ytimg.com/vi/{video_id}/0.jpg' height='240' width='320' time='00:00:00'/>
                <yt:duration seconds='{lengthText}'/>
                <yt:videoid id='{video_id}'>{video_id}</yt:videoid>
                <youTubeId id='{video_id}'>{video_id}</youTubeId>
                <media:credit role='uploader' name='{author_name}'>{author_name}</media:credit>
            </media:group>
            <gd:rating average='5' max='5' min='1' numRaters='79698' rel='http://schemas.google.com/g/2005#overall'/>
            <yt:statistics favoriteCount="318794" viewCount="{view_count_clean}"/>
            <yt:rating numLikes="286915" numDislikes="31879"/>
        </entry>'''

    def build_search_xml(self, json_data):
        """Builds an XML response from YouTube search results."""
        xml_string = '''<?xml version="1.0" encoding="UTF-8"?>\n<feed>'''

        for section in json_data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", []):
            if "itemSectionRenderer" in section:
                for video_item in section.get("itemSectionRenderer", {}).get("contents", []):
                    if "videoRenderer" in video_item:
                        xml_string += self.format_video_entry(video_item["videoRenderer"])

        xml_string += "\n</feed>"
        return xml_string

@app.route('/feeds/api/videos')
def search():
    query = request.args.get("q")
    ip = request.host.split(":")[0]  # Extracts the IP from the request's host
    port = request.environ.get('SERVER_PORT', '5000')

    if not query:
        return Response("<error>Missing query parameter</error>", mimetype="text/xml")

    cached_data = get_cached_results(query)
    if cached_data:
        json_data = cached_data
    else:
        yt_api = YouTubeSearchAPI(ip, port)
        json_data = yt_api.search(query)
        if json_data:
            save_results(query, json_data)

    if json_data:
        xml_builder = YouTubeSearchXML(ip, port)
        xml_data = xml_builder.build_search_xml(json_data)
        return Response(xml_data, mimetype="text/xml")

    return Response("<error>No results found</error>", mimetype="text/xml")

@app.route('/feeds/api/standardfeeds/<region>/most_discussed')
def most_discussed(region):
    return send_file('Mobile/most_discussed.xml')

@app.route('/feeds/api/standardfeeds/<region>/recently_featured')
def recently_featured(region):
    return send_file('Mobile/recently_featured.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular')
def most_popular(region):
    return send_file('Mobile/most_popular.xml')

@app.route('/feeds/api/standardfeeds/<region>/most_popular_Autos')
def most_popular_Autos(region):
    return send_file('Mobile/most_popular.xml')

@app.route('/feeds/api/users/<region>/favorites')
def mobilefavorites(region):
    return send_file('Mobile/blank.xml')

@app.route('/feeds/api/charts/live/events/recently_broadcasted')
def recently_broadcasted():
    return send_file('Test1')

@app.route('/feeds/api/charts/live/events/live_now')
def live_now():
    return send_file('Test1')
    
def generate_device_id():
    charset = "qwertyuiopasdfghjklzxcvbnm1234567890"
    return ''.join(random.choices(charset, k=7))

SEARCH_DIR = "assets/search"
USER_DIR = "assets/cache/Users"
os.makedirs(SEARCH_DIR, exist_ok=True)
os.makedirs(USER_DIR, exist_ok=True)

def load_json_if_fresh(path: str, max_age: timedelta) -> dict | None:
    if not os.path.exists(path):
        return None

    file_time = datetime.fromtimestamp(os.path.getmtime(path))
    if datetime.now() - file_time < max_age:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return json.loads(content)
        except json.JSONDecodeError:
            # print(f"⚠️ Corrupted JSON file: {path}")
            try:
                os.remove(path)
            except Exception as e:
                # print(f"⚠️ Failed to delete corrupted file: {e}")
                pass  # 👈 This line was missing
    return None
    
def fetch_youtubei(endpoint: str, payload: dict) -> dict:
    url = f"https://www.youtube.com/youtubei/v1/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "X-Youtube-Client-Name": "1",
        "X-Youtube-Client-Version": "2.20210721.00.00"
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def resolve_channel_id(handle: str) -> str | None:
    query = handle.lstrip("@")
    search_path = f"{SEARCH_DIR}/{query}.json"
    payload = {
        "context": { "client": { "clientName": "WEB", "clientVersion": "2.20210721.00.00" } },
        "query": handle
    }
    data = load_json_if_fresh(search_path, timedelta(hours=48)) or fetch_youtubei("search", payload)
    with open(search_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        return data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]\
            ["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"][0]\
            ["channelRenderer"]["channelId"]
    except Exception:
        return None

def normalize_count(text: str) -> int:
    if not text:
        return 0
    text = text.strip().upper().replace(",", "")
    for suffix in ["SUBSCRIBERS", "VIDEOS", "VIEWS"]:
        if suffix in text:
            text = text.replace(suffix, "").strip()
    try:
        if "K" in text:
            return int(float(text.replace("K", "")) * 1000)
        elif "M" in text:
            return int(float(text.replace("M", "")) * 1000000)
        elif "B" in text:
            return int(float(text.replace("B", "")) * 1000000000)
        return int(float(text))
    except ValueError:
        return 0

def normalize_views(text: str) -> int:
    if not text:
        return 0
    text = text.strip().upper().replace(",", "")
    for suffix in ["SUBSCRIBERS", "VIDEOS", "VIEWS"]:
        if suffix in text:
            text = text.replace(suffix, "").strip()
    try:
        if "K" in text:
            return int(float(text.replace("K", "")) * 1000)
        elif "M" in text:
            return int(float(text.replace("M", "")) * 1000000)
        elif "B" in text:
            return int(float(text.replace("B", "")) * 1000000000)
        return int(float(text))
    except ValueError:
        return 0

def parse_duration_to_seconds(duration: str) -> int:
    parts = duration.strip().split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 3:
            hours, minutes, seconds = parts
        elif len(parts) == 2:
            hours = 0
            minutes, seconds = parts
        elif len(parts) == 1:
            hours = 0
            minutes = 0
            seconds = parts[0]
        else:
            return 0
        return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        return 0

def parse_published_date(text: str) -> str:
    if not text:
        return datetime.now().isoformat()
    try:
        return date_parser.parse(text).isoformat()
    except Exception:
        pass
    match = re.match(r"(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago", text.lower())
    if match:
        value, unit = match.groups()
        value = int(value)
        delta_args = {unit + "s": value}
        try:
            return (datetime.now() - timedelta(**delta_args)).isoformat()
        except Exception:
            pass
    return datetime.now().isoformat()

def extract_avatar_url(data: dict) -> str | None:
    header = data.get("header", {}).get("c4TabbedHeaderRenderer", {})
    thumbs = header.get("avatar", {}).get("thumbnails", [])
    for thumb in thumbs:
        url = thumb.get("url", "")
        if "yt3.googleusercontent.com" in url:
            return url
    try:
        microthumbs = data["microformat"]["microformatDataRenderer"]["thumbnail"]["thumbnails"]
        for item in microthumbs:
            url = item.get("url", "")
            if "yt3.googleusercontent.com" in url:
                return url
    except Exception:
        pass
    return thumbs[0].get("url") if thumbs else None

def find_metadata_text(obj: dict | list) -> dict:
    found = {"subscribers": None, "videos": None}
    
    def recurse(node):
        if isinstance(node, dict):
            txt = node.get("text", {})
            if isinstance(txt, dict):
                content = txt.get("content", "")
                if "subscriber" in content.lower() and not found["subscribers"]:
                    found["subscribers"] = content
                if "video" in content.lower() and not found["videos"]:
                    found["videos"] = content
            for value in node.values():
                recurse(value)
        elif isinstance(node, list):
            for item in node:
                recurse(item)
    
    recurse(obj)
    return found

def find_channel_id_in_videocache(user_ident: str) -> str | None:
    ident = user_ident.strip().lower()
    handle_pattern = re.compile(rf"@{re.escape(ident)}$", re.IGNORECASE)

    for filename in os.listdir("assets/cache/videoinfo"):
        if not filename.endswith(".json"):
            continue

        try:
            with open(os.path.join("assets/cache/videoinfo", filename), "r", encoding="utf-8") as f:
                data = json.load(f)

            video_details = data.get("videoDetails", {})
            microformat = data.get("microformat", {}).get("playerMicroformatRenderer", {})

            owner_url = (
                data.get("ownerProfileUrl", "") or
                video_details.get("ownerProfileUrl", "") or
                microformat.get("ownerProfileUrl", "")
            )

            channel_id = (
                data.get("channelId") or
                video_details.get("channelId") or
                microformat.get("externalChannelId")
            )

            display_name = (
                video_details.get("author", "") or
                microformat.get("author", "")
            ).strip().lower()

            if not owner_url and not display_name:
                continue

            # Decode and normalize URL path
            parsed = urlparse(owner_url.lower())
            path = unquote(parsed.path).lstrip('/')
            path = path.lower()

            #print(f"Checking: {filename} with url: {owner_url} → path: {path}")

            # Match @handle
            if handle_pattern.search(path):
                #print(f"Matched handle! Returning channelId: {channel_id}")
                return channel_id

            # Match custom path
            if path in {f"c/{ident}", f"user/{ident}", ident}:
                #print(f"Matched custom URL path! Returning channelId: {channel_id}")
                return channel_id

            # Match display name
            if display_name == ident:
                #print(f"Matched display name! Returning channelId: {channel_id}")
                return channel_id

        except Exception as e:
            #print(f"Error in {filename}: {e}")
            continue

    #print("No match found.")
    return None

def extract_user_info(data: dict, channel_id: str) -> dict:
    header = data.get("header", {}).get("c4TabbedHeaderRenderer", {})
    fallback = data.get("metadata", {}).get("channelMetadataRenderer", {})
    
    # Title and description
    title = header.get("title") or fallback.get("title") or "Unknown Channel"
    description = header.get("description") or fallback.get("description") or ""

    # Avatar (thumbnail)
    avatar = None
    thumbs = header.get("avatar", {}).get("thumbnails", [])
    if thumbs:
        avatar = thumbs[-1].get("url", "")
    if not avatar:
        try:
            microthumbs = data["microformat"]["microformatDataRenderer"]["thumbnail"]["thumbnails"]
            avatar = microthumbs[-1].get("url", "")
        except Exception:
            avatar = ""
    if avatar:
        avatar = avatar.split("?")[0]  # Clean URL

    # Subscriber and video count
    subs_text = header.get("subscriberCountText", {}).get("simpleText", "")
    vids_text = header.get("videoCountText", {}).get("simpleText", "")
    if not subs_text or not vids_text:
        stats = find_metadata_text(data)
        subs_text = subs_text or stats.get("subscribers", "")
        vids_text = vids_text or stats.get("videos", "")

    subscribers = normalize_views(subs_text)
    videos = normalize_views(vids_text)

    return {
        "channelId": channel_id,
        "title": title,
        "description": description,
        "subscribers": subscribers,
        "videos": videos,
        "pfp": avatar,
        "userName": title
    }


def get_user_info(channel_id: str) -> dict:
    path = f"{USER_DIR}/{channel_id}_info.json"
    payload = {
        "context": { "client": { "clientName": "WEB", "clientVersion": "2.20210721.00.00" } },
        "browseId": channel_id
    }
    data = load_json_if_fresh(path, timedelta(hours=48)) or fetch_youtubei("browse", payload)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return extract_user_info(data, channel_id)

def get_uploads(channel_id: str) -> list[dict]:
    path = f"{USER_DIR}/{channel_id}_uploads.json"
    payload = {
        "context": { "client": { "clientName": "WEB", "clientVersion": "2.20210721.00.00" } },
        "browseId": channel_id,
        "params": "EgZ2aWRlb3M%3D"
    }
    data = load_json_if_fresh(path, timedelta(hours=48)) or fetch_youtubei("browse", payload)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        contents = data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][1]\
            ["tabRenderer"]["content"]["richGridRenderer"]["contents"]
        videos = []
        for item in contents:
            video = item.get("richItemRenderer", {}).get("content", {}).get("videoRenderer")
            if video:
                videos.append(video)
        return videos
    except Exception:
        return []

def generate_atom_xml(info: dict, handle: str, base_url: str) -> str:
    now = datetime.now().isoformat()
    id_url = f"{base_url}/feeds/api/users/{handle}"
    channel_uri = f"{base_url}/users/{info['channelId']}"
    uploads_uri = f"{channel_uri}/uploads"
    return f"""<?xml version='1.0' encoding='UTF-8'?>
<entry
    xmlns='http://www.w3.org/2005/Atom'
    xmlns:media='http://search.yahoo.com/mrss/'
    xmlns:gd='http://schemas.google.com/g/2005'
    xmlns:yt='http://gdata.youtube.com/schemas/2007'>
    <id>{id_url}</id>
    <published>{now}</published>
    <updated>{now}</updated>
    <category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#userProfile'/>
    <category scheme='http://gdata.youtube.com/schemas/2007/channeltypes.cat' term=''/>
    <title type='text'>{escape(info['title'])}</title>
    <content type='text'></content>
    <link rel='self' type='application/atom+xml' href='{id_url}'/>
    <author>
        <name>{escape(info['userName'])}</name>
        <uri>{channel_uri}</uri>
    </author>
    <yt:age>1</yt:age>
    <yt:description></yt:description>
    <gd:feedLink rel='http://gdata.youtube.com/schemas/2007#user.uploads' href='{uploads_uri}' countHint='{info['videos']}'/>
    <yt:statistics lastWebAccess='{now}' subscriberCount='{info['subscribers']}' videoWatchCount='1' viewCount='0' totalUploadViews='0'/>
    <media:thumbnail url='{info['pfp']}'/>
    <yt:username>{escape(info['userName'])}</yt:username>
    <yt:channelId>{escape(info['userName'])}</yt:channelId>
</entry>"""

def generate_uploads_atom_xml(info: dict, uploads: list, handle: str, base_url: str) -> str:
    feed_id = f"{base_url}/feeds/api/users/{handle}/uploads"
    now = datetime.utcnow().isoformat() + "Z"
    entries = ""

    for video in uploads:
        video_id = video.get("videoId")
        title = video.get("title", {}).get("runs", [{}])[0].get("text", "")
        description = video.get("descriptionSnippet", {}).get("runs", [{}])[0].get("text", "")
        duration_str = video.get("lengthText", {}).get("simpleText", "")
        duration_sec = parse_duration_to_seconds(duration_str)
        views_str = video.get("viewCountText", {}).get("simpleText", "")
        views = normalize_views(views_str)
        published_text = video.get("publishedTimeText", {}).get("simpleText", "")
        published = parse_published_date(published_text)  # should return ISO8601
        thumbnail = video.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", "")

        entries += f"""
        <entry>
            <id>{base_url}/feeds/api/videos/{video_id}</id>
            <youTubeId id="{video_id}">{video_id}</youTubeId>
            <published>{published}</published>
            <updated>{published}</updated>
            <category scheme="http://gdata.youtube.com/schemas/2007/categories.cat" label="-" term="-">-</category>
            <title type="text"><![CDATA[{title}]]></title>
            <content type="text"><![CDATA[{description}]]></content>
            <link rel="http://gdata.youtube.com/schemas/2007#video.related" href="{base_url}/feeds/api/videos/{video_id}/related"/>
            <author>
                <name>{info['userName']}</name>
                <uri>{base_url}/feeds/api/users/{info['userName']}</uri>
            </author>
            <gd:comments>
                <gd:feedLink href="{base_url}/feeds/api/videos/{video_id}/comments" countHint="530"/>
            </gd:comments>
            <media:group>
                <media:category label="-" scheme="http://gdata.youtube.com/schemas/2007/categories.cat">-</media:category>
                <media:content url="{base_url}/channel_fh264_getvideo?v={video_id}" type="video/3gpp" medium="video" expression="full" duration="{duration_sec}" yt:format="3"/>
                <media:description type="plain"><![CDATA[{description}]]></media:description>
                <media:keywords>-</media:keywords>
                <media:player url="http://www.youtube.com/watch?v={video_id}"/>
                <media:thumbnail yt:name="hqdefault" url="http://i.ytimg.com/vi/{video_id}/hqdefault.jpg" height="240" width="320" time="00:00:00"/>
                <media:thumbnail yt:name="poster" url="http://i.ytimg.com/vi/{video_id}/0.jpg" height="240" width="320" time="00:00:00"/>
                <media:thumbnail yt:name="default" url="http://i.ytimg.com/vi/{video_id}/0.jpg" height="240" width="320" time="00:00:00"/>
                <yt:duration seconds="{duration_sec}"/>
                <yt:videoid id="{video_id}">{video_id}</yt:videoid>
                <youTubeId id="{video_id}">{video_id}</youTubeId>
                <media:credit role="uploader" name="{info['userName']}">{info['userName']}</media:credit>
            </media:group>
            <gd:rating average="5" max="5" min="1" numRaters="0" rel="http://schemas.google.com/g/2005#overall"/>
            <yt:statistics favoriteCount="0" viewCount="{views}"/>
            <yt:rating numLikes="0" numDislikes="0"/>
        </entry>
        """

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'
      xmlns:media='http://search.yahoo.com/mrss/'
      xmlns:openSearch='http://a9.com/-/spec/opensearchrss/1.0/'
      xmlns:gd='http://schemas.google.com/g/2005'
      xmlns:yt='http://gdata.youtube.com/schemas/2007'>
    <id>{feed_id}</id>
    <updated>{now}</updated>
    <category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#video'/>
    <title type='text'>Uploads by {handle}</title>
    <logo>http://www.youtube.com/img/pic_youtubelogo_123x63.gif</logo>
    <author>
        <name>{info['userName']}</name>
        <uri>{base_url}/feeds/api/users/{info['userName']}</uri>
    </author>
    <generator version='2.0' uri='http://gdata.youtube.com/'>YouTube data API</generator>
    <openSearch:totalResults>{len(uploads)}</openSearch:totalResults>
    <openSearch:startIndex>1</openSearch:startIndex>
    <openSearch:itemsPerPage>{len(uploads)}</openSearch:itemsPerPage>
    {entries}
</feed>"""

@app.route("/feeds/api/users/<user_ident>")
@app.route("/feeds/api/channels/<user_ident>")
def serve_user_profile(user_ident):
    handle = f"@{user_ident}"
    channel_id = resolve_channel_id(handle) or find_channel_id_in_videocache(user_ident)

    if not channel_id:
        for filename in os.listdir("assets/cache/videoinfo"):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join("assets/cache/videoinfo", filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cid = data.get("channelId")
                    cname = data.get("channelName", "").lstrip("@")
                    if cname.lower() == user_ident.lower() or cid.lower() == user_ident.lower():
                        channel_id = cid
                        break
                except Exception:
                    continue

    if not channel_id:
        return Response("Channel not found", status=404)

    info = get_user_info(channel_id)
    base_url = f"{request.scheme}://{request.host}"
    xml_response = generate_atom_xml(info, user_ident, base_url)
    return Response(xml_response, mimetype="application/atom+xml")


@app.route("/feeds/api/users/<user_ident>/uploads")
@app.route("/users/<user_ident>/uploads")
def serve_user_uploads(user_ident):
    if not user_ident.startswith("UC"):
        handle = f"@{user_ident}"
        channel_id = resolve_channel_id(handle) or find_channel_id_in_videocache(user_ident)
    else:
        channel_id = user_ident


    if not channel_id:
        for filename in os.listdir("assets/cache/videoinfo"):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join("assets/cache/videoinfo", filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cid = data.get("channelId")
                    cname = data.get("channelName", "").lstrip("@")
                    if cname.lower() == user_ident.lower() or cid.lower() == user_ident.lower():
                        channel_id = cid
                        break
                except Exception:
                    continue

    if not channel_id:
        return Response("Channel not found", status=404)

    info = get_user_info(channel_id)
    uploads = get_uploads(channel_id)
    base_url = f"{request.scheme}://{request.host}"
    xml_response = generate_uploads_atom_xml(info, uploads, user_ident, base_url)
    return Response(xml_response, mimetype="application/atom+xml")


TEMPLATE_PATH = 'player.json'
CACHE_DIR = 'assets/cache/innertube'
PLACEHOLDER = b'thevideoiid'  # must be 11 bytes for exact replacement

@app.route('/youtubei/v1/player', methods=['GET', 'POST'])
def youtube_player():
    video_id = request.args.get('id', '').strip()

    if not video_id:
        return jsonify({"error": "Missing 'id' parameter"}), 400

    if len(video_id) != 11:
        return jsonify({"error": "Video ID must be 11 characters"}), 400

    # Prepare cache path
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{video_id}.json")

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
            #print(f"[ERROR] Failed to fetch info: {response.status_code}")
            return {"error": "Failed to fetch video info"}

        try:
            data = response.json()
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except Exception as e:
            #print(f"[ERROR] JSON parse error: {e}")
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
@app.route('/geeeeeeeeeeeeeet_video', methods=['GET'])
def serve_video():
    video_id = get_clean_video_id()

    if not video_id:
        return "Missing or invalid video_id parameter", 400

    try:
        video_path = download_video(video_id)
        return send_file(video_path, as_attachment=True)
    except Exception as e:
        #print(f"[SERVER ERROR] {e}")
        return "Internal server error", 500

# Flask Routes
@app.route('/youtube/v3/activities')
def activites():
    return send_file('browse.json', mimetype='application/x-shockwave-flash')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
