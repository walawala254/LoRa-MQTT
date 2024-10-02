from flask import Flask, jsonify, send_from_directory
import socket
import os
from flask_cors import CORS

app = Flask(__name__, static_folder='lora-vue-frontend/dist')  # Correct static folder path
CORS(app)  # Enable CORS for API requests

def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return None

@app.route('/get-ip', methods=['GET'])
def get_ip():
    ip = get_ip_address()
    return jsonify({"ip": ip})

# Serve Vue static files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
