from flask import Flask, render_template_string, request, jsonify, Response, stream_with_context
import base64
from curl_cffi import requests
import json
from pathlib import Path
import time
import os
import sys

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Global config storage
CONFIG_FILE = "grok_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "current": {
            "cookie": "stblid=64c0788f-2da3-41e3-8045-ac4d0d1fa72c; x-anon-token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNWFiNjZiYjMtZTEzYS00NzhhLWI3M2EtM2YyZTE0NGVmYzhjIiwidGVhbV9pZCI6bnVsbCwiZXhwIjoxNzkxODc4NzU3LCJpc19hbm9uX3VzZXIiOnRydWV9.Fo9Nm91QnvVrqaYI6F1DhdJIeCPtNqF8ykIQlYuhNdc; _ga=GA1.1.919478197.1764574701; i18nextLng=tr; cf_clearance=BrgWOxkUrab3o0I.Te8rTN2tMM_jkiC39BM0cH41T4A-1765115933-1.2.1.1-UOWsgxme6l7muV9l_tj6eENv8399NTIr_msCnd4Qj29TxELotMfre50dADPtqtdQEnl4bmVJWhWuDJflrm6aE3_Xo7oogHDfT9.HHvnVeOKjtr2jGAgCLVTRHcT.cSNXIJvqROmRBMAQWj_gavf7n5NEdmI.rZLPSFDg5x983pO6vYs4PZRYS.1LlyRa1gBFo5VLtpap9bVkYv_0DpnfY0j4s0E6PI42CD5F128CpKw; x-anonuserid=740cf253-5f6a-415e-8355-f09107df7e64; x-challenge=SYi%2Byqk7IYl6C8ovCGQ4zJCt2LeAtl%2BzsVWS6wgifh5O5D%2B1XVo1M1tkAS5AFOQYrfZCHMO5DfrvuZmyYD92yvlVqwgJli%2B5im33%2F6S30iLIvgiRukESAlqCd8MT1OkQYkoTQqy4GYMasravHlqKW%2Fs2S%2Fwc2v%2BNrCiPCAy%2BK1yUsXMdP2E%3D; x-signature=YSO%2Fe7Pwvn1II5JmbRTw6ebuzjt7ELouwUMfr4cWWckeTVm8xGF9Z7w9wcYlqYYtQdpZn8OhfYGAp47OaQi20A%3D%3D; sso-rw=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiMzhmMjJlNmMtZmY0ZS00MmMzLTk2ZDctNWMyNDA2YzJhOTVmIn0.GKp70IRVpJT0SmfpgpbGvXYgkyxiQVe-ndrq9Fv_t9I; sso=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiMzhmMjJlNmMtZmY0ZS00MmMzLTk2ZDctNWMyNDA2YzJhOTVmIn0.GKp70IRVpJT0SmfpgpbGvXYgkyxiQVe-ndrq9Fv_t9I; x-userid=9bbc8518-3a45-415f-b1b0-4799381e82de; mp_ea93da913ddb66b6372b89d97b1029ac_mixpanel=%7B%22distinct_id%22%3A%229bbc8518-3a45-415f-b1b0-4799381e82de%22%2C%22%24device_id%22%3A%22221a43d4-d560-4913-9aa6-82bf51db419f%22%2C%22%24search_engine%22%3A%22google%22%2C%22%24initial_referrer%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%2C%22%24initial_referring_domain%22%3A%22www.google.com%22%2C%22__mps%22%3A%7B%7D%2C%22__mpso%22%3A%7B%7D%2C%22__mpus%22%3A%7B%7D%2C%22__mpa%22%3A%7B%7D%2C%22__mpu%22%3A%7B%7D%2C%22__mpr%22%3A%5B%5D%2C%22__mpap%22%3A%5B%5D%2C%22%24user_id%22%3A%229bbc8518-3a45-415f-b1b0-4799381e82de%22%7D; _ga_8FEWB057YH=GS2.1.s1765115895$o18$g1$t1765115964$j56$l0$h0",
            "statsig_id": "5JwsuUREdE0bBLpu7NExChTnaELTb/5pyidhSqsMn5h98q6mQHXJ46XAq82G7k161vPCAuCHlIGq1UJmu5u4IASBqCiY5w"
        },
        "saved": []
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_mime_type(filename):
    ext = Path(filename).suffix.lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp'
    }
    return mime_types.get(ext, 'image/png')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grok Video Generator</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Minecraft', monospace, sans-serif;
            background: #2b2b2b;
            color: #fff;
            height: 100vh;
            overflow: hidden;
        }
        
        .container {
            display: grid;
            grid-template-columns: 350px 1fr 300px;
            height: 100vh;
            gap: 10px;
            padding: 10px;
        }
        
        .panel {
            background: #3c3c3c;
            border: 3px solid #5a5a5a;
            box-shadow: inset 0 0 0 1px #1a1a1a;
            padding: 15px;
            overflow-y: auto;
        }
        
        .panel::-webkit-scrollbar {
            width: 12px;
        }
        
        .panel::-webkit-scrollbar-track {
            background: #2b2b2b;
        }
        
        .panel::-webkit-scrollbar-thumb {
            background: #5a5a5a;
            border: 2px solid #2b2b2b;
        }
        
        h2 {
            color: #55ff55;
            text-shadow: 2px 2px #003300;
            margin-bottom: 15px;
            font-size: 18px;
            border-bottom: 2px solid #5a5a5a;
            padding-bottom: 8px;
        }
        
        .upload-area {
            border: 3px dashed #5a5a5a;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            background: #2b2b2b;
            margin-bottom: 15px;
            position: relative;
        }
        
        .upload-area:hover {
            border-color: #55ff55;
            background: #353535;
        }
        
        #preview {
            max-width: 100%;
            max-height: 200px;
            margin-top: 10px;
            border: 2px solid #5a5a5a;
        }
        
        input[type="text"], textarea {
            width: 100%;
            padding: 10px;
            background: #2b2b2b;
            border: 2px solid #5a5a5a;
            color: #fff;
            font-family: inherit;
            margin-bottom: 10px;
        }
        
        input[type="text"]:focus, textarea:focus {
            outline: none;
            border-color: #55ff55;
        }
        
        .checkbox-group {
            margin: 15px 0;
            padding: 10px;
            background: #2b2b2b;
            border: 2px solid #5a5a5a;
        }
        
        input[type="checkbox"] {
            margin-right: 8px;
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        
        label {
            cursor: pointer;
            display: flex;
            align-items: center;
            color: #aaa;
        }
        
        button {
            width: 100%;
            padding: 12px;
            background: #5a5a5a;
            border: 3px solid #3c3c3c;
            color: #fff;
            font-family: inherit;
            font-weight: bold;
            cursor: pointer;
            text-shadow: 2px 2px #1a1a1a;
            margin-bottom: 10px;
            font-size: 14px;
        }
        
        button:hover {
            background: #6a6a6a;
            border-color: #55ff55;
        }
        
        button:active {
            background: #4a4a4a;
        }
        
        button.primary {
            background: #55aa55;
            border-color: #3a7a3a;
        }
        
        button.primary:hover {
            background: #65ba65;
        }
        
        button.settings {
            background: #5555aa;
            border-color: #3a3a7a;
        }
        
        button.settings:hover {
            background: #6565ba;
        }
        
        .video-player {
            background: #1a1a1a;
            border: 3px solid #5a5a5a;
            padding: 15px;
            margin-bottom: 15px;
            min-height: 400px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        video {
            max-width: 100%;
            max-height: 350px;
            border: 2px solid #5a5a5a;
        }
        
        .video-placeholder {
            color: #5a5a5a;
            font-size: 14px;
            text-align: center;
        }
        
        .log-container {
            background: #1a1a1a;
            border: 2px solid #5a5a5a;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.6;
            max-height: calc(100vh - 40px);
            overflow-y: auto;
        }
        
        .log-entry {
            margin-bottom: 5px;
            padding: 5px;
            border-left: 3px solid #5a5a5a;
            padding-left: 8px;
        }
        
        .log-entry.success {
            color: #55ff55;
            border-color: #55ff55;
        }
        
        .log-entry.error {
            color: #ff5555;
            border-color: #ff5555;
        }
        
        .log-entry.info {
            color: #5555ff;
            border-color: #5555ff;
        }
        
        .log-entry.progress {
            color: #ffff55;
            border-color: #ffff55;
        }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #2b2b2b;
            border: 2px solid #5a5a5a;
            margin: 10px 0;
            position: relative;
        }
        
        .progress-fill {
            height: 100%;
            background: #55ff55;
            transition: width 0.3s;
            position: relative;
        }
        
        .progress-text {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            text-align: center;
            line-height: 20px;
            color: #fff;
            text-shadow: 1px 1px #000;
            font-size: 12px;
            font-weight: bold;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .modal.active {
            display: flex;
        }
        
        .modal-content {
            background: #3c3c3c;
            border: 3px solid #5a5a5a;
            padding: 20px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border-bottom: 2px solid #5a5a5a;
            padding-bottom: 10px;
        }
        
        .close-btn {
            background: #ff5555;
            border: 2px solid #aa3a3a;
            width: auto;
            padding: 5px 15px;
        }
        
        .saved-config {
            background: #2b2b2b;
            border: 2px solid #5a5a5a;
            padding: 10px;
            margin-bottom: 10px;
            cursor: pointer;
        }
        
        .saved-config:hover {
            border-color: #55ff55;
        }
        
        .saved-config.active {
            border-color: #55ff55;
            background: #353535;
        }

        .delete-btn {
            background: #ff5555;
            border: 2px solid #aa3a3a;
            padding: 5px 10px;
            margin-left: 10px;
            font-size: 12px;
            display: inline-block;
            width: auto;
        }

        .delete-btn:hover {
            background: #ff6666;
        }

        .saved-config-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .video-actions {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        
        .video-actions button {
            flex: 1;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Left Panel - Controls -->
        <div class="panel">
            <h2>⚙ Controls</h2>
            
            <button class="settings" onclick="openSettings()">⚙ Settings</button>
            
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <div>📁 Click to Upload Image</div>
                <input type="file" id="fileInput" accept="image/*" style="display:none;" onchange="previewImage(this)">
                <img id="preview" style="display:none;">
            </div>
            
            <input type="text" id="promptInput" placeholder="Enter prompt (e.g., dancing)">
            
            <div class="checkbox-group">
                <label>
                    <input type="checkbox" id="enhanceCheck" checked>
                    <span>🎨 Auto Enhance (Upscale)</span>
                </label>
            </div>
            
            <button class="primary" onclick="generateVideo()">🎬 Generate Video</button>
            
            <div class="progress-bar" style="display:none;" id="progressBar">
                <div class="progress-fill" id="progressFill" style="width:0%"></div>
                <div class="progress-text" id="progressText">0%</div>
            </div>
        </div>
        
        <!-- Center Panel - Video Player -->
        <div class="panel">
            <h2>🎬 Video Player</h2>
            
            <div class="video-player" id="videoPlayer">
                <div class="video-placeholder">
                    No video generated yet<br>
                    Upload an image and generate a video
                </div>
            </div>
            
            <div class="video-actions" id="videoActions" style="display:none;">
                <button onclick="enhanceVideo()">✨ Enhance Video</button>
                <button onclick="downloadVideo()">💾 Download Video</button>
            </div>
        </div>
        
        <!-- Right Panel - Logs -->
        <div class="panel">
            <h2>📋 Logs</h2>
            <div class="log-container" id="logContainer">
                <div class="log-entry info">System ready...</div>
            </div>
        </div>
    </div>
    
    <!-- Settings Modal -->
    <div class="modal" id="settingsModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 style="margin:0;">⚙ Settings</h2>
                <button class="close-btn" onclick="closeSettings()">✕</button>
            </div>
            
            <h3 style="color:#5555ff; margin-bottom:10px;">Current Configuration</h3>
            <textarea id="cookieInput" placeholder="Cookie String" style="height:100px;"></textarea>
            <input type="text" id="statsigInput" placeholder="Statsig ID">
            <button onclick="saveCurrentConfig()">💾 Save Current</button>
            
            <h3 style="color:#5555ff; margin:20px 0 10px;">Saved Configurations</h3>
            <div id="savedConfigs"></div>
            
            <button onclick="addNewConfig()">➕ Add New Configuration</button>
        </div>
    </div>
    
    <script>
        let currentVideoUrl = null;
        let currentVideoId = null;
        let currentAssetId = null;
        
        function addLog(message, type = 'info') {
            const log = document.getElementById('logContainer');
            const entry = document.createElement('div');
            entry.className = 'log-entry ' + type;
            entry.textContent = '[' + new Date().toLocaleTimeString() + '] ' + message;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight;
        }
        
        function updateProgress(percent, text) {
            const bar = document.getElementById('progressBar');
            const fill = document.getElementById('progressFill');
            const textEl = document.getElementById('progressText');
            
            bar.style.display = 'block';
            fill.style.width = percent + '%';
            textEl.textContent = text || (percent + '%');
        }
        
        function hideProgress() {
            document.getElementById('progressBar').style.display = 'none';
        }
        
        function previewImage(input) {
            const preview = document.getElementById('preview');
            if (input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                    addLog('Image loaded: ' + input.files[0].name, 'success');
                }
                reader.readAsDataURL(input.files[0]);
            }
        }
        
        async function generateVideo() {
            const fileInput = document.getElementById('fileInput');
            const prompt = document.getElementById('promptInput').value;
            const enhance = document.getElementById('enhanceCheck').checked;
            
            if (!fileInput.files[0]) {
                addLog('Please select an image!', 'error');
                return;
            }
            
            if (!prompt) {
                addLog('Please enter a prompt!', 'error');
                return;
            }
            
            addLog('Starting video generation...', 'info');
            updateProgress(0, 'Starting...');
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('prompt', prompt);
            formData.append('enhance', enhance);
            
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    body: formData
                });
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    const {value, done} = await reader.read();
                    if (done) break;
                    
                    const text = decoder.decode(value);
                    const lines = text.split('\\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.type === 'log') {
                                addLog(data.message, data.level);
                            } else if (data.type === 'progress') {
                                updateProgress(data.percent, data.message);
                            } else if (data.type === 'video') {
                                currentVideoUrl = data.url;
                                currentVideoId = data.video_id;
                                currentAssetId = data.asset_id;
                                displayVideo(data.url);
                                addLog('Video generated successfully!', 'success');
                            } else if (data.type === 'enhanced') {
                                currentVideoUrl = data.url;
                                displayVideo(data.url);
                                addLog('Video enhanced successfully!', 'success');
                            } else if (data.type === 'complete') {
                                hideProgress();
                                addLog('All operations completed!', 'success');
                            } else if (data.type === 'error') {
                                addLog('Error: ' + data.message, 'error');
                                hideProgress();
                            }
                        }
                    }
                }
            } catch (error) {
                addLog('Error: ' + error.message, 'error');
                hideProgress();
            }
        }
        
        function displayVideo(url) {
            const player = document.getElementById('videoPlayer');
            // Use proxy endpoint to bypass CORS
            const proxyUrl = '/proxy-video?url=' + encodeURIComponent(url);
            player.innerHTML = '<video controls loop><source src="' + proxyUrl + '" type="video/mp4"></video>';
            document.getElementById('videoActions').style.display = 'flex';
        }
        
        async function enhanceVideo() {
            if (!currentVideoId) {
                addLog('No video ID available for enhancement', 'error');
                return;
            }
            
            addLog('Enhancing video...', 'info');
            updateProgress(0, 'Enhancing...');
            
            try {
                const response = await fetch('/enhance', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({video_id: currentVideoId})
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    currentVideoUrl = data.url;
                    displayVideo(data.url);
                    addLog('Video enhanced successfully!', 'success');
                    updateProgress(100, 'Complete');
                    setTimeout(hideProgress, 2000);
                } else {
                    addLog('Enhancement failed: ' + data.message, 'error');
                    hideProgress();
                }
            } catch (error) {
                addLog('Error: ' + error.message, 'error');
                hideProgress();
            }
        }
        
        function downloadVideo() {
            if (currentVideoUrl) {
                window.open(currentVideoUrl, '_blank');
                addLog('Opening video in new tab...', 'info');
            }
        }
        
        function openSettings() {
            fetch('/get-config')
                .then(r => r.json())
                .then(config => {
                    document.getElementById('cookieInput').value = config.current.cookie;
                    document.getElementById('statsigInput').value = config.current.statsig_id;
                    loadSavedConfigs(config.saved, config.current);
                    document.getElementById('settingsModal').classList.add('active');
                });
        }
        
        function closeSettings() {
            document.getElementById('settingsModal').classList.remove('active');
        }
        
        function loadSavedConfigs(saved, current) {
            const container = document.getElementById('savedConfigs');
            container.innerHTML = '';
            
            saved.forEach((cfg, idx) => {
                const div = document.createElement('div');
                div.className = 'saved-config';
                if (cfg.cookie === current.cookie && cfg.statsig_id === current.statsig_id) {
                    div.classList.add('active');
                }
                
                div.innerHTML = 
                    '<div class="saved-config-header">' +
                        '<div onclick="selectConfig(' + idx + ')" style="flex:1; cursor:pointer;">' +
                            '<strong>Config ' + (idx + 1) + '</strong><br>' +
                            '<small>' + cfg.cookie.substring(0, 50) + '...</small>' +
                        '</div>' +
                        '<button class="delete-btn" onclick="deleteConfig(' + idx + '); event.stopPropagation();">✕</button>' +
                    '</div>';
                
                container.appendChild(div);
            });
        }
        
        function selectConfig(idx) {
            fetch('/get-config')
                .then(r => r.json())
                .then(config => {
                    const cfg = config.saved[idx];
                    document.getElementById('cookieInput').value = cfg.cookie;
                    document.getElementById('statsigInput').value = cfg.statsig_id;
                    addLog('Configuration loaded', 'info');
                });
        }
        
        function saveCurrentConfig() {
            const cookie = document.getElementById('cookieInput').value;
            const statsig = document.getElementById('statsigInput').value;
            
            fetch('/save-config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({cookie, statsig_id: statsig})
            })
            .then(r => r.json())
            .then(data => {
                addLog('Configuration saved!', 'success');
                openSettings();
            });
        }

        function deleteConfig(idx) {
            if (!confirm('Bu konfigürasyonu silmek istediğinize emin misiniz?')) {
                return;
            }
            
            fetch('/delete-config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({index: idx})
            })
            .then(r => r.json())
            .then(data => {
                addLog('Configuration deleted!', 'success');
                openSettings();
            });
        }
        
        function addNewConfig() {
            document.getElementById('cookieInput').value = '';
            document.getElementById('statsigInput').value = '';
            addLog('Enter new configuration', 'info');
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get-config')
def get_config():
    return jsonify(load_config())

@app.route('/save-config', methods=['POST'])
def save_config_route():
    data = request.json
    config = load_config()
    
    config['current'] = {
        'cookie': data['cookie'],
        'statsig_id': data['statsig_id']
    }
    
    # Add to saved if not exists
    exists = False
    for saved in config['saved']:
        if saved['cookie'] == data['cookie'] and saved['statsig_id'] == data['statsig_id']:
            exists = True
            break
    
    if not exists:
        config['saved'].append({
            'cookie': data['cookie'],
            'statsig_id': data['statsig_id']
        })
    
    save_config(config)
    return jsonify({'status': 'success'})

@app.route('/delete-config', methods=['POST'])
def delete_config_route():
    data = request.json
    config = load_config()
    
    idx = data.get('index')
    if idx is not None and 0 <= idx < len(config['saved']):
        deleted = config['saved'].pop(idx)
        save_config(config)
        return jsonify({'status': 'success', 'message': 'Config deleted'})
    
    return jsonify({'status': 'error', 'message': 'Invalid index'})

@app.route('/generate', methods=['POST'])
def generate():
    @stream_with_context
    def generate_stream():
        try:
            config = load_config()
            cookie = config['current']['cookie']
            statsig_id = config['current']['statsig_id']
            
            if not cookie:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Cookie not configured'})}\n\n"
                sys.stdout.flush()
                return
            
            file = request.files['file']
            prompt = request.form['prompt']
            enhance = request.form['enhance'] == 'true'
            
            # Save temp file
            temp_path = 'temp_upload.png'
            file.save(temp_path)
            
            BASE_HEADERS = {
                'accept': '*/*',
                'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                'content-type': 'application/json',
                'origin': 'https://grok.com',
                'referer': 'https://grok.com/imagine/favorites',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'x-statsig-id': statsig_id,
                'cookie': cookie
            }
            
            # Step 1: Upload
            yield f"data: {json.dumps({'type': 'log', 'message': 'Step 1/6: Uploading file...', 'level': 'info'})}\n\n"
            sys.stdout.flush()
            yield f"data: {json.dumps({'type': 'progress', 'percent': 10, 'message': 'Uploading...'})}\n\n"
            sys.stdout.flush()
            
            with open(temp_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            
            mime_type = get_mime_type(temp_path)
            
            upload_data = {
                "fileName": Path(temp_path).name,
                "fileMimeType": mime_type,
                "content": content,
                "fileSource": "IMAGINE_SELF_UPLOAD_FILE_SOURCE"
            }
            
            response = requests.post(
                'https://grok.com/rest/app-chat/upload-file',
                headers=BASE_HEADERS,
                json=upload_data,
                impersonate="chrome131"
            )
            
            time.sleep(0.5)
            
            if response.status_code != 200:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Upload failed: {response.status_code}'})}\n\n"
                sys.stdout.flush()
                return
            
            result = response.json()
            asset_id = result.get('fileMetadataId')
            
            if not asset_id:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Asset ID not found'})}\n\n"
                sys.stdout.flush()
                return
            
            yield f"data: {json.dumps({'type': 'log', 'message': f'✓ Asset ID: {asset_id}', 'level': 'success'})}\n\n"
            sys.stdout.flush()
            
            # Step 2: Get asset
            yield f"data: {json.dumps({'type': 'log', 'message': 'Step 2/6: Getting asset info...', 'level': 'info'})}\n\n"
            sys.stdout.flush()
            yield f"data: {json.dumps({'type': 'progress', 'percent': 25, 'message': 'Processing...'})}\n\n"
            sys.stdout.flush()
            
            headers2 = BASE_HEADERS.copy()
            del headers2['content-type']
            
            response = requests.get(
                f'https://grok.com/rest/assets/{asset_id}',
                headers=headers2,
                impersonate="chrome131"
            )
            
            time.sleep(0.5)
            
            if response.status_code != 200:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Get asset failed: {response.status_code}'})}\n\n"
                sys.stdout.flush()
                return
            
            asset_data = response.json()
            file_uri = asset_data.get('key') or result.get('fileUri')
            
            if file_uri:
                media_url = f"https://assets.grok.com/{file_uri}"
            else:
                media_url = asset_data.get('url')
            
            yield f"data: {json.dumps({'type': 'log', 'message': '✓ Media URL obtained', 'level': 'success'})}\n\n"
            sys.stdout.flush()
            
            # Step 3: Create media post
            yield f"data: {json.dumps({'type': 'log', 'message': 'Step 3/6: Creating media post...', 'level': 'info'})}\n\n"
            sys.stdout.flush()
            yield f"data: {json.dumps({'type': 'progress', 'percent': 40, 'message': 'Creating post...'})}\n\n"
            sys.stdout.flush()
            
            media_data = {
                "mediaType": "MEDIA_POST_TYPE_IMAGE",
                "mediaUrl": media_url
            }
            
            response = requests.post(
                'https://grok.com/rest/media/post/create',
                headers=BASE_HEADERS,
                json=media_data,
                impersonate="chrome131"
            )
            
            time.sleep(0.5)
            yield f"data: {json.dumps({'type': 'log', 'message': '✓ Media post created', 'level': 'success'})}\n\n"
            sys.stdout.flush()
            
            # Step 4: Create conversation
            yield f"data: {json.dumps({'type': 'log', 'message': 'Step 4/6: Generating video...', 'level': 'info'})}\n\n"
            sys.stdout.flush()
            yield f"data: {json.dumps({'type': 'progress', 'percent': 50, 'message': 'Generating video...'})}\n\n"
            sys.stdout.flush()
            
            conversation_data = {
                "temporary": True,
                "modelName": "grok-3",
                "message": f"{media_url} {prompt} --mode=custom",
                "fileAttachments": [asset_id],
                "toolOverrides": {"videoGen": True},
                "responseMetadata": {
                    "modelConfigOverride": {
                        "modelMap": {
                            "videoGenModelConfig": {
                                "parentPostId": asset_id,
                                "aspectRatio": "2:3",
                                "videoLength": 6
                            }
                        }
                    }
                }
            }
            
            headers5 = BASE_HEADERS.copy()
            headers5['referer'] = f'https://grok.com/imagine/post/{asset_id}'
            
            response = requests.post(
                'https://grok.com/rest/app-chat/conversations/new',
                headers=headers5,
                json=conversation_data,
                impersonate="chrome131",
                stream=True
            )
            
            video_url = None
            video_id = None
            last_progress = 50
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if 'result' in data and 'response' in data['result']:
                                streaming_response = data['result']['response'].get('streamingVideoGenerationResponse', {})
                                progress = streaming_response.get('progress', 0)
                                
                                if progress > last_progress:
                                    last_progress = progress
                                    display_progress = 50 + int(progress * 0.4)
                                    yield f"data: {json.dumps({'type': 'progress', 'percent': display_progress, 'message': f'Video: {progress}%'})}\n\n"
                                    sys.stdout.flush()
                                
                                if progress == 100:
                                    video_url = streaming_response.get('videoUrl')
                                    video_id = streaming_response.get('videoId')
                                    if video_url:
                                        full_video_url = f"https://assets.grok.com/{video_url}"
                                        yield f"data: {json.dumps({'type': 'log', 'message': f'✓ Video generated!', 'level': 'success'})}\n\n"
                                        sys.stdout.flush()
                                        yield f"data: {json.dumps({'type': 'video', 'url': full_video_url, 'video_id': video_id, 'asset_id': asset_id})}\n\n"
                                        sys.stdout.flush()
                                        break
                        except:
                            pass
                
                if not video_url:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Video URL not found'})}\n\n"
                    sys.stdout.flush()
                    return
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Conversation failed: {response.status_code}'})}\n\n"
                sys.stdout.flush()
                return
            
            time.sleep(1)
            
            # Step 5: Like post
            yield f"data: {json.dumps({'type': 'log', 'message': 'Step 5/6: Liking post...', 'level': 'info'})}\n\n"
            sys.stdout.flush()
            yield f"data: {json.dumps({'type': 'progress', 'percent': 92, 'message': 'Finalizing...'})}\n\n"
            sys.stdout.flush()
            
            like_data = {"id": asset_id}
            headers6 = BASE_HEADERS.copy()
            headers6['referer'] = f'https://grok.com/imagine/post/{asset_id}'
            
            response = requests.post(
                'https://grok.com/rest/media/post/like',
                headers=headers6,
                json=like_data,
                impersonate="chrome131"
            )
            
            yield f"data: {json.dumps({'type': 'log', 'message': '✓ Post liked', 'level': 'success'})}\n\n"
            sys.stdout.flush()
            
            # Step 6: Upscale if requested
            if enhance and video_id:
                yield f"data: {json.dumps({'type': 'log', 'message': 'Step 6/6: Enhancing video...', 'level': 'info'})}\n\n"
                sys.stdout.flush()
                yield f"data: {json.dumps({'type': 'progress', 'percent': 95, 'message': 'Enhancing...'})}\n\n"
                sys.stdout.flush()
                
                upscale_data = {"videoId": video_id}
                
                response = requests.post(
                    'https://grok.com/rest/media/video/upscale',
                    headers=BASE_HEADERS,
                    json=upscale_data,
                    impersonate="chrome131"
                )
                
                if response.status_code == 200:
                    upscale_result = response.json()
                    hd_url = upscale_result.get('hdMediaUrl')
                    if hd_url:
                        yield f"data: {json.dumps({'type': 'log', 'message': '✓ Video enhanced!', 'level': 'success'})}\n\n"
                        sys.stdout.flush()
                        yield f"data: {json.dumps({'type': 'enhanced', 'url': hd_url})}\n\n"
                        sys.stdout.flush()
                    else:
                        yield f"data: {json.dumps({'type': 'log', 'message': '⚠ HD URL not found', 'level': 'error'})}\n\n"
                        sys.stdout.flush()
                else:
                    yield f"data: {json.dumps({'type': 'log', 'message': f'⚠ Enhance failed: {response.status_code}', 'level': 'error'})}\n\n"
                    sys.stdout.flush()
            else:
                yield f"data: {json.dumps({'type': 'log', 'message': 'Step 6/6: Skipped (enhance disabled)', 'level': 'info'})}\n\n"
                sys.stdout.flush()
            
            yield f"data: {json.dumps({'type': 'progress', 'percent': 100, 'message': 'Complete!'})}\n\n"
            sys.stdout.flush()
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            sys.stdout.flush()
            
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            sys.stdout.flush()
    
    return Response(generate_stream(), 
                   mimetype='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'X-Accel-Buffering': 'no',
                       'Connection': 'keep-alive'
                   })

@app.route('/enhance', methods=['POST'])
def enhance():
    try:
        config = load_config()
        cookie = config['current']['cookie']
        statsig_id = config['current']['statsig_id']
        
        if not cookie:
            return jsonify({'status': 'error', 'message': 'Cookie not configured'})
        
        data = request.json
        video_id = data.get('video_id')
        
        if not video_id:
            return jsonify({'status': 'error', 'message': 'Video ID required'})
        
        BASE_HEADERS = {
            'accept': '*/*',
            'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'origin': 'https://grok.com',
            'referer': 'https://grok.com/imagine/favorites',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-statsig-id': statsig_id,
            'cookie': cookie
        }
        
        upscale_data = {"videoId": video_id}
        
        response = requests.post(
            'https://grok.com/rest/media/video/upscale',
            headers=BASE_HEADERS,
            json=upscale_data,
            impersonate="chrome131"
        )
        
        if response.status_code == 200:
            upscale_result = response.json()
            hd_url = upscale_result.get('hdMediaUrl')
            if hd_url:
                return jsonify({'status': 'success', 'url': hd_url})
            else:
                return jsonify({'status': 'error', 'message': 'HD URL not found'})
        else:
            return jsonify({'status': 'error', 'message': f'Request failed: {response.status_code}'})
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    
@app.route('/proxy-video')
def proxy_video():
    """Proxy endpoint to serve videos through Flask (bypasses CORS)"""
    try:
        video_url = request.args.get('url')
        if not video_url:
            return "No URL provided", 400
        
        config = load_config()
        cookie = config['current']['cookie']
        
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'referer': 'https://grok.com/',
            'cookie': cookie
        }
        
        response = requests.get(video_url, headers=headers, impersonate="chrome131", stream=True)
        
        if response.status_code == 200:
            return Response(
                response.iter_content(chunk_size=8192),
                content_type='video/mp4',
                headers={
                    'Accept-Ranges': 'bytes',
                    'Cache-Control': 'public, max-age=3600'
                }
            )
        else:
            return f"Failed to fetch video: {response.status_code}", response.status_code
            
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    print("Starting Grok Video Generator...")
    print("Open: http://127.0.0.1:5000")
    app.run(debug=False, port=5000, threaded=True, use_reloader=False)
