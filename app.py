from flask import Flask, request, Response, send_file
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from pytubefix import YouTube
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

// test 

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
    ET.SubElement(root, "generator", {"ver": "1.0", "uri": "http://kamil.cc/"}).text = "Liinback data API"
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
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
