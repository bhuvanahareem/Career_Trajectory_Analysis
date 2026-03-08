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
            // Store chatbot context extracted from resume
            if (typeof chatbotContext !== 'undefined') {
                chatbotContext = data.chatbotContext || null;
            }
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

// New DOM Elements for Confused Feature
const confusedBtn = document.getElementById('confusedBtn');
const confusedSection = document.getElementById('confusedSection');
const careerCardsGrid = document.getElementById('careerCardsGrid');
const detailedCareerView = document.getElementById('detailedCareerView');
const backToCardsBtn = document.getElementById('backToCardsBtn');
const detailedTitle = document.getElementById('detailedTitle');
const detailedScoreBadge = document.getElementById('detailedScoreBadge');
const detailedDesc = document.getElementById('detailedDesc');
const detailedMissingList = document.getElementById('detailedMissingList');
const detailedRoadmap = document.getElementById('detailedRoadmap');
const resetConfusedBtn = document.getElementById('resetConfusedBtn');

function checkAnalyzeButton() {
    const hasFile = state.uploadedFile !== null;
    const hasDomain = domainInput.value.trim().length > 0;
    analyzeBtn.disabled = !(hasFile && hasDomain);
    if (confusedBtn) confusedBtn.disabled = !hasFile;
}

domainInput.addEventListener('input', checkAnalyzeButton);
confusedBtn.addEventListener('click', fetchConfusedResults);
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

async function fetchConfusedResults() {
    if (state.resumeSkills.length === 0) return;

    showLoading();
    try {
        const response = await fetch(`${API_BASE}/confused`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ skills: state.resumeSkills })
        });

        const data = await response.json();
        if (data.success) {
            renderCareerCards(data.matches);
            inputSection.style.display = 'none';
            confusedSection.style.display = 'block';
            confusedSection.scrollIntoView({ behavior: 'smooth' });
        } else {
            throw new Error(data.error || 'Failed to analyze career paths');
        }
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
    renderWavyRoadmap(data.all_skills_by_tier, domainInput.value.trim(), 'mermaidContainer');
}

function renderCareerCards(matches) {
    careerCardsGrid.innerHTML = '';

    if (matches.length === 0) {
        careerCardsGrid.innerHTML = '<p class="no-matches">No domains found with more than 30% match. Try adding more skills to your resume!</p>';
        return;
    }

    matches.forEach((match, index) => {
        const card = document.createElement('div');
        card.className = 'career-card';
        card.style.animationDelay = `${index * 0.1}s`;

        card.innerHTML = `
            <div class="card-content">
                <h3 class="card-title">${match.domain}</h3>
                <p class="card-desc">${match.description}</p>
                <div class="card-footer">
                    <span class="match-badge">${match.score}% Match</span>
                    <span class="missing-count">${match.missing_count} skills missing</span>
                </div>
            </div>
        `;

        card.addEventListener('click', () => showDetailedCareerAnalysis(match));
        careerCardsGrid.appendChild(card);
    });
}

