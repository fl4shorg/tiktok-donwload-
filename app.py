from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)

def baixar_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'video_tiktok.mp4',
        'noplaylist': True,
        'quiet': False,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'writethumbnail': True,
        'writeinfojson': True,
        'merge_output_format': 'mp4',
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

@app.route('/baixar_video', methods=['GET'])
def baixar_video_route():
    url_video = request.args.get('url')
    if not url_video:
        return jsonify({'erro': 'URL do vídeo não fornecida'}), 400

    try:
        baixar_video(url_video)
        return jsonify({'mensagem': 'Download iniciado com sucesso'}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
