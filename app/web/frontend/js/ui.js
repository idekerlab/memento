/**
 * UI utility functions for the Memento Web Interface
 */
class MementoUI {
    constructor() {
        this.activeNetworkUUID = null;
        this.networksList = [];
        this.currentView = 'init'; // 'init' or 'operation'
        
        // Track which sections are open/closed
        this.openSections = {
            'primary-instructions': false,
            'schema': false,
            'active-actions': true,
            'recent-episodes': false,
            'errors': false,
            'reasoning': false,
            'tasks': false,
            'results': false
        };
    }
    
    /**
     * Initialize UI event handlers
     */
    init() {
        this._setupTabSwitching();
        this._setupCollapsibleSections();
        this._setupButtons();
        
        // Initialize network search
        const searchInput = document.getElementById('network-search');
        if (searchInput) {
            searchInput.addEventListener('input', (event) => {
                this._filterNetworks(event.target.value);
            });
        }
    }
    
    /**
     * Setup tab switching in initialization view
     */
    _setupTabSwitching() {
        const selectKgBtn = document.getElementById('select-kg-tab-btn');
        const emptyKgBtn = document.getElementById('empty-kg-tab-btn');
        const selectKgTab = document.getElementById('select-kg-tab');
        const emptyKgTab = document.getElementById('empty-kg-tab');
        
        if (selectKgBtn && emptyKgBtn && selectKgTab && emptyKgTab) {
            selectKgBtn.addEventListener('click', () => {
                selectKgBtn.classList.add('active');
                emptyKgBtn.classList.remove('active');
                selectKgTab.classList.add('active');
                emptyKgTab.classList.remove('active');
            });
            
            emptyKgBtn.addEventListener('click', () => {
                emptyKgBtn.classList.add('active');
                selectKgBtn.classList.remove('active');
                emptyKgTab.classList.add('active');
                selectKgTab.classList.remove('active');
            });
        }
    }
    
    /**
     * Setup collapsible sections
     */
    _setupCollapsibleSections() {
        const sections = document.querySelectorAll('.collapsible-section');
        
        sections.forEach(section => {
            const header = section.querySelector('.collapsible-header');
            const content = section.querySelector('.collapsible-content');
            const toggleIcon = section.querySelector('.toggle-icon');
            const title = section.querySelector('h3').textContent.toLowerCase().replace(/\s+/g, '-');
            
            // Set initial state based on openSections
            if (this.openSections[title]) {
                section.classList.add('open');
                toggleIcon.textContent = '-';
            } else {
                section.classList.remove('open');
                toggleIcon.textContent = '+';
            }
            
            header.addEventListener('click', () => {
                const isOpen = section.classList.toggle('open');
                toggleIcon.textContent = isOpen ? '-' : '+';
                this.openSections[title] = isOpen;
            });
        });
    }
    
    /**
     * Setup workflow buttons
     */
    _setupButtons() {
        // Initialization view buttons
        const createEmptyKgBtn = document.getElementById('create-empty-kg-btn');
        if (createEmptyKgBtn) {
            createEmptyKgBtn.addEventListener('click', () => {
                const initialAction = document.getElementById('initial-action').value.trim();
                if (!initialAction) {
                    this.showStatus('Please enter an initial action description', 'error');
                    return;
                }
                
                // Signal to app.js to initialize empty KG
                document.dispatchEvent(new CustomEvent('initialize-empty', {
                    detail: { initialAction }
                }));
            });
        }
        
        // Operation view buttons
        const nextEpisodeBtn = document.getElementById('next-episode-btn');
        const runPromptBtn = document.getElementById('run-prompt-btn');
        const executeTasksBtn = document.getElementById('execute-tasks-btn');
        const snapshotBtn = document.getElementById('snapshot-btn');
        
        if (nextEpisodeBtn) {
            nextEpisodeBtn.addEventListener('click', () => {
                document.dispatchEvent(new CustomEvent('next-episode'));
            });
        }
        
        if (runPromptBtn) {
            runPromptBtn.addEventListener('click', () => {
                document.dispatchEvent(new CustomEvent('run-prompt'));
            });
        }
        
        if (executeTasksBtn) {
            executeTasksBtn.addEventListener('click', () => {
                document.dispatchEvent(new CustomEvent('execute-tasks'));
            });
        }
        
        if (snapshotBtn) {
            snapshotBtn.addEventListener('click', () => {
                document.dispatchEvent(new CustomEvent('save-snapshot'));
            });
        }
    }
    
