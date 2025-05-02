from app.agent import Memento
from app.knowledge_graph import KnowledgeGraph
from app.mcp_client import MCPClient
import asyncio
import json
from typing import Optional, Dict, Any

class StepRunner:
    """
    Provides step-by-step control over Memento agent execution.
    """
    def __init__(self):
        self.kg_client: Optional[MCPClient] = None
        self.knowledge_graph: Optional[KnowledgeGraph] = None
        self.agent: Optional[Memento] = None
        self.current_episode: Optional[Dict[str, Any]] = None

    async def connect(self, server_url: str) -> None:
        """
        Connect to the MCP server and initialize components.
        
        Args:
            server_url: URL of the MCP server to connect to
        """
        try:
            self.kg_client = MCPClient()
            await self.kg_client.connect_to_server(server_url)
            
            # Initialize knowledge graph
            self.knowledge_graph = KnowledgeGraph(self.kg_client)
            await self.knowledge_graph.ensure_initialized()
            
            # Initialize agent
            self.agent = await Memento.create(self.knowledge_graph)
            print("Successfully connected and initialized agent")
            
        except Exception as e:
            print(f"Error connecting to server: {str(e)}")
            raise

    async def start_episode(self) -> Dict[str, Any]:
        """
        Start a new episode but don't execute it yet.
        
        Returns:
            Dict containing episode details
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call connect() first")
            
        try:
            # Create new episode
            self.current_episode = await self.agent.episode_manager.new_episode()
            print(f"Created new episode {self.current_episode['id']}")
            return self.current_episode
            
        except Exception as e:
            print(f"Error starting episode: {str(e)}")
            raise

    async def get_episode_plan(self) -> Dict[str, Any]:
        """
        Get the LLM's planned tasks for the current episode without executing them.
        
        Returns:
            Dict containing reasoning and planned tasks
        """
        if not self.current_episode:
            raise RuntimeError("No active episode. Call start_episode() first")
            
        try:
            # Get prompt and query LLM
            prompt = await self.agent.query_manager.assemble_prompt()
            query_status = await self.agent.query_manager.query_llm(
                context="You are a Memento agent - an ethical and helpful autonomous system designed to pursue goals set by a user.",
                prompt=prompt,
                episode_id=self.current_episode['id']
            )
            
            # Get the planning results
            query = f"""
                SELECT key, value 
                FROM properties 
                WHERE entity_id = {self.current_episode['id']}
                AND key IN ('reasoning', 'tasks')
            """
            response = await self.knowledge_graph.query_database(query)
            
            plan = {}
            for row in response['results']:
                if row['key'] == 'tasks':
                    plan['tasks'] = json.loads(row['value'])
                else:
                    plan[row['key']] = row['value']
                    
            return plan
            
        except Exception as e:
            print(f"Error getting episode plan: {str(e)}")
            raise

    async def execute_plan(self) -> Dict[str, str]:
        """
        Execute the planned tasks for the current episode.
        
        Returns:
            Dict containing execution status
        """
        if not self.current_episode:
            raise RuntimeError("No active episode. Call start_episode() first")
            
        try:
            # Execute tasks
            task_status = await self.agent.task_manager.execute_tasks(self.current_episode['id'])
            print(f"Tasks executed: {task_status.get("status")}")
            return task_status
            
        except Exception as e:
            print(f"Error executing tasks: {str(e)}")
            raise

    async def complete_episode(self) -> Dict[str, str]:
        """
        Complete the current episode and prepare for the next one.
        
        Returns:
            Dict containing completion status
        """
        if not self.current_episode:
            raise RuntimeError("No active episode. Call start_episode() first")
            
        try:
            # Close the episode
            status = await self.agent.episode_manager.close_episode(self.current_episode['id'])
            self.current_episode = None
            return status
            
        except Exception as e:
            print(f"Error completing episode: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Clean up connections and resources"""
        if self.kg_client:
            await self.kg_client.cleanup()
            self.kg_client = None
            self.knowledge_graph = None
            self.agent = None
            self.current_episode = None

async def main():
    """Example usage of StepRunner"""
    runner = StepRunner()
    try:
        # Connect to server
        server_url = "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py"
        await runner.connect(server_url)
        
        while True:  # Main episode loop
            # Start new episode
            episode = await runner.start_episode()
            print(f"Started episode {episode['id']}")
            
            # Get planned tasks
            plan = await runner.get_episode_plan()
            print("\nPlanned tasks:")
            print(json.dumps(plan, indent=2))
            
            # Execute if user confirms
            user_input = input("\nExecute these tasks? (y/n): ")
            if user_input.lower() == 'y':
                status = await runner.execute_plan()
                print(f"\nExecution status: {status}")
                
                # Complete episode
                completion = await runner.complete_episode()
                print(f"\nEpisode completion status: {completion}")
            elif user_input.lower() == 'n':
                print("\nSkipping task execution.")
                await runner.complete_episode()
            
            # Check if user wants to continue with another episode
            continue_input = input("\nRun next episode? (y/n): ")
            if continue_input.lower() != 'y':
                print("\nExiting Memento agent.")
                break
            
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
