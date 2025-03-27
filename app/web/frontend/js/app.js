/**
 * Main application logic for the Memento Web Interface
 */
class MementoApp {
    constructor() {
        this.initialized = false;
        this.currentStage = 'initial'; // 'initial', 'prompt', 'execute', 'completed'
    }
    
    /**
     * Initialize the application
     */
    async init() {
        // Initialize UI
        ui.init();
        
        // Setup event listeners
        this._setupEventListeners();
        
        // Fetch available networks if we're starting in init view
        if (ui.currentView === 'init') {
            await this._loadNetworks();
        }
        
        // Check server status
        try {
            const status = await api.getStatus();
            
            // If already initialized, switch to operation view
            if (status.initialized) {
                this.initialized = true;
                ui.switchView('operation');
                await this._refreshCurrentEpisode();
            }
        } catch (error) {
            ui.showStatus('Error connecting to server: ' + error.message, 'error');
        }
    }
    
    /**
     * Setup event listeners for UI interactions
     */
    _setupEventListeners() {
        // Initialization events
        document.addEventListener('initialize-ndex', async (event) => {
            await this._initializeFromNDEx(event.detail.uuid);
        });
        
        document.addEventListener('initialize-empty', async (event) => {
            await this._initializeEmpty(event.detail.initialAction);
        });
        
        // Operation events
        document.addEventListener('next-episode', async () => {
            await this._startNextEpisode();
        });
        
        document.addEventListener('run-prompt', async () => {
            await this._runPrompt();
        });
        
        document.addEventListener('execute-tasks', async () => {
            await this._executeTasks();
        });
        
        document.addEventListener('save-snapshot', async () => {
            await this._saveSnapshot();
        });
    }
    
    /**
     * Load available networks from NDEx
     */
    async _loadNetworks() {
        try {
            const statusMessage = ui.showStatus('Loading networks from NDEx...', 'info', 0);
            const response = await api.getNDExNetworks();
            statusMessage.close();
            
            if (response.success && response.networks) {
                ui.renderNetworks(response.networks);
            } else {
                ui.showStatus('Failed to load networks', 'error');
            }
        } catch (error) {
            ui.showStatus('Error loading networks: ' + error.message, 'error');
        }
    }
    
    /**
     * Initialize from an NDEx network
     * @param {string} uuid - NDEx network UUID
     */
    async _initializeFromNDEx(uuid) {
        try {
            const statusMessage = ui.showStatus('Initializing from NDEx network...', 'info', 0);
            const response = await api.initializeFromNDEx(uuid);
            statusMessage.close();
            
            if (response.success) {
                ui.showStatus('Successfully initialized from NDEx', 'success');
                this.initialized = true;
                
                // Switch to operation view
                ui.switchView('operation');
                
                // Refresh current episode info
                await this._refreshCurrentEpisode();
            } else {
                ui.showStatus('Failed to initialize from NDEx: ' + response.error, 'error');
            }
        } catch (error) {
            ui.showStatus('Error initializing from NDEx: ' + error.message, 'error');
        }
    }
    
    /**
     * Initialize with empty KG and initial action
     * @param {string} initialAction - Description of the initial action
     */
    async _initializeEmpty(initialAction) {
        try {
            const statusMessage = ui.showStatus('Initializing with empty KG...', 'info', 0);
            const response = await api.initializeEmpty(initialAction);
            statusMessage.close();
            
            if (response.success) {
                ui.showStatus('Successfully initialized with empty KG', 'success');
                this.initialized = true;
                
                // Switch to operation view
                ui.switchView('operation');
                
                // Refresh current episode info
                await this._refreshCurrentEpisode();
            } else {
                ui.showStatus('Failed to initialize with empty KG: ' + response.error, 'error');
            }
        } catch (error) {
            ui.showStatus('Error initializing with empty KG: ' + error.message, 'error');
        }
    }
    
