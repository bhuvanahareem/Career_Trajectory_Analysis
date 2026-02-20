from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import fitz  # PyMuPDF
from docx import Document
import os
import re
from werkzeug.utils import secure_filename

# --- IMPORT YOUR TRAINED AI LOGIC ---
from predictor import analyze_skill_gap, extract_skills_from_text

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def clean_text(text):
    text = text.replace('|', ' ').replace(':', ' ').replace('/', ' ')
    return re.sub(r'\s+', ' ', text).strip()

# --- ROUTES ---

@app.route('/api/upload', methods=['POST'])
def upload_resume():
    file = request.files.get('file')
    if not file: return jsonify({'error': 'No file'}), 400
    
    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    
    file_ext = filename.rsplit('.', 1)[1].lower()
    try:
        if file_ext == 'pdf':
            with fitz.open(path) as d:
                text = "".join([page.get_text() for page in d])
        else:
            text = "\n".join([p.text for p in Document(path).paragraphs])
        
        # Use the logic from predictor.py to intelligently find skills in the text
        clean_resume_text = clean_text(text)
        skills = extract_skills_from_text(clean_resume_text)
        
        os.remove(path)
        return jsonify({'success': True, 'skills': skills})
    except Exception as e:
        if os.path.exists(path): os.remove(path)
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_career():
    data = request.json
    # These are the skills returned by the upload route
    user_skills = data.get('skills', [])
    target_job = data.get('domain', '').strip()
    
    # --- USE THE TRAINED AI ENGINE ---
    analysis = analyze_skill_gap(user_skills, target_job)
    
    # Matching the exact keys your UI expects to see
    return jsonify({
        'score': round(float(analysis['score']), 2),
        'status_text': analysis['status_text'],
        'found_skills': analysis['found_skills'],
        'missing_skills': analysis['missing_skills'],
        'roadmap': analysis['roadmap'],
        'alt_domain': analysis['alt_domain']
    })

# --- SERVE FRONTEND (STRICTLY NO JINJA) ---
@app.route('/')
def index():
    # Serves your index.html directly from the root folder
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    # Serves your style.css, script.js, and images
    return send_from_directory('.', path)

if __name__ == '__main__':
    # Using threaded=False to prevent the OMP Error on some Windows systems
    app.run(debug=True, port=5000, threaded=False)