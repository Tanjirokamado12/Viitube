from flask import Flask, request, Response, send_file,jsonify, redirect
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from pytubefix import YouTube
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import subprocess
import os
import isodate  # Install with `pip install isodate`
import jwt  # Install with `pip install PyJWT`
import datetime
import time
import json
import random
import string

OAUTH2_DEVICE_CODE_URL = 'https://oauth2.googleapis.com/device/code'
OAUTH2_TOKEN_URL = 'https://oauth2.googleapis.com/token'
CLIENT_ID = '627431331381.apps.googleusercontent.com'
CLIENT_SECRET = 'O_HOjELPNFcHO_n_866hamcO'
REDIRECT_URI = ''
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/channels"

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
        
        try:
            json_data = response.json()
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
    
# Flask Routes
@app.route('/wiitv')
def wiitv():
    return send_file('swf/leanbacklite_wii.swf', mimetype='application/x-shockwave-flash')
# Flask Routes

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

YOUTUBEI_SEARCH_URL = "https://www.youtube.com/youtubei/v1/search"
YOUTUBE_V3_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
CACHE_DIR = "./assets/cache/search"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_file(query):
    return os.path.join(CACHE_DIR, f"{query}.json")

def is_cache_valid(cache_file):
    if not os.path.exists(cache_file):
        return False
    last_modified = os.path.getmtime(cache_file)
    return (time.time() - last_modified) < (5 * 24 * 60 * 60)  # 5 days

def fetch_videos(query, oauth_token=None):
    cache_file = get_cache_file(query)
    videos = []  # Ensure videos is initialized
    
    # Check cache validity
    if is_cache_valid(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)
    
    if oauth_token:
        headers = HEADERS.copy()
        headers["Authorization"] = f"Bearer {oauth_token}"
        params = {"part": "snippet", "q": query, "type": "video", "maxResults": 50}

        try:
            response = requests.get(YOUTUBE_V3_SEARCH_URL, headers=headers, params=params)
            response.raise_for_status()  # Check for HTTP errors
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return []  # Return an empty list if API fails
        
        video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
        video_stats = {}

        if video_ids:
            try:
                stats_response = requests.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    headers=headers,
                    params={"part": "contentDetails,statistics", "id": ",".join(video_ids)}
                )
                stats_response.raise_for_status()
                stats_data = stats_response.json().get("items", {})
                video_stats = {item["id"]: item for item in stats_data}
            except requests.exceptions.RequestException as e:
                print(f"Error fetching video stats: {e}")

        for item in data.get("items", []):
            video_id = item["id"]["videoId"]
            details = video_stats.get(video_id, {})

            duration = details.get("contentDetails", {}).get("duration", "PT0S")
            parsed_duration = isodate.parse_duration(duration)
            duration_seconds = int(parsed_duration.total_seconds())

            view_count = details.get("statistics", {}).get("viewCount", "0")

            videos.append({
                "title": item["snippet"]["title"],
                "videoId": video_id,
                "author": item["snippet"]["channelTitle"],
                "authorId": item["snippet"]["channelId"],
                "thumbnailUrl": item["snippet"]["thumbnails"]["high"]["url"],
                "viewCount": view_count,
                "duration": str(duration_seconds),
                "published": item["snippet"]["publishedAt"]
            })
    
    # Save results to cache
    try:
        with open(cache_file, "w") as f:
            json.dump(videos, f, indent=4)
    except Exception as e:
        print(f"Error saving to cache: {e}")

    return videos

@app.route("/feeds/api/videos", methods=["GET"])
def search():
    query = request.args.get("q")
    oauth_token = request.args.get("oauth_token")  # Extract OAuth token if provided
    if not query:
        return "Query parameter 'q' is required", 400

    videos = fetch_videos(query, oauth_token)
    xml_response = create_xml_response(videos)
    
    return Response(xml_response, mimetype="application/xml")