function showDetailedCareerAnalysis(career) {
    confusedSection.style.display = 'none';
    detailedCareerView.style.display = 'block';

    detailedTitle.textContent = career.domain;
    detailedScoreBadge.textContent = `${career.score}% Match`;
    detailedDesc.textContent = career.description;

    // Update Missing Skills List
    detailedMissingList.innerHTML = '';
    career.missing_skills.forEach(skill => {
        const li = document.createElement('li');
        li.textContent = skill;
        detailedMissingList.appendChild(li);
    });

    // Render Wavy Roadmap
    renderWavyRoadmap(career.all_skills_by_tier, career.domain, 'detailedRoadmap');

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

backToCardsBtn.addEventListener('click', () => {
    detailedCareerView.style.display = 'none';
    confusedSection.style.display = 'block';
});

resetConfusedBtn.addEventListener('click', () => {
    confusedSection.style.display = 'none';
    inputSection.style.display = 'block';
    clearFile();
});

function updateScoreCircle(score) {
    const s = parseFloat(score);
    const circumference = 2 * Math.PI * 45;
    const offset = circumference - (s / 100) * circumference;
    scoreProgress.style.strokeDashoffset = offset;
    animateValue(scoreValue, 0, s, 1500);
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

function renderWavyRoadmap(allSkillsByTier, domain, containerId) {
    const container = document.getElementById(containerId);

    // Set title if it's the main roadmap container
    if (containerId === 'mermaidContainer') {
        roadmapTitle.textContent = `Strategic Path: ${domain}`;
    }

    container.innerHTML = '';

    const wrapper = document.createElement('div');
    wrapper.className = 'roadmap-wrapper';

    // Adjust width for 5 tiers + Start + Goal (total 7 nodes)
    const numTiers = 5;
    const totalNodes = numTiers + 2;
    const spacing = 300;
    const totalWidth = (totalNodes - 1) * spacing;

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute('class', 'wavy-road-svg');
    svg.setAttribute('width', totalWidth);
    svg.setAttribute('height', '400');
    svg.setAttribute('viewBox', `0 0 ${totalWidth} 400`);

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    let d = "M 0 200";
    for (let i = 0; i < totalNodes - 1; i++) {
        const x1 = i * spacing + (spacing / 2);
        const y1 = (i % 2 === 0) ? 50 : 350;
        const x2 = (i + 1) * spacing;
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

    const tierKeys = ['beginner', 'compulsory', 'intermediate', 'advanced', 'next_steps'];
    const nodeLabels = ['Start', 'Beginner', 'Compulsory', 'Intermediate', 'Advanced', 'Next_Steps', 'Goal'];

    const userSkillsLower = (state.resumeSkills || []).map(s => s.toLowerCase());

    nodeLabels.forEach((label, index) => {
        const nodeEl = document.createElement('div');
        nodeEl.className = 'wavy-node';

        const x = index * spacing;
        nodeEl.style.left = `${x}px`;

        if (label === 'Start') {
            nodeEl.classList.add('node-start');
            nodeEl.innerHTML = '<span>YOU</span>';
        } else if (label === 'Goal') {
            nodeEl.classList.add('node-goal');
            nodeEl.innerHTML = `<span>Goal: ${domain}</span>`;
        } else {
            const tierKey = tierKeys[index - 1];
            const allSkills = (allSkillsByTier && allSkillsByTier[tierKey]) ? allSkillsByTier[tierKey] : [];

            // Check which skills are mastered
            const skillsHtml = allSkills.map(skill => {
                const isMastered = userSkillsLower.includes(skill.toLowerCase());
                return `<span class="skill-tag ${isMastered ? 'mastered' : 'missing'}">${isMastered ? '✓ ' : ''}${skill}</span>`;
            }).join(' ');

            const isTierMastered = allSkills.length > 0 && allSkills.every(s => userSkillsLower.includes(s.toLowerCase()));

            if (isTierMastered) nodeEl.classList.add('achieved');
            nodeEl.textContent = index;

            const content = document.createElement('div');
            // Toggle top/bottom to match the wave
            content.className = `node-content ${index % 2 !== 0 ? 'top' : 'bottom'}`;
            content.innerHTML = `
                <div class="tier-title">${label}</div>
                <div class="tier-skills">
                    <strong>${isTierMastered ? 'ACHIEVED' : 'PATHWAY SKILLS'}</strong><br>
                    ${skillsHtml || '<span class="text-muted">No specific skills listed</span>'}
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
    confusedSection.style.display = 'none';
    detailedCareerView.style.display = 'none';
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

// ==============================================
// CHATBOT LOGIC
// ==============================================

const chatbotToggle = document.getElementById('chatbotToggle');
const chatbotPanel = document.getElementById('chatbotPanel');
const chatbotCloseBtn = document.getElementById('chatbotCloseBtn');
const chatbotBackBtn = document.getElementById('chatbotBackBtn');
const chatbotMessages = document.getElementById('chatbotMessages');
const chatbotInput = document.getElementById('chatbotInput');
const chatbotSendBtn = document.getElementById('chatbotSendBtn');

let chatMessages = [];  // [{ role: 'user'|'bot', text: '...' }]
let chatbotOpen = false;
let chatbotInitialized = false;
let isSending = false;
let chatbotContext = null;  // Extracted career context from resume

// Open chatbot
chatbotToggle.addEventListener('click', () => {
    chatbotOpen = true;
    chatbotPanel.classList.add('open');
    chatbotToggle.classList.add('hidden');
    chatbotInput.focus();

    // Send initial greeting on first open
    if (!chatbotInitialized) {
        chatbotInitialized = true;
        sendInitialGreeting();
    }
});

// Close chatbot
chatbotCloseBtn.addEventListener('click', () => {
    chatbotOpen = false;
    chatbotPanel.classList.remove('open');
    chatbotToggle.classList.remove('hidden');
});

// Send on Enter
chatbotInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !isSending) sendChatMessage();
});

// Send on button click
chatbotSendBtn.addEventListener('click', () => {
    if (!isSending) sendChatMessage();
});

// Back button — removes last user+bot exchange
chatbotBackBtn.addEventListener('click', () => {
    if (chatMessages.length <= 1) return;

    // Remove messages from end: last bot reply, then last user message
    let removed = 0;
    while (chatMessages.length > 1 && removed < 2) {
        const last = chatMessages[chatMessages.length - 1];
        chatMessages.pop();
        removed++;
        if (last.role === 'user') break;
    }

    renderChatMessages();
    updateBackButton();
});

function sendInitialGreeting() {
    let greeting;
    if (state.resumeSkills && state.resumeSkills.length > 0) {
        greeting = "I've reviewed the skills from your resume. What are your current interests? I'd love to help you figure out the best next step in your career.";
    } else {
        greeting = "Hi there! I'm your career advisor. To get started, could you tell me — are you currently a student, a working professional, or on a gap year?";
    }

    chatMessages.push({ role: 'bot', text: greeting });
    renderChatMessages();
    updateBackButton();
}

async function sendChatMessage() {
    const text = chatbotInput.value.trim();
    if (!text || isSending) return;

    isSending = true;
    chatbotSendBtn.disabled = true;

    // Add user message
    chatMessages.push({ role: 'user', text: text });
    appendBubble('user', text);
    chatbotInput.value = '';

    // Show typing indicator
    const typingEl = showTypingIndicator();
    scrollChatToBottom();

    // Build resume context for API
    let resumeContext = null;
    if (state.resumeSkills && state.resumeSkills.length > 0) {
        resumeContext = {
            skills: state.resumeSkills,
            domain: domainInput.value.trim() || 'technology',
            chatbotContext: chatbotContext
        };
    }

    try {
        const response = await fetch(`${API_BASE}/chatbot`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: chatMessages,
                resumeContext: resumeContext
            })
        });

        const data = await response.json();
        removeTypingIndicator(typingEl);

        if (data.error) {
            const errMsg = { role: 'bot', text: 'Sorry, something went wrong. Please try again in a moment.' };
            chatMessages.push(errMsg);
            appendBubble('bot', errMsg.text);
        } else {
            const botMsg = { role: 'bot', text: data.reply };
            chatMessages.push(botMsg);
            appendBubble('bot', data.reply);
        }
    } catch (err) {
        removeTypingIndicator(typingEl);
        const errMsg = { role: 'bot', text: 'Connection error. Please check if the server is running.' };
        chatMessages.push(errMsg);
        appendBubble('bot', errMsg.text);
    } finally {
        isSending = false;
        chatbotSendBtn.disabled = false;
        scrollChatToBottom();
        updateBackButton();
        chatbotInput.focus();
    }
}

function appendBubble(role, text) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    bubble.textContent = text;
    chatbotMessages.appendChild(bubble);
    scrollChatToBottom();
}

function renderChatMessages() {
    chatbotMessages.innerHTML = '';
    chatMessages.forEach(msg => appendBubble(msg.role, msg.text));
    scrollChatToBottom();
}

function showTypingIndicator() {
    const typing = document.createElement('div');
    typing.className = 'typing-indicator';
    typing.innerHTML = '<span></span><span></span><span></span>';
    chatbotMessages.appendChild(typing);
    scrollChatToBottom();
    return typing;
}

function removeTypingIndicator(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
}

function scrollChatToBottom() {
    requestAnimationFrame(() => {
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    });
}

function updateBackButton() {
    chatbotBackBtn.disabled = chatMessages.length <= 1;
}

// ==============================================
// STUDY PLAN FEATURE
// ==============================================

const studyPlanBtnWrapper = document.getElementById('studyPlanBtnWrapper');
const studyPlanBtn = document.getElementById('studyPlanBtn');
const spOverlay = document.getElementById('spOverlay');
const spCard = document.getElementById('spCard');
const spCloseBtn = document.getElementById('spCloseBtn');
const spDomainTitle = document.getElementById('spDomainTitle');
const spDomainDesc = document.getElementById('spDomainDesc');
const spSkillLevelBadge = document.getElementById('spSkillLevelBadge');
const spFoundChips = document.getElementById('spFoundChips');
const spMissingChips = document.getElementById('spMissingChips');
const spMotivationText = document.getElementById('spMotivationText');
const spWeekPlan = document.getElementById('spWeekPlan');
const spDownloadBtn = document.getElementById('spDownloadBtn');

let currentStudyPlan = null; // cache the last fetched plan

// Hook into existing displayResults to show button
const _origDisplayResults = displayResults;
displayResults = function (data) {
    _origDisplayResults(data);
    if (data.missing_skills && data.missing_skills.length > 0) {
        studyPlanBtnWrapper.style.display = 'flex';
    } else {
        studyPlanBtnWrapper.style.display = 'none';
    }
};

// Open handler
studyPlanBtn.addEventListener('click', openStudyPlan);

// Close handlers
spCloseBtn.addEventListener('click', closeStudyPlan);
spOverlay.addEventListener('click', (e) => {
    if (e.target === spOverlay) closeStudyPlan();
});
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeStudyPlan();
});

// Download handler
spDownloadBtn.addEventListener('click', downloadStudyPlan);

async function openStudyPlan() {
    if (!state.analysisResult) return;
    const data = state.analysisResult;

    // Show loading state on button
    studyPlanBtn.disabled = true;
    studyPlanBtn.querySelector('.sp-btn-text').textContent = 'Building your plan…';

    try {
        const response = await fetch(`${API_BASE}/study-plan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                missing_skills: data.missing_skills || [],
                found_skills: data.found_skills || [],
                score: data.score || 0,
                domain: domainInput.value.trim(),
                description: data.description || '',
            })
        });

        const plan = await response.json();
        if (!plan.success) throw new Error(plan.error || 'Failed to build plan');

        currentStudyPlan = plan;
        renderStudyPlan(plan);

    } catch (err) {
        alert(`Could not build your study plan: ${err.message}`);
    } finally {
        studyPlanBtn.disabled = false;
        studyPlanBtn.querySelector('.sp-btn-text').textContent = 'Get study plan to excel';
    }
}

function renderStudyPlan(plan) {
    // --- Header ---
    spDomainTitle.textContent = plan.domain || domainInput.value.trim();
    spDomainDesc.textContent = plan.description || '';

    const levelColors = { Beginner: '#4ade80', Intermediate: '#60a5fa', Advanced: '#f472b6' };
    spSkillLevelBadge.textContent = `Your Level: ${plan.skill_level}`;
    spSkillLevelBadge.style.background = levelColors[plan.skill_level] || '#ACC8A2';

    // --- Found Chips ---
    spFoundChips.innerHTML = '';
    (plan.found_skills || []).forEach(skill => {
        const chip = document.createElement('span');
        chip.className = 'sp-chip sp-chip-found';
        chip.textContent = skill;
        spFoundChips.appendChild(chip);
    });
    if (!plan.found_skills || plan.found_skills.length === 0) {
        spFoundChips.innerHTML = '<span class="sp-chip-empty">None matched yet — keep building!</span>';
    }

    // --- Missing Chips ---
    spMissingChips.innerHTML = '';
    (plan.missing_skills || []).forEach(skill => {
        const chip = document.createElement('span');
        chip.className = 'sp-chip sp-chip-missing';
        chip.textContent = skill;
        spMissingChips.appendChild(chip);
    });

    // --- Motivation Banner ---
    const scoreInt = Math.round(plan.score || 0);
    spMotivationText.textContent =
        `Your study plan to go from ${scoreInt}% to a 100% expert in ${plan.domain || 'this domain'}!`;

    // --- Week Plan ---
    spWeekPlan.innerHTML = '';
    if (!plan.weeks || plan.weeks.length === 0) {
        spWeekPlan.innerHTML = '<p class="sp-no-plan">🎉 You already have all the skills — you\'re an expert!</p>';
    } else {
        plan.weeks.forEach((weekData, idx) => {
            const box = renderWeekBox(weekData, idx);
            spWeekPlan.appendChild(box);
        });
    }

    // --- Show modal with entrance animation ---
    spOverlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    // Staggered entrance for week boxes
    setTimeout(() => {
        const boxes = spWeekPlan.querySelectorAll('.sp-week-box');
        boxes.forEach((box, i) => {
            box.style.animationDelay = `${i * 0.12}s`;
            box.classList.add('sp-week-box--visible');
        });
    }, 80);
}

function renderWeekBox(weekData, idx) {
    const box = document.createElement('div');
    box.className = 'sp-week-box';

    const weekThemes = ['#ACC8A2', '#8FA87E', '#6B8E5E', '#4f7042', '#3a5530', '#2D3A28'];
    const accentColor = weekThemes[idx % weekThemes.length];

    box.innerHTML = `
        <div class="sp-week-label" style="border-color: ${accentColor};">
            <span class="sp-week-number">Week</span>
            <span class="sp-week-num-large">${weekData.week}</span>
        </div>
        <div class="sp-week-content"></div>
    `;

    const content = box.querySelector('.sp-week-content');

    weekData.skills.forEach(skillObj => {
        const skillRow = document.createElement('div');
        skillRow.className = 'sp-skill-row';

        // Source icon map
        const sourceIcon = {
            'YouTube': '▶',
            'W3Schools': 'W',
            'GeeksForGeeks': 'G',
            'MDN': 'M',
            'Official Docs': '📄',
            'GitHub': '⬡',
        };

        const resourcesHtml = skillObj.resources.map(r => {
            const icon = sourceIcon[r.source] || '🔗';
            const meta = [r.duration, r.views, r.level_tag].filter(Boolean).join(' · ');
            const metaHtml = meta ? `<span class="sp-link-meta">${meta}</span>` : '';
            return `
                <a href="${r.url}" target="_blank" rel="noopener noreferrer" class="sp-resource-link" title="${r.title}">
                    <span class="sp-link-icon sp-src-${r.source.replace(/\s+/g, '-').toLowerCase()}">${icon}</span>
                    <span class="sp-link-body">
                        <span class="sp-link-title">${r.title}</span>
                        ${metaHtml}
                    </span>
                    <span class="sp-link-ext">↗</span>
                </a>`;
        }).join('');

        skillRow.innerHTML = `
            <div class="sp-skill-name">
                <span class="sp-skill-dot" style="background:${accentColor}"></span>
                ${skillObj.skill}
            </div>
            <div class="sp-resources-col">${resourcesHtml}</div>
        `;
        content.appendChild(skillRow);
    });

    return box;
}

function closeStudyPlan() {
    spOverlay.style.display = 'none';
    document.body.style.overflow = '';
}

// ─── PDF Export ───────────────────────────────────────────────────────────────
async function downloadStudyPlan() {
    if (!currentStudyPlan) return;

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

    const PAGE_W = 210;
    const PAGE_H = 297;
    const MARGIN = 18;
    const CONTENT_W = PAGE_W - MARGIN * 2;
    const OLIVE = [26, 37, 23];
    const SAGE = [172, 200, 162];
    const WHITE = [255, 255, 255];
    const MUTED = [80, 80, 80];

    let y = 0;

    function checkPage(needed = 10) {
        if (y + needed > PAGE_H - 14) {
            doc.addPage();
            y = MARGIN;
            drawPageBranding();
        }
    }

    function drawPageBranding() {
        // Top bar
        doc.setFillColor(...OLIVE);
        doc.rect(0, 0, PAGE_W, 10, 'F');
        doc.setFontSize(7);
        doc.setTextColor(...SAGE);
        doc.setFont('helvetica', 'bold');
        doc.text('CAREER TRAJECTORY  |  PERSONALIZED STUDY PLAN', MARGIN, 6.5);

        // Bottom bar
        doc.setFillColor(...SAGE);
        doc.rect(0, PAGE_H - 8, PAGE_W, 8, 'F');
        doc.setFontSize(6.5);
        doc.setTextColor(...OLIVE);
        doc.text('Generated by Career Trajectory AI  •  Your path to mastery starts here.', MARGIN, PAGE_H - 3.5);
    }

    // ── Cover ──────────────────────────────────────────────────────────────────
    doc.setFillColor(...OLIVE);
    doc.rect(0, 0, PAGE_W, 60, 'F');

    // Decorative sage stripe
    doc.setFillColor(...SAGE);
    doc.rect(0, 58, PAGE_W, 3, 'F');

    doc.setFontSize(7);
    doc.setTextColor(...SAGE);
    doc.setFont('helvetica', 'bold');
    doc.text('CAREER TRAJECTORY', MARGIN, 16);

    doc.setFontSize(22);
    doc.setTextColor(...WHITE);
    doc.setFont('helvetica', 'bold');
    const titleLines = doc.splitTextToSize(`Personalized Study Plan: ${currentStudyPlan.domain}`, CONTENT_W);
    doc.text(titleLines, MARGIN, 30);

    doc.setFontSize(10);
    doc.setTextColor(...SAGE);
    doc.setFont('helvetica', 'normal');
    doc.text(currentStudyPlan.description, MARGIN, 30 + titleLines.length * 9 + 4, { maxWidth: CONTENT_W });

    y = 72;
    drawPageBranding();

    // ── Level Badge ────────────────────────────────────────────────────────────
    const levelColors = { Beginner: [74, 222, 128], Intermediate: [96, 165, 250], Advanced: [244, 114, 182] };
    const lc = levelColors[currentStudyPlan.skill_level] || SAGE;
    doc.setFillColor(...lc);
    doc.roundedRect(MARGIN, y, 50, 8, 2, 2, 'F');
    doc.setFontSize(8);
    doc.setTextColor(...OLIVE);
    doc.setFont('helvetica', 'bold');
    doc.text(`Your Level: ${currentStudyPlan.skill_level}`, MARGIN + 4, y + 5.5);
    y += 14;

    // ── Skills You Have ────────────────────────────────────────────────────────
    checkPage(20);
    doc.setFontSize(11);
    doc.setTextColor(...OLIVE);
    doc.setFont('helvetica', 'bold');
    doc.text('Skills You Have', MARGIN, y);
    y += 5;
    doc.setFillColor(...SAGE);
    doc.rect(MARGIN, y, CONTENT_W, 0.5, 'F');
    y += 4;

    const foundSkillsList = currentStudyPlan.found_skills || [];
    if (foundSkillsList.length > 0) {
        let chipX = MARGIN;
        foundSkillsList.forEach(skill => {
            const tw = doc.getTextWidth(skill) + 8;
            if (chipX + tw > PAGE_W - MARGIN) { chipX = MARGIN; y += 8; checkPage(8); }
            doc.setFillColor(220, 237, 215);
            doc.roundedRect(chipX, y - 4, tw, 6, 1.5, 1.5, 'F');
            doc.setFontSize(7.5);
            doc.setTextColor(...OLIVE);
            doc.setFont('helvetica', 'normal');
            doc.text(skill, chipX + 4, y + 0.5);
            chipX += tw + 3;
        });
        y += 10;
    } else {
        doc.setFontSize(9); doc.setTextColor(...MUTED);
        doc.text('None matched yet.', MARGIN, y); y += 8;
    }

    // ── Skills to Acquire ──────────────────────────────────────────────────────
    checkPage(20);
    doc.setFontSize(11);
    doc.setTextColor(...OLIVE);
    doc.setFont('helvetica', 'bold');
    doc.text('Skills to Acquire', MARGIN, y);
    y += 5;
    doc.setFillColor(...SAGE);
    doc.rect(MARGIN, y, CONTENT_W, 0.5, 'F');
    y += 4;

    const missingSkillsList = currentStudyPlan.missing_skills || [];
    if (missingSkillsList.length > 0) {
        let chipX = MARGIN;
        missingSkillsList.forEach(skill => {
            const tw = doc.getTextWidth(skill) + 8;
            if (chipX + tw > PAGE_W - MARGIN) { chipX = MARGIN; y += 8; checkPage(8); }
            doc.setFillColor(200, 215, 190);
            doc.roundedRect(chipX, y - 4, tw, 6, 1.5, 1.5, 'F');
            doc.setFontSize(7.5);
            doc.setTextColor(...OLIVE);
            doc.setFont('helvetica', 'normal');
            doc.text(skill, chipX + 4, y + 0.5);
            chipX += tw + 3;
        });
        y += 10;
    }

    // ── Motivation Banner ──────────────────────────────────────────────────────
    checkPage(16);
    doc.setFillColor(...OLIVE);
    doc.roundedRect(MARGIN, y, CONTENT_W, 12, 3, 3, 'F');
    doc.setFontSize(9.5);
    doc.setTextColor(...SAGE);
    doc.setFont('helvetica', 'bold');
    const motText = `Your study plan to go from ${Math.round(currentStudyPlan.score || 0)}% to a 100% expert in ${currentStudyPlan.domain}!`;
    const motLines = doc.splitTextToSize(motText, CONTENT_W - 10);
    doc.text(motLines, MARGIN + 5, y + 7.8, { maxWidth: CONTENT_W - 10 });
    y += 18;

    // ── Week Plans ─────────────────────────────────────────────────────────────
    const weekAccents = [[172, 200, 162], [143, 168, 126], [107, 142, 94], [79, 112, 66], [58, 85, 48], [45, 58, 40]];

    (currentStudyPlan.weeks || []).forEach((weekData, idx) => {
        checkPage(24);
        const accent = weekAccents[idx % weekAccents.length];

        // Week header bar
        doc.setFillColor(...accent);
        doc.roundedRect(MARGIN, y, CONTENT_W, 9, 2, 2, 'F');
        doc.setFontSize(10);
        doc.setTextColor(...OLIVE);
        doc.setFont('helvetica', 'bold');
        doc.text(`Week ${weekData.week}`, MARGIN + 5, y + 6.2);
        y += 12;

        weekData.skills.forEach(skillObj => {
            checkPage(10);
            // Skill name
            doc.setFontSize(9);
            doc.setTextColor(...OLIVE);
            doc.setFont('helvetica', 'bold');
            doc.text(`• ${skillObj.skill}`, MARGIN + 4, y);
            y += 5;

            // Skill description
            if (skillObj.description) {
                checkPage(10);
                doc.setFontSize(8);
                doc.setTextColor(...MUTED);
                doc.setFont('helvetica', 'italic');
                const descLines = doc.splitTextToSize(skillObj.description, CONTENT_W - 10);
                doc.text(descLines, MARGIN + 6, y);
                y += descLines.length * 4 + 2;
            }

            // Resources
            skillObj.resources.forEach(r => {
                checkPage(8);
                doc.setFontSize(8);
                doc.setTextColor(...MUTED);
                doc.setFont('helvetica', 'normal');

                const meta = [r.source, r.duration, r.level_tag].filter(Boolean).join(' · ');
                const titleText = doc.splitTextToSize(`   ${r.title}`, CONTENT_W - 20); // Removed arrow
                doc.text(titleText, MARGIN + 10, y);
                y += titleText.length * 4.5;

                if (meta) {
                    doc.setFontSize(7);
                    doc.setTextColor(120, 140, 110);
                    doc.text(`     ${meta}`, MARGIN + 10, y);
                    y += 4;
                }

                // Clickable URL
                doc.setFontSize(7);
                doc.setTextColor(26, 37, 23);
                const urlText = r.url.length > 70 ? r.url.substring(0, 67) + '…' : r.url;
                doc.textWithLink(`     ${urlText}`, MARGIN + 10, y, { url: r.url });
                y += 5.5;
            });
            y += 3;
        });
        y += 4;
    });

    const filename = `Study_Plan_${(currentStudyPlan.domain || 'Career').replace(/\s+/g, '_')}.pdf`;
    doc.save(filename);
}
