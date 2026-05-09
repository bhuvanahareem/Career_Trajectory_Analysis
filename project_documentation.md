# Career Trajectory Prediction: Project Documentation

## 1. Overview
The **Career Trajectory Prediction** project is an AI-powered web application designed to help users identify their current professional standing, analyze skill gaps for their desired roles, and generate actionable, tailored study plans. It combines deep learning, natural language processing (NLP), and third-party APIs to act as a personalized career advisor.

---

## 2. User Workflow & User Experience (UX)

### User Workflow
1. **Input Phase**: The user uploads their resume (PDF or DOCX format) and inputs a target career domain (e.g., "Data Scientist"). Alternatively, if they are unsure, they can use the **"Confused?"** feature based strictly on their resume.
2. **Analysis Phase**: The application extracts text, matches skills using a custom trained AI model, and calculates a match percentage against industry standards for the selected domain.
3. **Exploration Phase**: The user is presented with a breakdown of their skills (Found vs. Missing) and a structured **"Strategic Roadmap"** to reach their goal.
4. **Actionable Remediation**: For missing skills, the user can click to generate a **Study Plan**, which provides a curated weekly curriculum of tutorial videos (powered by YouTube API).
5. **Interactive Guidance**: At any point, the user can converse with an **AI Career Advisor Chatbot** that retains context about their uploaded resume and domain to answer specific career questions.

### User Experience (UX)
* **Single Page Application (SPA)**: Smooth transitions between upload, analysis, and detailed views without page reloads.
* **Dynamic Visualizations**: Uses a wavy SVG-based interactive roadmap to visualize tiered career progressions and Chart.js for skill breakdown pie charts.
* **Loading States & Animations**: Fluid animations, including a dynamic score counter and non-blocking loading overlays, ensuring the user feels the system's responsiveness.
* **Context-Aware Assistance**: The chatbot greets the user differently depending on whether they have uploaded a resume, and it skips redundant questions if it already knows their profile.

---

## 3. User Interface (UI) Components
* **Frontend Stack**: Built with Vanilla HTML5, CSS3, and JavaScript. 
* **Custom Assets**: Uses custom Javascript to dynamically render SVG wavy roadmap nodes based on progression tiers, Chart.js for data visualization, and Mermaid.js for backup structural charting.
* **Responsive Modals**: Integrates floating panels for the Chatbot and overlapping modal dialogs for the Study Plan generation.

---

## 4. Methodologies & Technologies Used

### Machine Learning & Data Science Methods
* **Sequence Classification**: A fine-tuned **BERT (BertForSequenceClassification)** model is trained locally using `trainer.py`. It converts job titles into multi-hot encoded skill vectors, effectively learning the relationship between job titles and the required skills.
* **Regex-based Skill Extraction**: Uses exact boundary matching against the vocabulary learned by the BERT model to extract existing skills from raw resume text (`extract_data.py` & `predictor.py`).
* **Large Language Models (LLMs)**: Utilizes the **Groq API** (`llama-3.3-70b-versatile`) heavily:
  * For structured entity extraction (parsing resumes into Pydantic-defined JSON schemas to find experience, education, etc.).
  * For personalized conversational AI (the chatbot).
* **Retrieval & Content Ranking**: The `study_plan.py` broker searches the YouTube Data API and algorithmically ranks videos based on inferred difficulty levels (parsed from titles) and view counts, selecting a varied mix of "Intro", "Tutorial", and "In-depth" content.

### Application Architecture
* **Backend**: Python-based **Flask** server utilizing `flask_cors` for cross-origin interactions.
* **Document Parsing**: Utilizes `PyMuPDF` (fitz) for PDFs and `python-docx` for Word documents.

---

## 5. API Endpoints

The Flask backend exposes the following REST API endpoints:

* **`POST /api/upload`**
  * **Role**: Accepts a file upload.
  * **Action**: Parses the document text, extracts skills using the local predictor engine, and queries Groq to create a rich JSON context of the applicant.
  * **Returns**: Extracted textual skills and chatbot context object.

