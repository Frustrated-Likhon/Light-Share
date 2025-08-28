from flask import Flask, request, render_template, send_file, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'local-file-sharing-secret-key-2024'
app.config['UPLOAD_FOLDER'] = 'shared_files'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
METADATA_FILE = 'file_metadata.json'

def load_metadata():
    try:
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        return []
    except:
        return []

def save_metadata(metadata):
    try:
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
        return True
    except:
        return False

def add_file_metadata(original_filename, saved_filename, file_size, uploader_ip):
    metadata = load_metadata()
    new_file = {
        'id': len(metadata) + 1,
        'original_filename': original_filename,
        'filename': saved_filename,
        'file_size': file_size,
        'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'uploader_ip': uploader_ip,
        'download_count': 0
    }
    metadata.append(new_file)
    if save_metadata(metadata):
        return new_file
    return None

def update_download_count(filename):
    metadata = load_metadata()
    for file in metadata:
        if file['filename'] == filename:
            file['download_count'] += 1
            file['last_download'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            break
    save_metadata(metadata)

def delete_file_metadata(filename):
    metadata = load_metadata()
    metadata = [file for file in metadata if file['filename'] != filename]
    save_metadata(metadata)

def format_file_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

def get_relative_time(timestamp):
    try:
        now = datetime.now()
        upload_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        diff = now - upload_time
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    except:
        return timestamp

@app.route('/')
def index():
    files = load_metadata()
    files.sort(key=lambda x: x.get('upload_time', ''), reverse=True)
    
    for file in files:
        file['formatted_size'] = format_file_size(file.get('file_size', 0))
        file['relative_time'] = get_relative_time(file.get('upload_time', ''))
    
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if file:
        original_filename = file.filename
        filename = secure_filename(original_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        saved_filename = f"{name}_{timestamp}{ext}"
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
        file.save(file_path)
        
        file_size = os.path.getsize(file_path)
        uploader_ip = request.remote_addr
        
        if add_file_metadata(original_filename, saved_filename, file_size, uploader_ip):
            flash(f'File "{original_filename}" uploaded successfully!', 'success')
        else:
            flash('Failed to save file metadata', 'error')
        
        return redirect(url_for('index'))
    
    flash('Upload failed', 'error')
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    file_metadata = get_file_metadata(filename)
    if not file_metadata:
        flash('File not found', 'error')
        return redirect(url_for('index'))
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        flash('File not found on server', 'error')
        return redirect(url_for('index'))
    
    update_download_count(filename)
    
    return send_file(file_path, as_attachment=True, download_name=file_metadata['original_filename'])

@app.route('/delete/<filename>')
def delete_file(filename):
    file_metadata = get_file_metadata(filename)
    if not file_metadata:
        flash('File not found', 'error')
        return redirect(url_for('index'))
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    delete_file_metadata(filename)
    flash(f'File "{file_metadata["original_filename"]}" deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/clear-all')
def clear_all_files():
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    save_metadata([])
    flash('All files cleared successfully!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)