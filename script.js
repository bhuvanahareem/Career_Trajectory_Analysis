// Detect if running from Flask server or direct file access
const API_BASE = window.location.protocol === 'file:' 
    ? 'http://localhost:5000/api' 
    : '/api';

// State management
let state = {
    resumeSkills: [],
    uploadedFile: null,
    analysisResult: null
};

// DOM Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const removeFile = document.getElementById('removeFile');
const domainInput = document.getElementById('domainInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const inputSection = document.getElementById('inputSection');
const resultsSection = document.getElementById('resultsSection');
const loadingOverlay = document.getElementById('loadingOverlay');
const scoreCircle = document.getElementById('scoreCircle');
const scoreProgress = document.getElementById('scoreProgress');
const scoreValue = document.getElementById('scoreValue');
const scoreStatus = document.getElementById('scoreStatus');
const foundSkills = document.getElementById('foundSkills');
const missingSkills = document.getElementById('missingSkills');
const roadmapContainer = document.getElementById('roadmapContainer');
const roadmapTitle = document.getElementById('roadmapTitle');
const mermaidContainer = document.getElementById('mermaidContainer');
const alternativeCareer = document.getElementById('alternativeCareer');
const altDomain = document.getElementById('altDomain');
const resetBtn = document.getElementById('resetBtn');

let skillChart = null;

// Initialize Mermaid
mermaid.initialize({ 
    startOnLoad: false,
    theme: 'default',
    themeVariables: {
        primaryColor: '#ACC8A2',
        primaryTextColor: '#1A2517',
        primaryBorderColor: '#8FA87E',
        lineColor: '#1A2517',
        secondaryColor: '#C4D9BC',
        tertiaryColor: '#E8EDE0'
    }
});

// File Upload Handlers
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', handleDragOver);
dropZone.addEventListener('dragleave', handleDragLeave);
dropZone.addEventListener('drop', handleDrop);
fileInput.addEventListener('change', handleFileSelect);
removeFile.addEventListener('click', clearFile);

function handleDragOver(e) {
    e.preventDefault();
    dropZone.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    dropZone.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

async function processFile(file) {
    if (!file.type.includes('pdf') && !file.name.endsWith('.docx')) {
        alert('Please upload a PDF or DOCX file');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        alert('File size must be less than 10MB');
        return;
    }

    state.uploadedFile = file;
    fileName.textContent = file.name;
    fileInfo.style.display = 'flex';
    dropZone.style.display = 'none';

    showLoading();
    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (data.success) {
            state.resumeSkills = data.skills;
            checkAnalyzeButton();
        } else {
            throw new Error(data.error || 'Failed to process file');
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
        clearFile();
    } finally {
        hideLoading();
    }
}

function clearFile() {
    state.uploadedFile = null;
    state.resumeSkills = [];
    fileInput.value = '';
    fileInfo.style.display = 'none';
    dropZone.style.display = 'block';
    checkAnalyzeButton();
}

function checkAnalyzeButton() {
    const hasFile = state.uploadedFile !== null;
    const hasDomain = domainInput.value.trim().length > 0;
    analyzeBtn.disabled = !(hasFile && hasDomain);
}

domainInput.addEventListener('input', checkAnalyzeButton);

analyzeBtn.addEventListener('click', performAnalysis);

async function performAnalysis() {
    const domain = domainInput.value.trim();
    if (!domain || state.resumeSkills.length === 0) {
        return;
    }

    showLoading();
    try {
        const response = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                skills: state.resumeSkills,
                domain: domain
            })
        });

        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        state.analysisResult = data;
        displayResults(data);
    } catch (error) {
        alert(`Error: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function displayResults(data) {
    inputSection.style.display = 'none';
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Update score display
    const score = data.score;
    updateScoreCircle(score);
    
    // Logic Fix: Map Python 'status_text' to your UI status area
    scoreStatus.textContent = data.status_text;
    scoreStatus.className = 'score-status ' + (score > 70 ? 'high' : score > 35 ? 'mid' : 'low');

    // Update skills lists
    updateSkillsList(foundSkills, data.found_skills, 'found');
    updateSkillsList(missingSkills, data.missing_skills, 'missing');

    // Create Chart
    createSkillChart(data.found_skills.length, data.missing_skills.length);

    // Logic Fix: Handle Alternative Careers (alt_domain)
    if (score < 40 && data.alt_domain) {
        altDomain.textContent = data.alt_domain;
        alternativeCareer.style.display = 'block';
    } else {
        alternativeCareer.style.display = 'none';
    }

    // Logic Fix: Render AI-Generated Roadmap directly
    renderRoadmap(data.roadmap, domainInput.value.trim());
}

function updateScoreCircle(score) {
    const circumference = 2 * Math.PI * 45;
    const offset = circumference - (score / 100) * circumference;
    scoreProgress.style.strokeDashoffset = offset;
    animateValue(scoreValue, 0, score, 1500);
}

function animateValue(element, start, end, duration) {
    const startTime = performance.now();
    const range = end - start;
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOutCubic = 1 - Math.pow(1 - progress, 3);
        const current = start + range * easeOutCubic;
        element.textContent = Math.round(current);
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

function updateSkillsList(container, skills, type) {
    container.innerHTML = '';
    if (!skills || skills.length === 0) {
        const li = document.createElement('li');
        li.textContent = type === 'found' ? 'No matching skills found' : 'No missing skills';
        li.style.background = 'transparent';
        li.style.color = 'var(--text-muted)';
        li.style.fontStyle = 'italic';
        container.appendChild(li);
    } else {
        skills.forEach(skill => {
            const li = document.createElement('li');
            li.textContent = skill;
            container.appendChild(li);
        });
    }
}

function createSkillChart(foundCount, missingCount) {
    const ctx = document.getElementById('skillChart').getContext('2d');
    if (skillChart) skillChart.destroy();

    skillChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Found Skills', 'Missing Skills'],
            datasets: [{
                data: [foundCount, missingCount],
                backgroundColor: ['#1A2517', '#8FA87E'],
                borderColor: '#ACC8A2',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#1A2517', usePointStyle: true }
                }
            }
        }
    });
}

function renderRoadmap(mermaidSyntax, domain) {
    roadmapTitle.textContent = `Strategic Path: ${domain}`;
    mermaidContainer.innerHTML = '';
    
    const id = 'roadmap-' + Date.now();
    mermaid.render(id, mermaidSyntax).then((result) => {
        mermaidContainer.innerHTML = result.svg;
    }).catch((error) => {
        console.error('Mermaid error:', error);
        mermaidContainer.innerHTML = '<p>Unable to render AI roadmap.</p>';
    });
}

// Reset handler
resetBtn.addEventListener('click', () => {
    state.resumeSkills = [];
    state.uploadedFile = null;
    state.analysisResult = null;
    clearFile();
    domainInput.value = '';
    resultsSection.style.display = 'none';
    inputSection.style.display = 'block';
    if (skillChart) {
        skillChart.destroy();
        skillChart = null;
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

function showLoading() { loadingOverlay.style.display = 'flex'; }
function hideLoading() { loadingOverlay.style.display = 'none'; }

domainInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !analyzeBtn.disabled) performAnalysis();
});