# Career Trajectory Prediction & Analysis System

An AI-driven career path analysis tool that evaluates a user's resume against a target job domain using NLP and machine learning to dynamically calculate skill gaps and provide visual roadmaps.

## Features

- **Resume Analysis**: Upload PDF or DOCX resumes for intelligent parsing
- **Dynamic Domain Matching**: Uses sentence-transformers to understand semantic relationships between skills and job domains
- **Skill Gap Scoring**: Calculates match percentage using cosine similarity
- **Visual Analytics**: Interactive pie charts and career roadmaps
- **Conditional Guidance**: Personalized recommendations based on match score

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Download spaCy language model:
```bash
python -m spacy download en_core_web_sm
```

3. Run the Flask server:
```bash
python app.py
```

4. Open `index.html` in your browser or serve via Flask

## Tech Stack

- **Backend**: Flask, Python
- **AI/ML**: sentence-transformers, spaCy, scikit-learn
- **Frontend**: HTML5, CSS3, JavaScript, Chart.js, Mermaid.js
- **File Processing**: PyMuPDF, python-docx

