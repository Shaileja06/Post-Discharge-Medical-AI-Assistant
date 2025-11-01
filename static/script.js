// ========================================
// Configuration
// ========================================
const API_BASE_URL = 'http://localhost:8000';

// ========================================
// State Management
// ========================================
let currentSessionId = null;
let isTyping = false;

// ========================================
// DOM Elements
// ========================================
const elements = {
    // Screens
    welcomeScreen: document.getElementById('welcomeScreen'),
    chatMessages: document.getElementById('chatMessages'),
    inputArea: document.getElementById('inputArea'),
    
    // Buttons
    startChatBtn: document.getElementById('startChatBtn'),
    sendBtn: document.getElementById('sendBtn'),
    newChatBtn: document.getElementById('newChatBtn'),
    infoBtn: document.getElementById('infoBtn'),
    patientsBtn: document.getElementById('patientsBtn'),
    
    // Input
    messageInput: document.getElementById('messageInput'),
    
    // Sidebar
    sidebar: document.getElementById('sidebar'),
    patientCard: document.getElementById('patientCard'),
    closeSidebar: document.getElementById('closeSidebar'),
    
    // Modals
    citationsModal: document.getElementById('citationsModal'),
    infoModal: document.getElementById('infoModal'),
    patientsModal: document.getElementById('patientsModal'),
    
    // Toast
    toastContainer: document.getElementById('toastContainer')
};

// ========================================
// Event Listeners
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    // Start chat
    elements.startChatBtn.addEventListener('click', startNewChat);
    elements.newChatBtn.addEventListener('click', startNewChat);
    
    // Send message
    elements.sendBtn.addEventListener('click', sendMessage);
    elements.messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Auto-resize textarea
    elements.messageInput.addEventListener('input', autoResizeTextarea);
    
    // Sidebar
    elements.closeSidebar.addEventListener('click', () => {
        elements.sidebar.classList.remove('active');
    });
    
    // Quick action buttons
    document.querySelectorAll('.feature-btn').forEach(btn => {
        btn.addEventListener('click', handleQuickAction);
    });
    
    // Info button
    elements.infoBtn.addEventListener('click', showSystemInfo);
    
    // Patients button
    elements.patientsBtn.addEventListener('click', showPatientsList);
    
    // Modal close buttons
    document.getElementById('closeCitationsModal').addEventListener('click', () => {
        elements.citationsModal.classList.remove('active');
    });
    
    document.getElementById('closeInfoModal').addEventListener('click', () => {
        elements.infoModal.classList.remove('active');
    });
    
    document.getElementById('closePatientsModal').addEventListener('click', () => {
        elements.patientsModal.classList.remove('active');
    });
    
    // Close modals on background click
    [elements.citationsModal, elements.infoModal, elements.patientsModal].forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
});

