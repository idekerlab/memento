/**
 * API client for the Memento Web Interface
 */
class MementoAPI {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
    }

    /**
     * Make an API request
     * @param {string} url - Endpoint URL
     * @param {Object} options - Fetch options
     * @returns {Promise} - Promise with the response data
     */
    async _request(url, options = {}) {
        try {
            const response = await fetch(`${this.baseURL}${url}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            const data = await response.json();
            
            if (!response.ok) {
                const error = new Error(data.detail || 'API request failed');
                error.status = response.status;
                error.data = data;
                throw error;
            }
            
            return data;
        } catch (error) {
            console.error('API request error:', error);
            throw error;
        }
    }

    /**
     * Get the server status
     * @returns {Promise} - Promise with status data
     */
    async getStatus() {
        return this._request('/api/status');
    }

    /**
     * Initialize the system from an NDEx network
     * @param {string} uuid - NDEx network UUID
     * @returns {Promise} - Promise with initialization result
     */
    async initializeFromNDEx(uuid) {
        return this._request('/api/init/ndex', {
            method: 'POST',
            body: JSON.stringify({ uuid })
        });
    }

    /**
     * Initialize the system with an empty KG and initial action
     * @param {string} initialActionDesc - Description of the initial action
     * @returns {Promise} - Promise with initialization result
     */
    async initializeEmpty(initialActionDesc) {
        return this._request('/api/init/empty', {
            method: 'POST',
            body: JSON.stringify({ initial_action_desc: initialActionDesc })
        });
    }

    /**
     * Get available networks from NDEx account
     * @returns {Promise} - Promise with networks data
     */
    async getNDExNetworks() {
        return this._request('/api/ndex/networks');
    }

    /**
     * Get the current episode information
     * @returns {Promise} - Promise with episode data
     */
    async getCurrentEpisode() {
        return this._request('/api/episode/current');
    }

    /**
     * Create the next episode
     * @returns {Promise} - Promise with new episode data
     */
    async startNextEpisode() {
        return this._request('/api/episode/next', {
            method: 'POST'
        });
    }

    /**
     * Run the prompt for the current episode
     * @returns {Promise} - Promise with updated episode data
     */
    async runPrompt() {
        return this._request('/api/episode/prompt', {
            method: 'POST'
        });
    }

    /**
     * Execute the tasks for the current episode
     * @returns {Promise} - Promise with execution results
     */
    async executeTasks() {
        return this._request('/api/episode/execute', {
            method: 'POST'
        });
    }

    /**
     * Save the current KG to NDEx
     * @returns {Promise} - Promise with snapshot information
     */
    async saveSnapshot() {
        return this._request('/api/snapshot/save', {
            method: 'POST'
        });
    }
}

// Export singleton API instance
const api = new MementoAPI();
