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
const altTitle = document.getElementById('altTitle');
const resetBtn = document.getElementById('resetBtn');
const specialMessage = document.getElementById('specialMessage');

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
    // Standard UI Transitions
    inputSection.style.display = 'none';
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // 1. Update Score and Status
    const score = data.score;
    if (typeof updateScoreCircle === 'function') updateScoreCircle(score);

    scoreStatus.textContent = data.status_text;
    scoreStatus.className = 'score-status ' + (score > 80 ? 'high' : score > 30 ? 'mid' : 'low');

    // 2. Handle Master/Warning Messages
    specialMessage.textContent = '';
    specialMessage.className = 'special-message';
    if (data.master_msg) {
        specialMessage.textContent = data.master_msg;
        specialMessage.classList.add('master');
    } else if (data.warning) {
        specialMessage.textContent = data.warning;
        specialMessage.classList.add('warning');
    }

    // 3. Update Skills Lists
    updateSkillsList(foundSkills, data.found_skills, 'found');
    updateSkillsList(missingSkills, data.missing_skills, 'missing');
    if (typeof createSkillChart === 'function') createSkillChart(data.found_skills.length, data.missing_skills.length);

    // 4. Alternative Domain Logic
    if (data.alt_domain) {
        altDomain.textContent = data.alt_domain;
        alternativeCareer.style.display = 'block';

        // Update Alt Title based on score
        if (score < 30) {
            altTitle.textContent = "Consider This Instead";
        } else {
            altTitle.textContent = "Other domains you might also be interested in";
        }

        // ONLY add the button if it doesn't exist to prevent duplicates
        if (!document.getElementById('exploreAltBtn')) {
            alternativeCareer.querySelector('.alt-card').insertAdjacentHTML('beforeend',
                `<button id="exploreAltBtn" class="analyze-btn" style="margin-top: 15px; width: auto; padding: 10px 30px; display: block; margin-left: auto; margin-right: auto; cursor: pointer;">Explore Roadmap</button>`
            );
        } else {
            document.getElementById('exploreAltBtn').style.display = 'block';
        }

        // 5. Create External Container (Outside the Black Box)
        let extRoadmap = document.getElementById('externalAltRoadmap');
        if (!extRoadmap) {
            extRoadmap = document.createElement('div');
            extRoadmap.id = 'externalAltRoadmap';
            extRoadmap.className = 'wavy-roadmap-section';
            extRoadmap.style.display = 'none';
            alternativeCareer.after(extRoadmap);
        }

        // 6. Alternative Roadmap Click Handler
        resultsSection.onclick = function (event) {
            if (event.target && event.target.id === 'exploreAltBtn') {
                extRoadmap.style.display = 'block';
                renderWavyRoadmap(data.alt_missing_by_tier, data.alt_domain, 'externalAltRoadmap');
                extRoadmap.scrollIntoView({ behavior: 'smooth' });
                event.target.style.display = 'none';
            }
        };
    } else {
        alternativeCareer.style.display = 'none';
        const oldRoadmap = document.getElementById('externalAltRoadmap');
        if (oldRoadmap) oldRoadmap.style.display = 'none';
    }

    // 7. Render Primary Roadmap
    renderWavyRoadmap(data.missing_by_tier, domainInput.value.trim(), 'mermaidContainer');
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

function renderWavyRoadmap(missingByTier, domain, containerId) {
    const container = document.getElementById(containerId);

    // Set title if it's the main roadmap container
    if (containerId === 'mermaidContainer') {
        roadmapTitle.textContent = `Strategic Path: ${domain}`;
    }

    container.innerHTML = '';

    const wrapper = document.createElement('div');
    wrapper.className = 'roadmap-wrapper';

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute('class', 'wavy-road-svg');
    svg.setAttribute('width', '1800');
    svg.setAttribute('height', '400');
    svg.setAttribute('viewBox', '0 0 1800 400');

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    // Generate a wavy path: Start at 200, wave between 50 and 350
    let d = "M 0 200";
    for (let i = 0; i < 6; i++) {
        const x1 = i * 300 + 150;
        const y1 = (i % 2 === 0) ? 50 : 350;
        const x2 = (i + 1) * 300;
        const y2 = 200;
        d += ` Q ${x1} ${y1} ${x2} ${y2}`;
    }
    path.setAttribute('d', d);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#ACC8A2');
    path.setAttribute('stroke-width', '14');
    path.setAttribute('stroke-dasharray', '20,15');
    path.setAttribute('stroke-linecap', 'round');
    svg.appendChild(path);
    wrapper.appendChild(svg);

    const nodesContainer = document.createElement('div');
    nodesContainer.className = 'nodes-container';

    const tierKeys = ['beginner', 'compulsory', 'intermediate', 'advanced'];
    const nodeLabels = ['Start', 'Beginner', 'Compulsory', 'Intermediate', 'Advanced', 'Goal'];

    nodeLabels.forEach((label, index) => {
        const nodeEl = document.createElement('div');
        nodeEl.className = 'wavy-node';

        const x = index * 300;
        nodeEl.style.left = `${x}px`;

        if (label === 'Start') {
            nodeEl.classList.add('node-start');
            nodeEl.innerHTML = '<span>YOU</span>';
        } else if (label === 'Goal') {
            nodeEl.classList.add('node-goal');
            nodeEl.innerHTML = `<span>Goal: ${domain}</span>`;
        } else {
            const tierKey = tierKeys[index - 1];
            const missing = (missingByTier && missingByTier[tierKey]) ? missingByTier[tierKey] : [];
            const isAchieved = missing.length === 0;

            if (isAchieved) nodeEl.classList.add('achieved');
            nodeEl.textContent = index;

            const content = document.createElement('div');
            // Toggle top/bottom to match the wave
            content.className = `node-content ${index % 2 !== 0 ? 'top' : 'bottom'}`;
            content.innerHTML = `
                <div class="tier-title">${label}</div>
                <div class="tier-skills">
                    <strong>${isAchieved ? 'ACHIEVED' : 'TARGET SKILLS'}</strong>
                    ${isAchieved ? '✓ All skills mastered' : missing.join(' • ')}
                </div>
            `;
            nodeEl.appendChild(content);

            const tierLabel = document.createElement('div');
            tierLabel.className = 'node-label';
            tierLabel.textContent = label;
            nodeEl.appendChild(tierLabel);
        }

        nodesContainer.appendChild(nodeEl);
    });

    wrapper.appendChild(nodesContainer);
    container.appendChild(wrapper);
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