def create_xml_response(videos):
    # Extract the request's base host (IP or domain)
    base_url = f"http://{request.host}/feeds/api/videos/"

    root = ET.Element("feed", {
        "xmlns:openSearch": "http://a9.com/-/spec/opensearch/1.1/",
        "xmlns:media": "http://search.yahoo.com/mrss/",
        "xmlns:yt": "http://www.youtube.com/xml/schemas/2015",
        "xmlns:gd": "http://schemas.google.com/g/2005"
    })
    ET.SubElement(root, "title", {"type": "text"}).text = "Videos"
    ET.SubElement(root, "generator", {"ver": "1.0", "uri": "http://kamil.cc/"}).text = "Viitube data API"
    ET.SubElement(root, "openSearch:totalResults").text = str(len(videos))
    ET.SubElement(root, "openSearch:startIndex").text = "1"
    ET.SubElement(root, "openSearch:itemsPerPage").text = "20"

    for video in videos:
        entry = ET.SubElement(root, "entry")
        video_url = f"{base_url}{video['videoId']}"

        ET.SubElement(entry, "id").text = video_url
        ET.SubElement(entry, "youTubeId", {"id": video["videoId"]}).text = video["videoId"]
        ET.SubElement(entry, "published").text = video["published"]
        ET.SubElement(entry, "updated").text = video["published"]
        ET.SubElement(entry, "category", {
            "scheme": "http://gdata.youtube.com/schemas/2007/categories.cat",
            "label": video.get("category", "Unknown"),
            "term": video.get("category", "Unknown")
        }).text = video.get("category", "Unknown")

        ET.SubElement(entry, "title", {"type": "text"}).text = video["title"]
        ET.SubElement(entry, "content", {"type": "text"}).text = video.get("description", "")

        ET.SubElement(entry, "link", {
            "rel": "http://gdata.youtube.com/schemas/2007#video.related",
            "href": f"{video_url}/related"
        })

        author = ET.SubElement(entry, "author")
        ET.SubElement(author, "name").text = video['authorId']
        ET.SubElement(author, "uri").text = f"http://{request.host}/feeds/api/users/{video['authorId']}"

        ET.SubElement(entry, "gd:comments").append(
            ET.Element("gd:feedLink", {
                "href": f"{video_url}/comments",
                "countHint": "530"
            })
        )

        media_group = ET.SubElement(entry, "media:group")
        ET.SubElement(media_group, "media:category", {
            "label": video.get("category", "Unknown"),
            "scheme": "http://gdata.youtube.com/schemas/2007/categories.cat"
        }).text = video.get("category", "Unknown")

        for fmt, url in [("3", "channel_fh264_getvideo"), ("14", "get_480"), ("8", "exp_hd")]:
            ET.SubElement(media_group, "media:content", {
                "url": f"http://{request.host}/{url}?video_id={video['videoId']}",
                "type": "video/3gpp",
                "medium": "video",
                "expression": "full",
                "duration": video["duration"],
                "yt:format": fmt
            })

        ET.SubElement(media_group, "media:description", {"type": "plain"}).text = video.get("description", "")
        ET.SubElement(media_group, "media:keywords").text = video.get("keywords", "Unknown")
        ET.SubElement(media_group, "media:player", {"url": f"http://www.youtube.com/watch?v={video['videoId']}"})

        for thumb_type in ["hqdefault", "poster", "default"]:
            ET.SubElement(media_group, "media:thumbnail", {
                "yt:name": thumb_type,
                "url": f"http://i.ytimg.com/vi/{video['videoId']}/{thumb_type}.jpg",
                "height": "240",
                "width": "320",
                "time": "00:00:00"
            })

        ET.SubElement(media_group, "yt:duration", {"seconds": video["duration"]})
        ET.SubElement(media_group, "yt:videoid", {"id": video["videoId"]}).text = video["videoId"]
        ET.SubElement(media_group, "youTubeId", {"id": video["videoId"]}).text = video["videoId"]
        ET.SubElement(media_group, "media:credit", {
            "role": "uploader",
            "name": video["authorId"]
        }).text = video["author"]

        ET.SubElement(entry, "gd:rating", {
            "average": "5",
            "max": "5",
            "min": "1",
            "numRaters": "181",
            "rel": "http://schemas.google.com/g/2005#overall"
        })

        ET.SubElement(entry, "yt:statistics", {
            "favoriteCount": "726",
            "viewCount": video["viewCount"]
        })
        ET.SubElement(entry, "yt:rating", {
            "numLikes": "6539",
            "numDislikes": "726"
        })
        
        ET.SubElement(entry, "yt:channelid").text = video["authorId"]
     
    return ET.tostring(root, encoding="utf-8", method="xml")

    
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
    print(message)
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

