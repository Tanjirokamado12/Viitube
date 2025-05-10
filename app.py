from flask import Flask, request, Response, send_file
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import pytubefix
import subprocess
import os

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
    
# Helper functions
def format_duration(seconds):
    """Convert seconds into YouTube-style duration format."""
    try:
        seconds = int(seconds)
        if seconds < 60:
            return f"0:{seconds:02d}"
        elif seconds < 3600:
            minutes = seconds // 60
            sec = seconds % 60
            return f"{minutes}:{sec:02d}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            sec = seconds % 60
            return f"{hours}:{minutes:02d}:{sec:02d}"
    except (ValueError, TypeError):
        return "Unknown"

def time_since(date_str):
    """Convert date string (YYYY-MM-DD) into a relative time format."""
    try:
        published_date = datetime.strptime(date_str, "%Y-%m-%d")
        now = datetime.now()
        diff = now - published_date
        if diff.days < 1:
            return "Today"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} weeks ago"
        elif diff.days < 365:
            months = diff.days // 30
            return f"{months} months ago"
        else:
            years = diff.days // 365
            return f"{years} years ago"
    except ValueError:
        return "Unknown"

def fetch_video_details(video_id):
    """Fetch detailed video info using YouTubei player API."""
    payload = {"videoId": video_id, "context": {"client": {"clientName": "WEB", "clientVersion": "2.20231221"}}}
    response = requests.post(YOUTUBEI_PLAYER_URL, json=payload, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return None

def convert_to_xml(data):
    """Convert YouTube JSON search response into XML format."""
    feed = ET.Element("feed", {
        "xmlns:openSearch": "http://a9.com/-/spec/opensearch/1.1/",
        "xmlns:media": "http://search.yahoo.com/mrss/",
        "xmlns:yt": "http://www.youtube.com/xml/schemas/2015"
    })

    ET.SubElement(feed, "title", {"type": "text"}).text = "Videos"
    ET.SubElement(feed, "generator", {
        "ver": "1.0",
        "uri": "http://kamil.cc/"
    }).text = "Liinback data API"

    search_results = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])

    for item in search_results:
        for video in item.get("itemSectionRenderer", {}).get("contents", []):
            if "videoRenderer" in video:
                video_data = video["videoRenderer"]
                entry = ET.SubElement(feed, "entry")

                video_id = video_data.get("videoId", "")
                video_title = video_data.get("title", {}).get("runs", [{}])[0].get("text", "")
                uploader_name = video_data.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
                uploader_id = video_data.get("ownerText", {}).get("runs", [{}])[0].get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId", "")
                thumbnail_url = f"http://i.ytimg.com/vi/{video_id}/mqdefault.jpg"

                # Fetch detailed video info
                details = fetch_video_details(video_id)
                if details and "videoDetails" in details:
                    duration_seconds = details["videoDetails"].get("lengthSeconds")
                    formatted_duration = format_duration(int(duration_seconds)) if duration_seconds else "Live"
                    raw_published_time = details.get("microformat", {}).get("playerMicroformatRenderer", {}).get("publishDate", "Unknown")
                    published_time = time_since(raw_published_time)
                    views_count = details.get("videoDetails", {}).get("viewCount", "0")
                else:
                    formatted_duration = "Unknown"
                    published_time = "Unknown"
                    views_count = "0"

                # Entry details
                ET.SubElement(entry, "id").text = f"http://192.168.1.18:443/api/videos/{video_id}"
                ET.SubElement(entry, "published").text = published_time
                ET.SubElement(entry, "title", {"type": "text"}).text = video_title
                ET.SubElement(entry, "link", {"rel": f"http://192.168.1.18:443/api/videos/{video_id}/related"})

                author = ET.SubElement(entry, "author")
                ET.SubElement(author, "name").text = uploader_name
                ET.SubElement(author, "uri").text = f"https://www.youtube.com/channel/{uploader_id}"

                media_group = ET.SubElement(entry, "media:group")
                ET.SubElement(media_group, "media:thumbnail", {
                    "yt:name": "mqdefault",
                    "url": thumbnail_url,
                    "height": "240",
                    "width": "320",
                    "time": formatted_duration
                })
                ET.SubElement(media_group, "yt:duration", {"seconds": str(duration_seconds if duration_seconds else 0)}).text = formatted_duration
                ET.SubElement(media_group, "yt:uploaderId", {"id": uploader_id}).text = uploader_id
                ET.SubElement(media_group, "yt:videoid", {"id": video_id}).text = video_id
                ET.SubElement(media_group, "media:credit", {"role": "uploader", "name": uploader_name}).text = uploader_name

                # Adding statistics
                ET.SubElement(entry, "yt:statistics", {
                    "favoriteCount": "0",
                    "viewCount": f"{views_count}"
                })

    return ET.tostring(feed, encoding="utf-8").decode()


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

@app.route('/feeds/api/videos', methods=['GET'])
def search_videos():
    """Search videos using YouTubei API and return XML response."""
    query = request.args.get('q')
    if not query:
        return Response("<error>Query parameter is required</error>", content_type="application/xml", status=400)

    payload = PAYLOAD_TEMPLATE.copy()
    payload["query"] = query

    response = requests.post(YOUTUBEI_SEARCH_URL, json=payload, headers=HEADERS)
    if response.status_code != 200:
        return Response("<error>Failed to fetch results</error>", content_type="application/xml", status=500)

    xml_response = convert_to_xml(response.json())
    return Response(xml_response, content_type="application/xml")

@app.route("/get_video")
def get_video():
    # Extract video_id from the request
    video_id = request.args.get("video_id")
    if not video_id:
        return "Missing video_id", 400

    # Construct YouTube URL
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # Define the path for assets folder
    assets_dir = os.path.join(os.getcwd(), "assets")

    # Ensure the assets folder exists
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)

    try:
        # Download video using pytubefix
        yt = pytubefix.YouTube(video_url)
        stream = yt.streams.filter(progressive=True, file_extension="mp4").first()
        if not stream:
            return "No suitable stream found", 404
        
        stream_url = stream.url

        # Define output file path
        output_file = os.path.join(assets_dir, f"{video_id}.webm")

        # FFmpeg command to process the video
        ffmpeg_cmd = [
            "ffmpeg", "-i", stream_url,
            "-c:v", "libvpx", "-b:v", "300k", "-cpu-used", "8",
            "-pix_fmt", "yuv420p", "-c:a", "libvorbis", "-b:a", "128k",
            "-r", "30", "-g", "30", output_file
        ]

        # Run FFmpeg command
        subprocess.run(ffmpeg_cmd)

        return f"Video downloaded and processed: {output_file}"

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
