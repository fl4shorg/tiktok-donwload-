from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

def extract_video_url(tiktok_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(tiktok_url, headers=headers)
    video_url = re.search(r'"playAddr":"(.*?)"', response.text)
    if video_url:
        return video_url.group(1).replace("\\u002F", "/")
    return None

@app.route('/get_video', methods=['GET'])
def get_video():
    tiktok_url = request.args.get("url")
    if not tiktok_url:
        return jsonify({"error": "URL do TikTok não fornecida"}), 400

    video_url = extract_video_url(tiktok_url)
    if video_url:
        return jsonify({"video_url": video_url})
    return jsonify({"error": "Não foi possível extrair o link"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