    /**
     * Switch between initialization and operation views
     * @param {string} view - 'init' or 'operation'
     */
    switchView(view) {
        const initView = document.getElementById('init-view');
        const operationView = document.getElementById('operation-view');
        
        if (view === 'init') {
            initView.classList.remove('hidden');
            operationView.classList.add('hidden');
            this.currentView = 'init';
        } else if (view === 'operation') {
            initView.classList.add('hidden');
            operationView.classList.remove('hidden');
            this.currentView = 'operation';
        }
    }
    
    /**
     * Show status overlay with message
     * @param {string} message - Message to display
     * @param {string} type - 'info', 'success', 'error', etc.
     * @param {number} duration - How long to show the message (ms), 0 for indefinite
     */
    showStatus(message, type = 'info', duration = 3000) {
        const overlay = document.getElementById('status-overlay');
        const statusMessage = document.getElementById('status-message');
        
        statusMessage.textContent = message;
        statusMessage.className = 'status-message ' + type;
        overlay.classList.remove('hidden');
        
        if (duration > 0) {
            setTimeout(() => {
                overlay.classList.add('hidden');
            }, duration);
        }
        
        return {
            close: () => overlay.classList.add('hidden')
        };
    }
    
    /**
     * Show a confirmation dialog with custom options
     * @param {string} message - Message to display
     * @param {Array} options - Array of option objects, each with label and value properties
     * @returns {Promise} - Resolves to the value of the selected option
     */
    showConfirmDialog(message, options) {
        console.log('Showing confirmation dialog with message:', message);
        
        // First, create a unique dialog ID to avoid conflicts
        const dialogId = 'dialog-' + Date.now();
        
        // Remove any existing dialog
        const existingDialog = document.querySelector('.dialog-overlay');
        if (existingDialog) {
            document.body.removeChild(existingDialog);
        }
        
        return new Promise((resolve) => {
            // Create dialog container with inline styles to ensure visibility
            const overlay = document.createElement('div');
            overlay.id = dialogId;
            overlay.className = 'dialog-overlay';
            
            // Force critical styles inline to override any potential CSS issues
            Object.assign(overlay.style, {
                position: 'fixed',
                top: '0',
                left: '0',
                width: '100%',
                height: '100%',
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                zIndex: '9999', // Very high z-index to ensure it's on top
                pointerEvents: 'auto'
            });
            
            // Create dialog box
            const dialog = document.createElement('div');
            dialog.className = 'dialog-box';
            
            // Force critical styles inline
            Object.assign(dialog.style, {
                backgroundColor: 'white',
                padding: '30px',
                borderRadius: '8px',
                maxWidth: '500px',
                width: '90%',
                boxShadow: '0 8px 16px rgba(0, 0, 0, 0.2)',
                position: 'relative',
                zIndex: '10000' // Even higher than the overlay
            });
            
            // Add message
            const messageEl = document.createElement('p');
            messageEl.textContent = message;
            Object.assign(messageEl.style, {
                marginBottom: '20px',
                fontSize: '1.1rem',
                lineHeight: '1.5',
                color: '#343a40'
            });
            dialog.appendChild(messageEl);
            
            // Add buttons
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'dialog-buttons';
            Object.assign(buttonContainer.style, {
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '15px',
                marginTop: '25px'
            });
            
            // Add buttons with click handlers
            options.forEach(option => {
                const button = document.createElement('button');
                button.textContent = option.label;
                button.className = option.primary ? 'primary-button' : 'secondary-button';
                
                Object.assign(button.style, {
                    padding: '10px 20px',
                    fontSize: '1rem',
                    cursor: 'pointer',
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: option.primary ? '#4a6fa5' : '#6b8cae',
                    color: 'white',
                    fontWeight: option.primary ? 'bold' : 'normal'
                });
                
                // Add hover effect
                button.onmouseover = () => {
                    button.style.backgroundColor = option.primary ? '#3d5d8a' : '#5a7694';
                };
                button.onmouseout = () => {
                    button.style.backgroundColor = option.primary ? '#4a6fa5' : '#6b8cae';
                };
                
                button.onclick = () => {
                    console.log('Dialog option selected:', option.value);
                    if (document.getElementById(dialogId)) {
                        document.body.removeChild(overlay);
                    }
                    resolve(option.value);
                };
                
                buttonContainer.appendChild(button);
            });
            
            // Assemble the dialog
            dialog.appendChild(buttonContainer);
            overlay.appendChild(dialog);
            
            // Add to document
            document.body.appendChild(overlay);
            console.log('Dialog added to DOM with ID:', dialogId);
            
            // Set a timeout to check if dialog is still in DOM after a brief delay
            setTimeout(() => {
                if (!document.getElementById(dialogId)) {
                    console.warn('Dialog removed unexpectedly from DOM');
                }
            }, 100);
        });
    }
    
