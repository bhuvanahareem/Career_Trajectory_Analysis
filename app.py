"""
Main Flask backend application handling API routes for resume processing, 
career analysis, chatbot interactions, and study plan generation.
"""

from flask import Flask, request, jsonify, send_from_directory # Web framework and request handling
from flask_cors import CORS # Cross-origin resource sharing support
import fitz  # PDF parsing (PyMuPDF)
from docx import Document # MS Word document parsing
import os # OS-level directory and environment management
import re # Regular expressions for text cleaning
import json # JSON data serialization and parsing
from werkzeug.utils import secure_filename # Secure file upload handling
from groq import Groq # Interface for Groq AI models
from dotenv import load_dotenv # Environment variable loader

import logging
logging.basicConfig(level=logging.INFO)

load_dotenv()
print(f"DEBUG: Groq Key found: {os.getenv('GROQ_API_KEY')[:5] if os.getenv('GROQ_API_KEY') else 'None'}...")
print(f"DEBUG: YouTube Key found: {os.getenv('YOUTUBE_API_KEY')[:8] if os.getenv('YOUTUBE_API_KEY') else 'NOT SET – will use static fallback'}")

# --- IMPORT YOUR TRAINED AI LOGIC ---
from predictor import analyze_skill_gap, extract_skills_from_text, analyze_confused_paths, CAREER_METADATA, validate_domain_input
from extract_data import extract_chatbot_context
from study_plan import ResourceBroker

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- GROQ CLIENT FOR CHATBOT ---
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# Use metadata from predictor instead of legacy JSON
CAREER_DOMAINS_SUMMARY = ", ".join(CAREER_METADATA.keys())

def clean_text(text):
    """Sanitizes raw text by removing special characters and extra spaces."""
    text = text.replace('|', ' ').replace(':', ' ').replace('/', ' ')
    return re.sub(r'\s+', ' ', text).strip()

# --- ROUTES ---

@app.route('/api/upload', methods=['POST'])
def upload_resume():
    """Handles resume uploads, extracts text/skills, and prepares chatbot context."""
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
        
        # Extract chatbot context from resume using Groq
        chatbot_context = None
        if GROQ_API_KEY:
            chatbot_context = extract_chatbot_context(text, GROQ_API_KEY)
        
        os.remove(path)
        return jsonify({
            'success': True,
            'skills': skills,
            'resumeText': text[:3000],  # First 3000 chars for chatbot context
            'chatbotContext': chatbot_context
        })
    except Exception as e:
        if os.path.exists(path): os.remove(path)
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_career():
    """Performs detailed skill gap analysis between user skills and target domain."""
    data = request.json
    # These are the skills returned by the upload route
    user_skills = data.get('skills', [])
    target_job = data.get('domain', '').strip()

    # --- INPUT VALIDATION GUARDRAIL ---
    # Reject gibberish / unrecognised domains before touching the AI model.
    validation = validate_domain_input(target_job)
    if not validation["valid"]:
        logging.warning(
            f"[VALIDATION REJECTED] Input: '{target_job}' "
            f"| Best similarity: {validation['score']:.4f} "
            f"| Threshold: 0.45"
        )
        return jsonify({
            "error": "domain_not_found",
            "message": (
                f"\u201c{target_job}\u201d is not a recognised career domain. "
                "Please enter a valid tech career path (e.g. \"Data Analyst\", "
                "\"DevOps Engineer\", \"UX Designer\")."
            ),
            "similarity": validation["score"]
        }), 400

    # Pass the canonical matched domain so the model uses the exact key.
    pre_validated_domain = validation["matched_domain"]
    logging.info(
        f"[VALIDATION PASSED] Input: '{target_job}' "
        f"\u2192 Matched: '{pre_validated_domain}' "
        f"| Score: {validation['score']:.4f}"
    )

    # --- USE THE TRAINED AI ENGINE ---
    analysis = analyze_skill_gap(user_skills, target_job, pre_validated_domain)

    return jsonify({
        'score': round(float(analysis['score']), 2),
        'status_text': analysis['status_text'],
        'warning': analysis['warning'],
        'master_msg': analysis['master_msg'],
        'found_skills': analysis['found_skills'],
        'missing_skills': analysis['missing_skills'],
        'roadmap': analysis['roadmap'],
        'missing_by_tier': analysis['missing_by_tier'],
        'all_skills_by_tier': analysis.get('all_skills_by_tier', {}),
        'alt_domain': analysis['alt_domain'],
        'alt_missing_by_tier': analysis.get('alt_missing_by_tier', {}),
        'description': analysis.get('description', '')
    })

@app.route('/api/confused', methods=['POST'])
def career_confused():
    """Suggests potential career paths based on existing skills match (>30%)."""
    data = request.json
    user_skills = data.get('skills', [])
    
    # Analyze all paths > 30% match
    from predictor import analyze_confused_paths
    matches = analyze_confused_paths(user_skills)
    
    return jsonify({
        'success': True,
        'matches': matches
    })