    /**
     * Refresh current episode information
     */
    async _refreshCurrentEpisode() {
        try {
            const response = await api.getCurrentEpisode();
            
            if (response.success) {
                // Update UI with episode information
                if (response.episode) {
                    ui.updateEpisodeInfo(response.episode);
                    ui.updatePromptSections(response.episode.prompt);
                    ui.updateEpisodeData(response.episode.data);
                } else {
                    ui.updateEpisodeInfo(null);
                    ui.updatePromptSections(null);
                    ui.updateEpisodeData(null);
                }
                
                // Set button states based on current stage
                ui.updateButtonStates(this.currentStage);
            } else {
                ui.showStatus('Failed to get episode information: ' + response.error, 'error');
            }
        } catch (error) {
            ui.showStatus('Error getting episode information: ' + error.message, 'error');
        }
    }
    
    /**
     * Start the next episode
     */
    async _startNextEpisode() {
        try {
            const statusMessage = ui.showStatus('Creating next episode...', 'info', 0);
            const response = await api.startNextEpisode();
            statusMessage.close();
            
            if (response.success) {
                ui.showStatus('Next episode created', 'success');
                
                // Update UI with new episode information
                ui.updateEpisodeInfo(response.episode);
                
                // Transition to prompt stage
                this.currentStage = 'prompt';
                ui.updateButtonStates(this.currentStage);
                
                // Refresh current episode to get prompt sections
                await this._refreshCurrentEpisode();
            } else {
                ui.showStatus('Failed to create next episode: ' + response.error, 'error');
            }
        } catch (error) {
            ui.showStatus('Error creating next episode: ' + error.message, 'error');
        }
    }
    
    /**
     * Run the prompt for the current episode
     */
    async _runPrompt() {
        try {
            const statusMessage = ui.showStatus('Running prompt...', 'info', 0);
            const response = await api.runPrompt();
            statusMessage.close();
            
            if (response.success) {
                ui.showStatus('Prompt completed', 'success');
                
                // Update episode data with reasoning and tasks
                ui.updateEpisodeData(response.episode.data);
                
                // Transition to execute stage
                this.currentStage = 'execute';
                ui.updateButtonStates(this.currentStage);
            } else {
                ui.showStatus('Failed to run prompt: ' + response.error, 'error');
            }
        } catch (error) {
            ui.showStatus('Error running prompt: ' + error.message, 'error');
        }
    }
    
    /**
     * Execute the tasks for the current episode
     */
    async _executeTasks() {
        try {
            const statusMessage = ui.showStatus('Executing tasks...', 'info', 0);
            const response = await api.executeTasks();
            statusMessage.close();
            
            if (response.success) {
                ui.showStatus('Tasks executed', 'success');
                
                // Update episode data with results
                ui.updateEpisodeData(response.episode.data);
                
                // Transition to completed stage
                this.currentStage = 'completed';
                ui.updateButtonStates(this.currentStage);
            } else {
                ui.showStatus('Failed to execute tasks: ' + response.error, 'error');
            }
        } catch (error) {
            ui.showStatus('Error executing tasks: ' + error.message, 'error');
        }
    }
    
    /**
     * Save a snapshot of the KG to NDEx
     */
    async _saveSnapshot() {
        try {
            const statusMessage = ui.showStatus('Saving snapshot to NDEx...', 'info', 0);
            const response = await api.saveSnapshot();
            statusMessage.close();
            
            if (response.success) {
                ui.showStatus(`Snapshot saved to NDEx: ${response.snapshot.name}`, 'success');
            } else {
                ui.showStatus('Failed to save snapshot: ' + response.error, 'error');
            }
        } catch (error) {
            ui.showStatus('Error saving snapshot: ' + error.message, 'error');
        }
    }
}

// Initialize the application when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new MementoApp();
    app.init().catch(error => {
        console.error('Error initializing application:', error);
        ui.showStatus('Failed to initialize application: ' + error.message, 'error');
    });
});