    /**
     * Render the list of NDEx networks
     * @param {Array} networks - List of networks from API
     */
    renderNetworks(networks) {
        this.networksList = networks;
        const networksList = document.getElementById('networks-list');
        
        if (!networksList) return;
        
        networksList.innerHTML = '';
        
        if (networks.length === 0) {
            networksList.innerHTML = '<div class="loading">No networks found</div>';
            return;
        }
        
        networks.forEach(network => {
            const networkItem = document.createElement('div');
            networkItem.className = 'network-item';
            networkItem.dataset.uuid = network.uuid;
            
            // Set selected state if this is the active network
            if (network.uuid === this.activeNetworkUUID) {
                networkItem.classList.add('selected');
            }
            
            // Format creation date
            let creationDate = 'Unknown date';
            if (network.creation_time) {
                try {
                    const date = new Date(network.creation_time);
                    creationDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                } catch (e) {
                    creationDate = network.creation_time;
                }
            }
            
            networkItem.innerHTML = `
                <div class="network-name">${network.name || 'Unnamed Network'}</div>
                <div class="network-description">${network.description || 'No description'}</div>
                <div class="network-date">${creationDate}</div>
            `;
            
            networkItem.addEventListener('click', () => {
                this._selectNetwork(network.uuid);
            });
            
            networksList.appendChild(networkItem);
        });
    }
    
    /**
     * Filter networks list by search query
     * @param {string} query - Search query
     */
    _filterNetworks(query) {
        if (!this.networksList.length) return;
        
        const filtered = this.networksList.filter(network => {
            const name = (network.name || '').toLowerCase();
            const description = (network.description || '').toLowerCase();
            query = query.toLowerCase();
            
            return name.includes(query) || description.includes(query);
        });
        
        this.renderNetworks(filtered);
    }
    
