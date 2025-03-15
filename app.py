from flask import Flask, request, jsonify
from TikTokApi import TikTokApi

app = Flask(__name__)

# Rota principal para verificar se a API está funcionando
@app.route('/')
def home():
    return jsonify({"message": "API funcionando corretamente!"})

# Rota para baixar o vídeo do TikTok
@app.route('/baixar_video', methods=['GET'])
def baixar_video():
    tiktok_url = request.args.get('url')  # Obtemos a URL do TikTok
    if not tiktok_url:
        return jsonify({"error": "URL não fornecida"}), 400
    
    api = TikTokApi.get_instance()
    video = api.video(url=tiktok_url)  # Pega o vídeo pelo link
    video_bytes = video.bytes(no_watermark=True)  # Baixa sem marca d'água
    
    # Salva o arquivo temporariamente
    with open('video_sem_marca.mp4', 'wb') as f:
        f.write(video_bytes)
    
    return jsonify({"message": "Vídeo baixado com sucesso!"}), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)