@app.route("/feeds/api/users/default", methods=["GET"])
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

            ET.SubElement(root, "id").text = "http://192.168.1.18:80/feeds/api/users/default"
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
                "href": "http://gdata.youtube.com/feeds/api/users/default"
            })

            author = ET.SubElement(root, "author")
            ET.SubElement(author, "name").text = channel_name
            ET.SubElement(author, "uri").text = "http://gdata.youtube.com/feeds/api/users/default"

            ET.SubElement(root, "yt:age").text = "1"
            ET.SubElement(root, "yt:description").text = snippet.get("description", "")

            ET.SubElement(root, "gd:feedLink", {
                "rel": "http://gdata.youtube.com/schemas/2007#user.uploads",
                "href": "http://gdata.youtube.com/feeds/api/users/default/uploads",
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
    xml_string += f'<link>http://{ip}:{port}/feeds/api/users/default/subscriptions?oauth_token={oauth_token}</link>'
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

@app.route('/feeds/api/users/default/subscriptions', methods=['GET'])
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

    ET.SubElement(feed, "id").text = "http://gdata.youtube.com/feeds/api/channel/uploads"
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
            "href": f"http://192.168.1.18:80/feeds/api/videos/{vid['videoid']}/related"
        })

        author = ET.SubElement(entry, "author")
        ET.SubElement(author, "name").text = vid["uploader"]
        ET.SubElement(author, "uri").text = f"http://192.168.1.18:80/feeds/api/users/{vid['uploader']}"

        comments = ET.SubElement(entry, "gd:comments")
        ET.SubElement(comments, "gd:feedLink", {
            "href": f"http://192.168.1.18:80/feeds/api/videos/{vid['videoid']}/comments",
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


@app.route("/feeds/api/users/<channel_id>/uploads")
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

@app.route("/feeds/api/users/default/uploads")
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
    redirect_url = f"/feeds/api/users/{channel_id}/uploads?{query_params}"  # Append query params

    # Redirect while keeping arguments
    return redirect(redirect_url, code=302)

@app.route("/feeds/api/users/default/favorites", methods=["GET"])
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
        xml_string += '<generator ver="1.0" uri="http://kamil.cc/">Liinback data API</generator>'
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

@app.route('/feeds/api/users/default/playlists', methods=['GET'])
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
        ET.SubElement(root, "updated").text = datetime.datetime.utcnow().isoformat() + "Z"
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
        
@app.route('/feeds/api/playlists/<playlist_id>', methods=['GET'])
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
    
ASSETS_DIR = "./assets"

ASSETS_FOLDER = "./assets"
os.makedirs(ASSETS_FOLDER, exist_ok=True)

@app.route('/exp_hd', methods=['GET'])
def exphd():
    video_id = request.args.get('video_id')
    if not video_id:
        return "Missing video_id parameter", 400

    mp4_path = os.path.join(ASSETS_FOLDER, f"{video_id}.mp4")

    # Serve the .mp4 file if it already exists
    if os.path.exists(mp4_path):
        return send_file(mp4_path, as_attachment=True)

    try:
        # Download the highest-resolution MP4 video using pytubefix
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        stream = yt.streams.get_highest_resolution()
        stream.download(output_path=ASSETS_FOLDER, filename=f"{video_id}.mp4")
    except Exception as e:
        return f"Error downloading video: {str(e)}", 500

    # Ensure the file exists before serving
    if os.path.exists(mp4_path):
        return send_file(mp4_path, as_attachment=True)
    
    return "Download failed, file not found", 500

@app.route('/channel_fh264_getvideo', methods=['GET'])
def channel_fh264_getvideo():
    video_id = request.args.get('video_id')
    if not video_id:
        return "Missing video_id parameter", 400

    mp4_path = os.path.join(ASSETS_FOLDER, f"{video_id}.mp4")

    # Serve the .mp4 file if it already exists
    if os.path.exists(mp4_path):
        return send_file(mp4_path, as_attachment=True)

    try:
        # Download the highest-resolution MP4 video using pytubefix
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        stream = yt.streams.get_highest_resolution()
        stream.download(output_path=ASSETS_FOLDER, filename=f"{video_id}.mp4")
    except Exception as e:
        return f"Error downloading video: {str(e)}", 500

    # Ensure the file exists before serving
    if os.path.exists(mp4_path):
        return send_file(mp4_path, as_attachment=True)
    
    return "Download failed, file not found", 500
    
    # File to store registered devices
REGISTRATION_FILE = "Registration.txt"

def generate_device_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def generate_device_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))

@app.route("/youtube/accounts/registerDevice", methods=["POST"])
def register_device():
    serial_number = request.args.get("serialNumber")  # Get from query parameters

    if not serial_number:
        return "Error: Missing serial number", 400  # Simple text response

    device_id = generate_device_id()
    device_key = generate_device_key()

    with open(REGISTRATION_FILE, "a") as file:
        file.write(f"Serial: {serial_number}\nDeviceId={device_id}\nDeviceKey={device_key}\n\n")

    return f"DeviceId={device_id}\nDeviceKey=ULxlVAAVMhZ2GeqZA/X1GgqEEIP1ibcd3S+42pkWfmk="  # Simple text response
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
