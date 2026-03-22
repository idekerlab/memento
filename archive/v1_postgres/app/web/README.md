# Memento Web Interface

A web application interface for the Memento agent system, providing functionality similar to `run_from_snapshot.py` with a user-friendly UI.

## Features

- Initialize from an existing knowledge graph on NDEx or with an empty KG
- Step-by-step control over the Memento agent execution
- Visual representation of episodes, reasoning, tasks, and results
- Save snapshots to NDEx for future use

## Structure

### Backend
- FastAPI server that provides a REST API for the frontend
- Wraps the functionality of the StepRunner class
- Handles knowledge graph operations, episode management, etc.

### Frontend
- Single-page HTML/CSS/JavaScript application
- Two main views:
  - Initialization view: Select a KG from NDEx or start with an empty KG
  - Operation view: Control episode execution and view results

## Running the Application

1. Make sure all Memento dependencies are installed:
   ```
   pip install -r requirements.txt
   ```

2. Start the web server:
   ```
   python -m app.web.main
   ```

3. Open a web browser and navigate to:
   ```
   http://localhost:8000
   ```

## Workflow

1. **Initialization**:
   - Select an existing knowledge graph from NDEx, or
   - Create an empty knowledge graph with an initial action

2. **Operation**:
   - Click "Next Episode" to start a new episode
   - Click "Run Prompt" to generate reasoning and tasks
   - Click "Execute Tasks" to execute the planned tasks
   - Click "Save Snapshot" to save the current state to NDEx

## API Endpoints

- `/api/status` - Get server status
- `/api/init/ndex` - Initialize from NDEx network
- `/api/init/empty` - Initialize with empty KG
- `/api/ndex/networks` - List available NDEx networks
- `/api/episode/current` - Get current episode
- `/api/episode/next` - Create next episode
- `/api/episode/prompt` - Run prompt for current episode
- `/api/episode/execute` - Execute tasks for current episode
- `/api/snapshot/save` - Save KG snapshot to NDEx
