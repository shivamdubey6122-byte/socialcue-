from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from backend.database.mongo import get_all_users, get_logs, get_settings, update_settings
from backend.services.face_recognition import get_video_stream
from backend.services.voice_assistant import assistant
import threading

app = Flask(__name__)
CORS(app)

@app.route('/api/users', methods=['GET'])
def users():
    return jsonify(get_all_users())

@app.route('/api/logs', methods=['GET'])
def logs():
    return jsonify(get_logs())

@app.route('/api/settings', methods=['GET', 'PUT'])
def settings():
    if request.method == 'PUT':
        update_settings(request.json)
        return jsonify({"status": "updated"})
    return jsonify(get_settings())

@app.route('/api/camera-stream')
def camera_stream():
    return Response(get_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/voice/start', methods=['POST'])
def start_voice():
    assistant.start()
    return jsonify({"status": "Voice Assistant Started"})

@app.route('/api/voice/stop', methods=['POST'])
def stop_voice():
    assistant.stop()
    return jsonify({"status": "Voice Assistant Stopped"})

def start_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    start_flask()