* **`POST /api/analyze`**
  * **Role**: Computes the skill gap for a target domain.
  * **Action**: Queries the BERT model (or fallback structured JSON) in `predictor.py` to compare user skills vs. required skills.
  * **Returns**: Match score, lists of `found_skills` and `missing_skills`, master/warning messages, and tiered structural roadmaps (`missing_by_tier`, `all_skills_by_tier`).

* **`POST /api/confused`**
  * **Role**: Determines alternative career paths for undecided users.
  * **Action**: Evaluates the user's resume skills against *all* mapped domains and returns those with a >30% match.
  * **Returns**: Array of matching domains, scores, and missing skill metrics.

* **`POST /api/chatbot`**
  * **Role**: Interactive career advice.
  * **Action**: Injects the user's resume data and conversation history into a heavily prompted Groq LLM context window.
  * **Returns**: The AI's conversational response.

* **`POST /api/study-plan`**
  * **Role**: Generates a weekly curriculum for missing skills.
  * **Action**: Uses `ResourceBroker`, which makes outbound calls to the YouTube Data API to fetch curated videos matching the missing skills. Uses a static JSON fallback library if the API key fails or quota is exceeded.
  * **Returns**: Categorized weeks with skill objectives, descriptions, and video URLs.

---

## 6. JSON Structured Data Formats

Data integrity and ML learning sets are driven by JSON configurations:

1. **`skills_knowledge.json`**: This is the core knowledge base. It links career domains (e.g., "Frontend Developer", "DevOps Engineer") to arrays of skills, categorized by strict tiers:
   * `"beginner"`, `"compulsory"`, `"intermediate"`, `"advanced"`, `"next_steps"`
   
2. **`skill_meta.json`**: Generated during the execution of `trainer.py`. It contains:
   * `"all_skills"`: A 1D flattened array of every unique skill identified, utilized as the canonical vocabulary size for the BERT classifier.
   * `"structured_data"`: A mirror of `skills_knowledge.json` leveraged by the frontend roadmap generator.

3. **Pydantic Schemas (`extract_data.py`)**: Defines strict JSON structures forced upon the LLM using Groq's JSON mode:
   * `ResumeData`: Contains `name`, `email`, `skills`, and an array of `Experience` objects (title, company, duration, responsibilities).
   * `ChatbotResumeData`: Contains logic-based fields like `current_status` (student vs. working), `years_experience`, and `career_interests`.

---

## 7. System Data Flow

1. **Upload & Ingestion**:
   * User Uploads Resume -> `Flask (/api/upload)` -> Uses `PyMuPDF` or `python-docx` to extract raw string -> Passes to `extract_skills_from_text()` for exact string matching & `extract_chatbot_context()` via Groq LLM for conversational memory -> Returns Context to Frontend state.
2. **Analysis Execution**:
   * User Inputs Domain -> `Flask (/api/analyze)` -> Passes domain and user skills to `CareerPredictor` instance.
   * `CareerPredictor` tokenizes the domain string -> Feeds to BERT model to output a probabilty matrix of required skills -> Computes overlapping matches -> Returns tiered analysis object (`missing_by_tier`, `all_skills_by_tier`) back to the Frontend.
3. **Remediation & Study Plan generation**:
   * User Clicks Study Plan -> `Flask (/api/study-plan)` -> Passes `missing_skills`.
   * `ResourceBroker` splits missing skills into logical weekly buckets -> Queries YouTube API formatting searches carefully -> Scores/Ranks videos on difficulty/views -> Returns final structured curriculum.
4. **Chatbot Interactions**:
   * User sends message via Chat Widget -> Frontend packages chat history + Groq context (from Step 1) -> `Flask (/api/chatbot)` -> Formats a dynamic system prompt -> Invokes Groq Llama3 -> Returns text response back to Widget UI.
