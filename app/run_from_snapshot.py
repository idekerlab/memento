# run_from_snapshot.py
import asyncio
from step import StepRunner
import sys
import json
from knowledge_graph import KnowledgeGraph
from mcp_client import MCPClient
import datetime

async def run_from_snapshot(uuid: str="12ae998d-f788-11ef-b81d-005056ae3c32"):
    """Load a snapshot and run StepRunner"""
    runner = None
    try:
        print(f"Initializing from snapshot {uuid}")
        runner = StepRunner()
        
        # Connect and initialize
        server_url = "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py"
        await runner.connect(server_url)
        
        # Load the snapshot
        print("Loading snapshot from NDEx...")
        await runner.knowledge_graph.load_from_ndex(uuid)
        print("Snapshot loaded successfully")
        
        while True:  # Main episode loop
            # Start new episode
            episode = await runner.start_episode()
            print(f"\nStarted episode {episode['id']}")
            
            # Get planned tasks
            plan = await runner.get_episode_plan()
            print("\nPlanned tasks:")
            print(json.dumps(plan, indent=2))
            
            # Get user input
            user_input = input("\nExecute these tasks? (y/n/q to quit): ").lower()
            if user_input == 'q':
                print("\nExiting Memento agent.")
                break
            elif user_input == 'y':
                status = await runner.execute_plan()
                print(f"\nExecution status: {status}")
                
                # Complete episode
                completion = await runner.complete_episode()
                print(f"\nEpisode completion status: {completion}")
            else:
                print("\nSkipping task execution.")
                await runner.complete_episode()

            # Check if user wants to snapshot the KG
            snapshot_input = input("\nSnapshot the KG to NDEx? (y/n): ").lower()
            if snapshot_input == 'y':
                try:
                    # Create backup with timestamp
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    name = f"Memento_KG_Snapshot_{timestamp}"
                    description = "Snapshot of Memento knowledge graph state"
                    
                    print(f"Creating backup: {name}")
                    uuid = await runner.knowledge_graph.save_to_ndex(name=name, description=description)
                    print(f"Backup complete. NDEx UUID: {uuid}")
        
                except Exception as e:
                    print(f"Error during snapshot: {str(e)}")
                    raise

            # Check if user wants to continue
            continue_input = input("\nRun next episode? (y/n): ").lower()
            if continue_input != 'y':
                print("\nExiting Memento agent.")
                break
            
    except Exception as e:
        print(f"Error in run_from_snapshot: {str(e)}")
        raise
    finally:
        if runner:
            await runner.cleanup()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        # print("Usage: python run_from_snapshot.py <ndex_uuid>")
        asyncio.run(run_from_snapshot())
        #sys.exit(1)
    else:
        uuid = sys.argv[1]
        asyncio.run(run_from_snapshot(uuid))