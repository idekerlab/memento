# test_planning_step.py
import asyncio
import json
import pytest
from app.step import StepRunner

@pytest.mark.asyncio
async def test_planning():
    runner = StepRunner()
    try:
        # Connect to server
        server_url = "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py"
        await runner.connect(server_url) 
        
        # Test database connection with simple query
        print("\nTesting database connection...")
        test_query = "SELECT COUNT(*) as count FROM entities"
        try:
            result = await runner.knowledge_graph.query_database(test_query)
            print(f"Database test successful: found {result['results'][0]['count']} entities")
        except Exception as e:
            print(f"Database test failed: {str(e)}")
            raise

        # Clean up previous test artifacts
        print("\nCleaning up previous test artifacts...")
        cleanup_query = """
            SELECT e.id 
            FROM entities e
            WHERE e.type = 'Action' 
            AND (e.name = 'Create RAS Pathway Analysis Plan'
                 OR e.name LIKE '%RAS%'
                 OR e.name LIKE '%prerequisite%')
        """
        print(f"Executing cleanup query:\n{cleanup_query}")
        try:
            result = await runner.knowledge_graph.query_database(cleanup_query)
            if 'results' not in result:
                print(f"Warning: No results key in query response: {result}")
                print("Skipping cleanup...")
                return "Skipped: Cleanup action failed"
                
            print(f"Found {len(result['results'])} actions to clean up")
            # Delete found actions and their relationships
            for row in result.get('results', []):
                # First delete relationships
                rels_query = f"""
                    SELECT id FROM relationships 
                    WHERE source_id = {row['id']} 
                    OR target_id = {row['id']}
                """
                rels = await runner.knowledge_graph.query_database(rels_query)
                for rel in rels['results']:
                    await runner.knowledge_graph.delete_relationship(rel['id'])
                    
                # Then delete the action
                await runner.knowledge_graph.delete_entity(row['id'])
                print(f"Deleted action {row['id']} and its relationships")
        except Exception as e:
            print(f"Cleanup query failed: {str(e)}")
            raise
        
        # Create new initial action
        action = await runner.knowledge_graph.add_entity(
            type="Action",
            name="Create RAS Pathway Analysis Plan",
            properties={
                "description": "Create a detailed plan for analyzing the RAS pathway in cancer genomics papers, broken down into concrete analytical steps",
                "completion_criteria": "Plan is created with a complete set of inactive Actions representing analysis steps with proper dependencies",
                "active": "TRUE",
                "state": "unsatisfied"
            }
        )
        print(f"\nCreated new action: {action['id']}")
        
        # Run episode
        episode = await runner.start_episode()
        print(f"Started episode {episode['id']}")
        
        plan = await runner.get_episode_plan()
        print("\nPlanned tasks:")
        print(json.dumps(plan, indent=2))
        
        status = await runner.execute_plan()
        print(f"\nExecution status: {status}")
        
        completion = await runner.complete_episode()
        print(f"\nEpisode completion status: {completion}")
        
        # Verify results
        query = f"""
            WITH RECURSIVE action_tree AS (
                -- Base case: start with our initial action
                SELECT a.id, a.name, p.value as state, 0 as level
                FROM entities a
                JOIN properties p ON a.id = p.entity_id
                WHERE a.id = {action['id']}
                AND p.key = 'state'

                UNION ALL

                -- Recursive case: find dependent actions
                SELECT e.id, e.name, p.value as state, at.level + 1
                FROM action_tree at
                JOIN relationships r ON r.source_id = e.id
                JOIN entities e ON e.id = r.target_id
                JOIN properties p ON e.id = p.entity_id
                WHERE r.type = 'depends_on'
                AND p.key = 'state'
            )
            SELECT id, name, state, level 
            FROM action_tree
            ORDER BY level, id;
        """
        
        result = await runner.knowledge_graph.query_database(query)
        print("\nResulting action hierarchy:")
        for row in result['results']:
            indent = "  " * row['level']
            print(f"{indent}{row['name']} ({row['state']})")
            
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(test_planning())