@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    """Manages AI career advisor conversation using Groq and resume context."""
    if not groq_client:
        return jsonify({'error': 'Groq API key not configured. Set GROQ_API_KEY in your .env file.'}), 500
    
    data = request.json
    messages = data.get('messages', [])
    resume_context = data.get('resumeContext', None)
    
    # Build the system instruction
    system_parts = [
        "You are a warm, knowledgeable career advisor specializing in technology careers.",
        "Your tone is encouraging, direct, and practical — like a wise mentor who genuinely cares.",
        "Keep replies concise (3-5 sentences max unless the user asks for detail).",
        "Use bullet points for lists. Never use markdown headers or bold formatting.",
        f"You have deep expertise in these career domains: {CAREER_DOMAINS_SUMMARY}.",
        "When giving advice, reference specific skills, tools, certifications, and realistic timelines.",
        "Always ask a follow-up question to keep the conversation going and understand the user better.",
    ]
    
    if resume_context and resume_context.get('skills'):
        skills_str = ", ".join(resume_context['skills'])
        domain = resume_context.get('domain', 'technology')
        
        chatbot_ctx = resume_context.get('chatbotContext', {})
        ctx_parts = []
        if chatbot_ctx:
            if chatbot_ctx.get('name'):
                ctx_parts.append(f"Name: {chatbot_ctx['name']}")
            if chatbot_ctx.get('current_status'):
                ctx_parts.append(f"Status: {chatbot_ctx['current_status']}")
            if chatbot_ctx.get('years_experience') is not None:
                ctx_parts.append(f"Experience: {chatbot_ctx['years_experience']} years")
            if chatbot_ctx.get('education'):
                ctx_parts.append(f"Education: {', '.join(chatbot_ctx['education'])}")
            if chatbot_ctx.get('career_interests'):
                ctx_parts.append(f"Interests: {', '.join(chatbot_ctx['career_interests'])}")
        
        context_str = ". ".join(ctx_parts) if ctx_parts else ""
        
        system_parts.append(
            f"The user has uploaded a resume. Their extracted skills are: [{skills_str}]. "
            f"Their target career domain is: {domain}. "
            f"{('Additional context from their resume: ' + context_str + '. ') if context_str else ''}"
            "Use this context to personalize your advice. You already know their background — "
            "don't ask them to list their skills again. Instead, dive straight into career guidance."
        )
    else:
        system_parts.append(
            "The user has NOT uploaded a resume yet. Start by understanding their situation. "
            "Ask whether they are a student, working professional, or on a gap year. "
            "Then ask about their interests, experience level, and career goals before giving advice."
        )
    
    system_instruction = "\n".join(system_parts)
    
    # Build contents for Groq
    groq_messages = [{"role": "system", "content": system_instruction}]
    for msg in messages:
        role = 'user' if msg.get('role') == 'user' else 'assistant'
        groq_messages.append({"role": role, "content": msg.get('text', '')})
    
    if len(groq_messages) <= 1:
        return jsonify({'reply': "I'd love to help! Could you tell me a bit more about yourself?"})
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=groq_messages,
            temperature=0.7,
            max_tokens=500,
        )
        reply = response.choices[0].message.content.strip()
        return jsonify({'reply': reply})
    except Exception as e:
        print(f"[CHATBOT ERROR]: {e}")
        error_str = str(e)
        if '429' in error_str:
            return jsonify({'reply': "I'm currently at my response limit. Please wait a moment and try again."}), 200
        return jsonify({'error': f'Chatbot error: {error_str}'}), 500

@app.route('/api/study-plan', methods=['POST'])
def get_study_plan():
    """Generates a structured multi-week learning resource plan for missing skills."""
    data = request.json
    missing_skills = data.get('missing_skills', [])
    found_skills   = data.get('found_skills', [])
    score          = float(data.get('score', 0))
    domain         = data.get('domain', '')
    description    = data.get('description', '')

    if not missing_skills:
        return jsonify({'success': True, 'weeks': [], 'skill_level': 'Beginner', 'message': 'No missing skills – you are ready!'})

    broker = ResourceBroker(youtube_api_key=YOUTUBE_API_KEY)
    weeks  = broker.build_study_plan(missing_skills, score)
    return jsonify({
        'success':     True,
        'weeks':       weeks,
        'skill_level': broker.get_skill_level(score),
        'domain':      domain,
        'description': description,
        'found_skills': found_skills,
        'missing_skills': missing_skills,
        'score':       score,
    })

# --- SERVE FRONTEND ---
@app.route('/')
def index():
    """Serves the main HTML frontend from the root directory."""
    # Serves your index.html directly from the root folder
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Delivers static assets such as CSS, JS, and image files."""
    # Serves your style.css, script.js, and images
    return send_from_directory('.', path)

if __name__ == '__main__':
    # Using threaded=False to prevent the OMP Error on some Windows systems
    app.run(debug=True, port=5000, threaded=False)