    /**
     * Select a network from the list
     * @param {string} uuid - NDEx network UUID
     */
    _selectNetwork(uuid) {
        this.activeNetworkUUID = uuid;
        
        // Update selection UI
        const items = document.querySelectorAll('.network-item');
        items.forEach(item => {
            if (item.dataset.uuid === uuid) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
        
        // Signal to app.js to initialize from NDEx
        document.dispatchEvent(new CustomEvent('initialize-ndex', {
            detail: { uuid }
        }));
    }
    
    /**
     * Update episode information
     * @param {Object} episode - Episode data
     */
    updateEpisodeInfo(episode) {
        if (!episode) {
            document.getElementById('episode-id').textContent = 'Episode: none';
            document.getElementById('agent-id').textContent = 'Agent: unknown';
            return;
        }
        
        document.getElementById('episode-id').textContent = `Episode: ${episode.id}`;
        document.getElementById('agent-id').textContent = `Agent: ${episode.agent_id}`;
    }
    
    /**
     * Update prompt sections
     * @param {Object} sections - Prompt sections
     */
    updatePromptSections(sections) {
        if (!sections) return;
        
        const primaryInstructions = document.getElementById('primary-instructions-content');
        const schema = document.getElementById('schema-content');
        const activeActions = document.getElementById('active-actions-content');
        const recentEpisodes = document.getElementById('recent-episodes-content');
        const errors = document.getElementById('errors-content');
        
        if (primaryInstructions) primaryInstructions.textContent = sections.primary_instructions || '';
        if (schema) schema.textContent = sections.schema || '';
        if (activeActions) activeActions.textContent = sections.active_actions || '';
        if (recentEpisodes) recentEpisodes.textContent = sections.recent_episodes || '';
        if (errors) errors.textContent = sections.errors || '';
    }
    
    /**
     * Update episode data (reasoning, tasks, results)
     * @param {Object} data - Episode data
     */
    updateEpisodeData(data) {
        if (!data) return;
        
        const reasoning = document.getElementById('reasoning-content');
        const tasks = document.getElementById('tasks-content');
        const results = document.getElementById('results-content');
        
        if (reasoning) {
            reasoning.textContent = data.reasoning || '';
            // Auto-open reasoning section when it's populated
            if (data.reasoning && !this.openSections['reasoning']) {
                const section = reasoning.closest('.collapsible-section');
                if (section) {
                    section.classList.add('open');
                    section.querySelector('.toggle-icon').textContent = '-';
                    this.openSections['reasoning'] = true;
                }
            }
        }
        
        if (tasks) {
            if (data.tasks && data.tasks.length > 0) {
                tasks.textContent = JSON.stringify(data.tasks, null, 2);
                // Auto-open tasks section when it's populated
                if (!this.openSections['tasks']) {
                    const section = tasks.closest('.collapsible-section');
                    if (section) {
                        section.classList.add('open');
                        section.querySelector('.toggle-icon').textContent = '-';
                        this.openSections['tasks'] = true;
                    }
                }
            } else {
                tasks.textContent = '';
            }
        }
        
        if (results) {
            if (data.results && data.results.length > 0) {
                results.textContent = JSON.stringify(data.results, null, 2);
                // Auto-open results section when it's populated
                if (!this.openSections['results']) {
                    const section = results.closest('.collapsible-section');
                    if (section) {
                        section.classList.add('open');
                        section.querySelector('.toggle-icon').textContent = '-';
                        this.openSections['results'] = true;
                    }
                }
            } else {
                results.textContent = '';
            }
        }
    }
    
    /**
     * Update workflow button states
     * @param {string} stage - 'initial', 'prompt', 'execute', 'completed'
     */
    updateButtonStates(stage) {
        const nextEpisodeBtn = document.getElementById('next-episode-btn');
        const runPromptBtn = document.getElementById('run-prompt-btn');
        const executeTasksBtn = document.getElementById('execute-tasks-btn');
        const snapshotBtn = document.getElementById('snapshot-btn');
        
        switch (stage) {
            case 'initial':
                // Initial state: Next episode enabled, others disabled
                if (nextEpisodeBtn) nextEpisodeBtn.disabled = false;
                if (runPromptBtn) runPromptBtn.disabled = true;
                if (executeTasksBtn) executeTasksBtn.disabled = true;
                if (snapshotBtn) snapshotBtn.disabled = true;
                break;
            case 'prompt':
                // After creating episode: Run prompt enabled, others disabled
                if (nextEpisodeBtn) nextEpisodeBtn.disabled = true;
                if (runPromptBtn) runPromptBtn.disabled = false;
                if (executeTasksBtn) executeTasksBtn.disabled = true;
                if (snapshotBtn) snapshotBtn.disabled = true;
                break;
            case 'execute':
                // After running prompt: Execute tasks enabled, others disabled
                if (nextEpisodeBtn) nextEpisodeBtn.disabled = true;
                if (runPromptBtn) runPromptBtn.disabled = true;
                if (executeTasksBtn) executeTasksBtn.disabled = false;
                if (snapshotBtn) snapshotBtn.disabled = true;
                break;
            case 'completed':
                // After executing tasks: Next episode and save snapshot enabled, others disabled
                if (nextEpisodeBtn) nextEpisodeBtn.disabled = false;
                if (runPromptBtn) runPromptBtn.disabled = true;
                if (executeTasksBtn) executeTasksBtn.disabled = true;
                if (snapshotBtn) snapshotBtn.disabled = false;
                break;
        }
    }
}

// Export singleton UI instance
const ui = new MementoUI();
