/**
 * UCI MVP - Live LLM Streaming Client
 * Handles real-time token streaming and reasoning display
 */

class LLMStreamingClient {
    constructor(options = {}) {
        this.wsUrl = options.wsUrl || `ws://${window.location.host}/ws`;
        this.autoConnect = options.autoConnect !== false;
        this.retryDelay = options.retryDelay || 3000;
        this.maxRetries = options.maxRetries || 5;
        
        this.ws = null;
        this.retryCount = 0;
        this.isConnected = false;
        this.eventHandlers = {};
        this.streamBuffers = new Map(); // Track multiple concurrent streams
        
        // UI Elements
        this.statusElement = null;
        this.streamContainer = null;
        
        if (this.autoConnect) {
            this.connect();
        }
        
        this.setupEventHandlers();
    }
    
    // WebSocket Connection Management
    connect() {
        console.log('Connecting to WebSocket:', this.wsUrl);
        
        try {
            this.ws = new WebSocket(this.wsUrl);
            this.setupWebSocketHandlers();
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.scheduleRetry();
        }
    }
    
    setupWebSocketHandlers() {
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.retryCount = 0;
            this.updateConnectionStatus('connected');
            this.emit('connected');
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error, event.data);
            }
        };
        
        this.ws.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason);
            this.isConnected = false;
            this.updateConnectionStatus('disconnected');
            this.emit('disconnected', event);
            
            if (!event.wasClean && this.retryCount < this.maxRetries) {
                this.scheduleRetry();
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.emit('error', error);
        };
    }
    
    scheduleRetry() {
        this.retryCount++;
        console.log(`Scheduling retry ${this.retryCount}/${this.maxRetries} in ${this.retryDelay}ms`);
        
        setTimeout(() => {
            if (this.retryCount <= this.maxRetries) {
                this.connect();
            } else {
                console.error('Max retries exceeded');
                this.updateConnectionStatus('failed');
            }
        }, this.retryDelay);
    }
    
    // Message Handling
    handleMessage(data) {
        const messageType = data.type;
        
        switch (messageType) {
            case 'llm_reasoning':
                this.handleLLMReasoning(data);
                break;
            case 'llm_test_stream':
                this.handleLLMTestStream(data);
                break;
            case 'simulation_event':
                this.handleSimulationEvent(data);
                break;
            case 'llm_test_complete':
            case 'llm_test_error':
                this.handleLLMTestComplete(data);
                break;
            case 'simulation_complete':
            case 'simulation_error':
                this.handleSimulationComplete(data);
                break;
            default:
                console.log('Unknown message type:', messageType, data);
        }
        
        // Emit generic message event
        this.emit('message', data);
    }
    
    handleLLMReasoning(data) {
        const event = data.event;
        const streamId = event.stream_id;
        
        if (event.type === 'token') {
            this.appendToken(streamId, event.content, event.section);
        } else if (event.type === 'reasoning_step') {
            this.displayReasoningStep(streamId, event.step, event.content);
        } else if (event.type === 'reasoning_complete') {
            this.completeStream(streamId, event);
        }
        
        this.emit('llm_reasoning', data);
    }
    
    handleLLMTestStream(data) {
        const event = data.event;
        const streamId = data.stream_id;
        
        if (event.type === 'token') {
            this.appendToken(streamId, event.content, event.section);
        } else if (event.type === 'reasoning_step') {
            this.displayReasoningStep(streamId, event.step, event.content);
        }
        
        this.emit('llm_test_stream', data);
    }
    
    handleSimulationEvent(data) {
        const event = data.event;
        
        if (event.type === 'llm_crew_reasoning' || event.type === 'llm_ops_reasoning') {
            const llmEvent = event.llm_event;
            const streamId = `${event.flight_id}_${event.type}`;
            
            if (llmEvent.type === 'token') {
                this.appendToken(streamId, llmEvent.content, llmEvent.section);
            } else if (llmEvent.type === 'reasoning_step') {
                this.displayReasoningStep(streamId, llmEvent.step, llmEvent.content);
            }
        }
        
        this.emit('simulation_event', data);
    }
    
    handleLLMTestComplete(data) {
        const streamId = data.stream_id;
        this.completeStream(streamId, data);
        this.emit('test_complete', data);
    }
    
    handleSimulationComplete(data) {
        this.emit('simulation_complete', data);
    }
    
    // Token Display Management
    appendToken(streamId, token, section = '') {
        if (!this.streamContainer) return;
        
        let streamElement = this.getOrCreateStreamElement(streamId);
        
        // Add section indicator if new section
        if (section && this.shouldShowSection(streamId, section)) {
            this.addSectionHeader(streamElement, section);
        }
        
        // Append token with typing effect
        const tokenSpan = document.createElement('span');
        tokenSpan.textContent = token;
        tokenSpan.className = 'token';
        
        streamElement.appendChild(tokenSpan);
        
        // Auto-scroll to latest token
        streamElement.scrollTop = streamElement.scrollHeight;
        
        // Update buffer
        if (!this.streamBuffers.has(streamId)) {
            this.streamBuffers.set(streamId, { content: '', section: '', lastSection: '' });
        }
        const buffer = this.streamBuffers.get(streamId);
        buffer.content += token;
        buffer.lastSection = section;
    }
    
    displayReasoningStep(streamId, step, content) {
        if (!this.streamContainer) return;
        
        let streamElement = this.getOrCreateStreamElement(streamId);
        
        const stepElement = document.createElement('div');
        stepElement.className = 'reasoning-step';
        stepElement.innerHTML = `
            <div class="step-header">
                <span class="step-icon"><i class="fas fa-brain"></i></span>
                <span class="step-name">${this.formatStepName(step)}</span>
            </div>
            <div class="step-content">${content}</div>
        `;
        
        streamElement.appendChild(stepElement);
        streamElement.scrollTop = streamElement.scrollHeight;
    }
    
    completeStream(streamId, data) {
        if (!this.streamContainer) return;
        
        let streamElement = this.getOrCreateStreamElement(streamId);
        
        const completeElement = document.createElement('div');
        completeElement.className = 'stream-complete';
        
        if (data.type === 'llm_test_error' || data.error) {
            completeElement.innerHTML = `
                <div class="completion-header error">
                    <span class="completion-icon"><i class="fas fa-times-circle text-danger"></i></span>
                    <span>Stream Error</span>
                </div>
                <div class="error-message">${data.error || 'Unknown error'}</div>
            `;
        } else {
            completeElement.innerHTML = `
                <div class="completion-header success">
                    <span class="completion-icon"><i class="fas fa-check-circle text-success"></i></span>
                    <span>Stream Complete</span>
                </div>
                <div class="completion-summary">
                    ${data.result?.llm_decision ? `<strong>Decision:</strong> ${data.result.llm_decision.substring(0, 100)}...` : ''}
                </div>
            `;
        }
        
        streamElement.appendChild(completeElement);
        streamElement.scrollTop = streamElement.scrollHeight;
    }
    
    // UI Helper Methods
    getOrCreateStreamElement(streamId) {
        let streamElement = document.getElementById(`stream_${streamId}`);
        
        if (!streamElement) {
            streamElement = document.createElement('div');
            streamElement.id = `stream_${streamId}`;
            streamElement.className = 'llm-stream';
            streamElement.innerHTML = `
                <div class="stream-header">
                    <span class="stream-title"><i class="fas fa-robot"></i> Stream: ${streamId}</span>
                    <span class="stream-time">${new Date().toLocaleTimeString()}</span>
                </div>
                <div class="stream-content"></div>
            `;
            
            this.streamContainer.appendChild(streamElement);
        }
        
        return streamElement.querySelector('.stream-content') || streamElement;
    }
    
    shouldShowSection(streamId, section) {
        const buffer = this.streamBuffers.get(streamId);
        return buffer && buffer.lastSection !== section;
    }
    
    addSectionHeader(streamElement, section) {
        const headerElement = document.createElement('div');
        headerElement.className = 'section-header';
        headerElement.innerHTML = `
            <span class="section-icon"><i class="fas fa-clipboard-list"></i></span>
            <span class="section-name">${this.formatStepName(section)}</span>
        `;
        streamElement.appendChild(headerElement);
    }
    
    formatStepName(step) {
        return step.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    updateConnectionStatus(status) {
        if (this.statusElement) {
            this.statusElement.className = `connection-status ${status}`;
            const statusText = {
                'connected': 'Connected',
                'disconnected': 'Disconnected',
                'failed': 'Connection Failed'
            };
            this.statusElement.textContent = statusText[status] || status;
        }
    }
    
    // Event System
    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);
    }
    
    off(event, handler) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event] = this.eventHandlers[event].filter(h => h !== handler);
        }
    }
    
    emit(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`❌ Error in event handler for ${event}:`, error);
                }
            });
        }
    }
    
    setupEventHandlers() {
        // Set up default event handlers
        this.on('connected', () => {
            console.log('LLM Streaming Client connected');
        });
        
        this.on('error', (error) => {
            console.error('LLM Streaming Client error:', error);
        });
    }
    
    // Public API Methods
    setStreamContainer(element) {
        this.streamContainer = element;
    }
    
    setStatusElement(element) {
        this.statusElement = element;
    }
    
    clearStreams() {
        if (this.streamContainer) {
            this.streamContainer.innerHTML = '';
        }
        this.streamBuffers.clear();
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
    
    // Utility Methods for Testing
    async testLLMStreaming(query = "Test LLM streaming with sample query") {
        try {
            const response = await fetch('/api/llm/stream-test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `query=${encodeURIComponent(query)}`
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('LLM streaming test started:', result);
            return result;
        } catch (error) {
            console.error('Failed to start LLM streaming test:', error);
            throw error;
        }
    }
    
    async startDaySimulation() {
        try {
            const response = await fetch('/api/simulation/start-day', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('Day simulation started:', result);
            return result;
        } catch (error) {
            console.error('Failed to start day simulation:', error);
            throw error;
        }
    }
}

// Global instance for easy access
window.llmStreaming = null;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing LLM Streaming Client');
    window.llmStreaming = new LLMStreamingClient();
});

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LLMStreamingClient;
}