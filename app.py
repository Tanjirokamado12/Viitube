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
    
    YOUTUBE_SEARCH_URL = "https://www.youtube.com/youtubei/v1/search?key=YOUR_API_KEY"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

def create_xml_response(videos):
    root = ET.Element("feed", {
        "xmlns:openSearch": "http://a9.com/-/spec/opensearch/1.1/",
        "xmlns:media": "http://search.yahoo.com/mrss/",
        "xmlns:yt": "http://www.youtube.com/xml/schemas/2015"
    })
    ET.SubElement(root, "title", {"type": "text"}).text = "Videos"
    ET.SubElement(root, "generator", {"ver": "1.0", "uri": "http://kamil.cc/"}).text = "Viitube data API"
    ET.SubElement(root, "openSearch:totalResults").text = str(len(videos))
    ET.SubElement(root, "openSearch:startIndex").text = "1"
    ET.SubElement(root, "openSearch:itemsPerPage").text = "20"

    for video in videos:
        entry = ET.SubElement(root, "entry")
        ET.SubElement(entry, "id").text = f"http://192.168.1.192:443/api/videos/{video['videoId']}"
        ET.SubElement(entry, "published").text = video["published"]
        ET.SubElement(entry, "title", {"type": "text"}).text = video["title"]
        ET.SubElement(entry, "link", {"rel": f"http://192.168.1.192:443/api/videos/{video['videoId']}/related"})

        author = ET.SubElement(entry, "author")
        ET.SubElement(author, "name").text = video["author"]
        ET.SubElement(author, "uri").text = f"https://www.youtube.com/channel/{video['authorId']}"

        media_group = ET.SubElement(entry, "media:group")
        ET.SubElement(media_group, "media:thumbnail", {
            "yt:name": "hqdefault",
            "url": f"http://i.ytimg.com/vi/{video['videoId']}/hqdefault.jpg",
            "height": "240",
            "width": "320",
            "time": "00:00:00"
        })
        ET.SubElement(media_group, "yt:duration", {"seconds": video["duration"]})
        ET.SubElement(media_group, "yt:uploaderId", {"id": video["authorId"]}).text = video["authorId"]
        ET.SubElement(media_group, "yt:videoid", {"id": video["videoId"]}).text = video["videoId"]
        ET.SubElement(media_group, "media:credit", {"role": "uploader", "name": video["author"]}).text = video["author"]

        ET.SubElement(entry, "yt:statistics", {
            "favoriteCount": "0",
            "viewCount": video["viewCount"]
        })

    return ET.tostring(root, encoding="utf-8", method="xml")

@app.route("/feeds/api/videos", methods=["GET"])
def search():
    query = request.args.get("q")
    if not query:
        return "Query parameter 'q' is required", 400

    payload = {
        "context": {
            "client": {
                "hl": "en",
                "gl": "US",
                "clientName": "WEB",
                "clientVersion": "2.20210714.01.00"
            }
        },
        "query": query
    }

    response = requests.post(YOUTUBEI_SEARCH_URL, json=payload, headers=HEADERS)
    data = response.json()

    primary_contents = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])

    videos = []
    for section in primary_contents:
        for item in section.get("itemSectionRenderer", {}).get("contents", []):
            video = item.get("videoRenderer")
            if video:
                videos.append({
                    "title": video.get("title", {}).get("runs", [{}])[0].get("text", "No Title"),
                    "videoId": video.get("videoId", "No Video ID"),
                    "author": video.get("ownerText", {}).get("runs", [{}])[0].get("text", "Unknown Author"),
                    "authorId": video.get("ownerText", {}).get("runs", [{}])[0].get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId", ""),
                    "thumbnailUrl": video.get("thumbnail", {}).get("thumbnails", [{}])[0].get("url", ""),
                    "viewCount": video.get("viewCountText", {}).get("simpleText", "0 views"),
                    "duration": video.get("lengthText", {}).get("simpleText", "Unknown Duration"),
                    "published": video.get("publishedTimeText", {}).get("simpleText", "Unknown Time")
                })

    xml_response = create_xml_response(videos)
    return Response(xml_response, mimetype="application/xml")
    
# Ensure 'assets' folder exists
if not os.path.exists("assets"):
    os.makedirs("assets")
    
# Ensure the assets folder exists
ASSETS_FOLDER = 'assets'
os.makedirs(ASSETS_FOLDER, exist_ok=True)

@app.route('/get_video', methods=['GET'])
def get_video():
    video_id = request.args.get('video_id')
    if not video_id:
        return "Missing video_id parameter", 400

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        # Define paths for downloaded and processed files
        file_path = os.path.join(ASSETS_FOLDER, f"{video_id}.mp4")
        processed_file = os.path.join(ASSETS_FOLDER, f"{video_id}.webm")

        # Check if processed file already exists
        if os.path.exists(processed_file):
            return send_file(processed_file, as_attachment=True)

        # Download video using pytube
        yt = YouTube(video_url)
        stream = yt.streams.get_highest_resolution()
        stream.download(output_path=ASSETS_FOLDER, filename=f"{video_id}.mp4")

        # Define FFmpeg command to process the video
        ffmpeg_cmd = [
            'ffmpeg', '-i', file_path, '-c:v', 'libvpx', '-b:v', '300k',
            '-cpu-used', '8', '-pix_fmt', 'yuv420p', '-c:a', 'libvorbis', '-b:a', '128k',
            '-r', '30', '-g', '30', processed_file
        ]

        # Run FFmpeg if processed file is not present
        subprocess.run(ffmpeg_cmd, check=True)

        return send_file(processed_file, as_attachment=True)

    except Exception as e:
        return f"Error: {str(e)}", 500

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
        maxResults=40
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
    response = service.playlistItems().list(part="snippet,contentDetails", playlistId=uploads_playlist_id, maxResults=10).execute()
    
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

    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