// ========================================
// Chat Functions
// ========================================
async function startNewChat() {
    try {
        showToast('Starting new conversation...', 'success');
        
        const response = await fetch(`${API_BASE_URL}/chat/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error('Failed to start chat');
        
        const data = await response.json();
        currentSessionId = data.session_id;
        
        // Hide welcome screen, show chat
        elements.welcomeScreen.style.display = 'none';
        elements.chatMessages.style.display = 'flex';
        elements.inputArea.style.display = 'block';
        
        // Clear messages
        elements.chatMessages.innerHTML = '';
        
        // Add greeting message
        addMessage(data.message, 'assistant', data.agent);
        
        showToast('Chat started successfully!', 'success');
    } catch (error) {
        console.error('Error starting chat:', error);
        showToast('Failed to start chat. Please try again.', 'error');
    }
}

async function sendMessage() {
    const message = elements.messageInput.value.trim();
    
    if (!message || isTyping) return;
    
    if (!currentSessionId) {
        showToast('Please start a chat first', 'warning');
        return;
    }
    
    // Add user message
    addMessage(message, 'user');
    
    // Clear input
    elements.messageInput.value = '';
    autoResizeTextarea();
    
    // Disable send button
    elements.sendBtn.disabled = true;
    isTyping = true;
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                message: message
            })
        });
        
        if (!response.ok) throw new Error('Failed to send message');
        
        const data = await response.json();
        
        // Hide typing indicator
        hideTypingIndicator();
        
        // Add assistant response
        addMessage(
            data.message, 
            'assistant', 
            data.agent,
            {
                citations: data.citations,
                urgency: data.urgency,
                usedWebSearch: data.used_web_search
            }
        );
        
        // Update patient card if patient data is received
        if (data.patient_data) {
            updatePatientCard(data.patient_data);
        }
        
    } catch (error) {
        console.error('Error sending message:', error);
        hideTypingIndicator();
        showToast('Failed to send message. Please try again.', 'error');
    } finally {
        elements.sendBtn.disabled = false;
        isTyping = false;
    }
}

function addMessage(text, role, agent = null, metadata = {}) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = role === 'user' 
        ? '<i class="fas fa-user"></i>' 
        : '<i class="fas fa-robot"></i>';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    // Add agent badge for assistant messages
    if (role === 'assistant' && agent) {
        const agentBadge = document.createElement('div');
        agentBadge.className = `agent-badge ${agent}`;
        agentBadge.innerHTML = `
            <i class="fas ${agent === 'clinical' ? 'fa-stethoscope' : 'fa-headset'}"></i>
            ${agent === 'clinical' ? 'Clinical Agent' : 'Receptionist'}
        `;
        bubble.appendChild(agentBadge);
    }
    
    // Add message text (with markdown-like formatting)
    const textContent = document.createElement('div');
    textContent.innerHTML = formatMessageText(text);
    bubble.appendChild(textContent);
    
    // Add urgency badge
    if (metadata.urgency) {
        const urgencyBadge = document.createElement('div');
        urgencyBadge.className = `urgency-badge ${metadata.urgency}`;
        urgencyBadge.innerHTML = `
            <i class="fas ${getUrgencyIcon(metadata.urgency)}"></i>
            ${metadata.urgency.toUpperCase()}
        `;
        bubble.appendChild(urgencyBadge);
    }
    
    // Add web search badge
    if (metadata.usedWebSearch) {
        const webBadge = document.createElement('div');
        webBadge.className = 'web-search-badge';
        webBadge.innerHTML = '<i class="fas fa-globe"></i> Includes web results';
        bubble.appendChild(webBadge);
    }
    
    // Add citations link
    if (metadata.citations && metadata.citations.length > 0) {
        const citationsBtn = document.createElement('button');
        citationsBtn.className = 'citations-link';
        citationsBtn.innerHTML = `
            <i class="fas fa-quote-left"></i>
            View ${metadata.citations.length} Citation${metadata.citations.length > 1 ? 's' : ''}
        `;
        citationsBtn.onclick = () => showCitations(metadata.citations);
        bubble.appendChild(citationsBtn);
    }
    
    // Add timestamp
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    bubble.appendChild(time);
    
    content.appendChild(bubble);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    elements.chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant typing-message';
    typingDiv.id = 'typingIndicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = '<i class="fas fa-robot"></i>';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const bubble = document.createElement('div');
    bubble.className = 'typing-bubble';
    bubble.innerHTML = '<span></span><span></span><span></span>';
    
    content.appendChild(bubble);
    typingDiv.appendChild(avatar);
    typingDiv.appendChild(content);
    
    elements.chatMessages.appendChild(typingDiv);
    scrollToBottom();
}

function hideTypingIndicator() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}

function formatMessageText(text) {
    // Convert **bold** to <strong>
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert *italic* to <em>
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convert newlines to <br>
    text = text.replace(/\n/g, '<br>');
    
    // Convert [1], [2] citations to styled spans
    text = text.replace(/\[(\d+)\]/g, '<span class="citation-marker">[$1]</span>');
    
    return text;
}

function getUrgencyIcon(urgency) {
    const icons = {
        emergency: 'fa-exclamation-circle',
        urgent: 'fa-exclamation-triangle',
        routine: 'fa-check-circle'
    };
    return icons[urgency] || 'fa-info-circle';
}

function scrollToBottom() {
    setTimeout(() => {
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }, 100);
}

function autoResizeTextarea() {
    const textarea = elements.messageInput;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

// ========================================
// Patient Card
// ========================================
function updatePatientCard(patientData) {
    const patientInfo = `
        <div class="patient-info">
            <h3>${patientData.patient_name}</h3>
            <span class="diagnosis-badge">
                <i class="fas fa-heartbeat"></i>
                ${patientData.primary_diagnosis}
            </span>
            
            <div class="patient-detail">
                <i class="fas fa-calendar"></i>
                Discharged: ${patientData.discharge_date}
            </div>
            
            <div class="patient-detail">
                <i class="fas fa-pills"></i>
                ${patientData.medications.length} Medications
            </div>
            
            <div class="patient-detail">
                <i class="fas fa-clipboard-check"></i>
                Follow-up scheduled
            </div>
        </div>
    `;
    
    elements.patientCard.innerHTML = patientInfo;
    showToast(`Welcome back, ${patientData.patient_name}!`, 'success');
}

// ========================================
// Quick Actions
// ========================================
function handleQuickAction(e) {
    const action = e.currentTarget.dataset.action;
    const messages = {
        medications: 'What are my medications?',
        diet: 'What are my dietary restrictions?',
        follow_up: 'When are my follow-up appointments?',
        warnings: 'What warning signs should I watch for?'
    };
    
    if (currentSessionId && messages[action]) {
        elements.messageInput.value = messages[action];
        sendMessage();
    } else {
        showToast('Please start a chat first', 'warning');
    }
}

// ========================================
// Citations Modal
// ========================================
function showCitations(citations) {
    const content = document.getElementById('citationsContent');
    
    let html = '';
    citations.forEach(citation => {
        const isWeb = citation.source === 'web';
        html += `
            <div class="citation-item ${isWeb ? 'web-source' : ''}">
                <div class="citation-header">
                    <span class="citation-id">${citation.id}</span>
                    <span class="source-badge ${citation.source}">
                        <i class="fas ${isWeb ? 'fa-globe' : 'fa-file-alt'}"></i>
                        ${citation.source}
                    </span>
                </div>
                ${citation.title ? `<strong>${citation.title}</strong><br>` : ''}
                <div class="citation-content">
                    ${citation.content}
                </div>
                ${citation.url ? `
                    <div class="citation-url">
                        <i class="fas fa-link"></i>
                        <a href="${citation.url}" target="_blank">${citation.url}</a>
                    </div>
                ` : ''}
                ${citation.relevance_score ? `
                    <div class="mt-10">
                        <small style="color: var(--text-light);">
                            Relevance: ${(citation.relevance_score * 100).toFixed(1)}%
                        </small>
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    content.innerHTML = html || '<p>No citations available</p>';
    elements.citationsModal.classList.add('active');
}

// ========================================
// System Info Modal
// ========================================
async function showSystemInfo() {
    elements.infoModal.classList.add('active');
    const content = document.getElementById('infoContent');
    content.innerHTML = '<div class="loader"></div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/health/`);
        const data = await response.json();
        
        content.innerHTML = `
            <div class="info-grid">
                <div class="info-card">
                    <h4>Status</h4>
                    <p><span class="badge">${data.status}</span></p>
                </div>
                <div class="info-card">
                    <h4>AI Model</h4>
                    <p>${data.model || 'N/A'}</p>
                </div>
                <div class="info-card">
                    <h4>Documents</h4>
                    <p>${data.document_count || 0}</p>
                </div>
                <div class="info-card">
                    <h4>Patients</h4>
                    <p>${data.patient_count || 0}</p>
                </div>
            </div>
            
            <h4 class="mt-10 mb-10">Features</h4>
            <div class="features-list">
                ${Object.entries(data.features || {}).map(([key, value]) => `
                    <div class="patient-detail">
                        <i class="fas fa-${value ? 'check-circle' : 'times-circle'}" 
                           style="color: ${value ? 'var(--secondary-color)' : 'var(--danger-color)'}"></i>
                        ${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        content.innerHTML = '<p style="color: var(--danger-color);">Failed to load system info</p>';
    }
}

// ========================================
// Patients List Modal
// ========================================
async function showPatientsList() {
    elements.patientsModal.classList.add('active');
    const content = document.getElementById('patientsContent');
    content.innerHTML = '<div class="loader"></div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/patients/list`);
        const data = await response.json();
        
        if (data.patients && data.patients.length > 0) {
            content.innerHTML = data.patients.map(patient => `
                <div class="patient-list-item">
                    <h4>${patient.name}</h4>
                    <p><i class="fas fa-calendar"></i> Discharged: ${patient.discharge_date}</p>
                    <p><i class="fas fa-stethoscope"></i> ${patient.diagnosis}</p>
                </div>
            `).join('');
        } else {
            content.innerHTML = '<p>No patients found</p>';
        }
    } catch (error) {
        content.innerHTML = '<p style="color: var(--danger-color);">Failed to load patients</p>';
    }
}

// ========================================
// Toast Notifications
// ========================================
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    }[type] || 'fa-info-circle';
    
    toast.innerHTML = `
        <i class="fas ${icon}"></i>
        <span>${message}</span>
    `;
    
    elements.toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'toastSlideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ========================================
// Add custom CSS for citation markers
// ========================================
const style = document.createElement('style');
style.textContent = `
    .citation-marker {
        display: inline-block;
        background: var(--primary-color);
        color: white;
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
        margin: 0 2px;
    }
`;
document.head.appendChild(style);