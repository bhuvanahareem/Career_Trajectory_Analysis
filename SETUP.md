# Setup Guide

## Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

## Installation Steps

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Download spaCy language model:**
   ```bash
   python -m spacy download en_core_web_sm
   ```
   
   Note: The first time you run the app, sentence-transformers will automatically download the `all-MiniLM-L6-v2` model (~90MB). This may take a few minutes.

3. **Start the Flask server:**
   ```bash
   python app.py
   ```
   
   The server will start on `http://localhost:5000`

4. **Open the frontend:**
   - Option 1: Open `index.html` directly in your browser (may have CORS issues)
   - Option 2: Serve via Flask by adding a route to serve `index.html` (recommended for production)

## Testing

1. Upload a resume (PDF or DOCX format)
2. Enter a target career domain (e.g., "Data Scientist", "Web Developer")
3. Click "Analyze" to see your skill gap score and personalized roadmap

## Troubleshooting

- **Model download issues**: Ensure you have a stable internet connection for the first run
- **CORS errors**: Make sure Flask-CORS is installed and the server is running
- **File upload errors**: Check file size (max 10MB) and format (PDF/DOCX only)
- **spaCy errors**: Verify `en_core_web_sm` is installed: `python -m spacy validate`

