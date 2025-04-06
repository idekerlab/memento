#!/usr/bin/env python3
"""
Script to initialize the Memento knowledge graph with templates and initial action
for testing the task chaining functionality.

This script:
1. Creates template entities for hypothesis generation, review, and improvement
2. Creates an initial Action with experimental data
3. Saves a snapshot to NDEx
"""

import sys
import os
import asyncio
import json
import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.step import StepRunner
from app.config import load_ndex_credentials

async def initialize_kg():
    # Initialize step runner and connect to KG
    runner = StepRunner()
    kg_server_url = "/Users/idekeradmin/Dropbox/GitHub/agent_kg/kg_access.py"
    print(f"Connecting to KG server at {kg_server_url}...")
    await runner.connect(kg_server_url)
    print("Connected to KG server")
    
    # Get a reference to the knowledge graph
    kg = runner.knowledge_graph
    
    # First check if the KG has existing data
    query = "SELECT COUNT(*) as count FROM entities"
    response = await kg.query_database(query)
    
    if response.get('results') and len(response.get('results')) > 0:
        count = response['results'][0].get('count', 0)
        if count > 0:
            # Ask for confirmation before clearing
            confirm = input(f"The KG contains {count} entities. Do you want to clear it? (y/n): ")
            if confirm.lower() == 'y':
                print("Clearing knowledge graph...")
                await kg.clear_database()
                print("Knowledge graph cleared")
            else:
                print("Keeping existing data")
    
    # Create template entities
    print("Creating template entities...")
    
    # 1. Hypothesis Generation Template
    hypothesis_template = await kg.add_entity(
        type="Template",
        name="HypothesisGenerationTemplate",
        properties={
            "description": "Template for generating a hypothesis based on experimental data",
            "template": """
You are a scientific hypothesis generator. Your task is to generate a detailed hypothesis based on the following experimental data:

EXPERIMENTAL DATA:
{data}

Please generate a detailed hypothesis that explains the observed gene expression changes. Your hypothesis should:
1. Propose a specific mechanism that explains the gene expression changes
2. Connect the observed changes to potential biological functions
3. Suggest potential pathways that might be involved
4. Be specific, clear, and testable
5. Suggest at least one prediction that could be tested in future experiments

Format your response as a clear, detailed scientific hypothesis. Be specific and provide the reasoning behind your hypothesis.
""",
            "context": "You are a scientific hypothesis generator specialized in molecular biology and genetics."
        }
    )
    print(f"Created Hypothesis Generation Template with ID: {hypothesis_template['id']}")
    
    # 2. Hypothesis Review Template
    review_template = await kg.add_entity(
        type="Template",
        name="HypothesisReviewTemplate",
        properties={
            "description": "Template for reviewing a scientific hypothesis",
            "template": """
You are a scientific peer reviewer. Your task is to critically review the following hypothesis:

HYPOTHESIS:
{hypothesis}

Please provide a detailed, critical review of this hypothesis. Your review should:
1. Evaluate the strengths and weaknesses of the hypothesis
2. Assess whether the hypothesis adequately explains all the experimental data
3. Identify any logical flaws or gaps in reasoning
4. Suggest additional factors or mechanisms that may have been overlooked
5. Recommend specific improvements to make the hypothesis more comprehensive and testable

Format your response as a constructive scientific review with clear, specific feedback points.
""",
            "context": "You are a scientific peer reviewer with expertise in molecular biology, genetics, and cellular signaling pathways."
        }
    )
    print(f"Created Hypothesis Review Template with ID: {review_template['id']}")
    
    # 3. Hypothesis Improvement Template
    improvement_template = await kg.add_entity(
        type="Template",
        name="HypothesisImprovementTemplate",
        properties={
            "description": "Template for improving a hypothesis based on review feedback",
            "template": """
You are a scientific researcher. Your task is to improve the following hypothesis based on the review feedback:

ORIGINAL HYPOTHESIS:
{hypothesis}

REVIEW FEEDBACK:
{review}

Please provide an improved, refined hypothesis that addresses the feedback. Your improved hypothesis should:
1. Maintain the core strengths of the original hypothesis
2. Address the weaknesses and gaps identified in the review
3. Incorporate any suggested additional factors or mechanisms
4. Be more comprehensive, specific, and testable
5. Clearly indicate what has changed from the original hypothesis

Format your response as a clear, detailed scientific hypothesis with an introductory paragraph explaining how your revised hypothesis addresses the review feedback.
""",
            "context": "You are a scientific researcher with expertise in molecular biology, genetics, and cellular signaling pathways."
        }
    )
    print(f"Created Hypothesis Improvement Template with ID: {improvement_template['id']}")
    
    # Create initial Action with experimental data
    print("Creating initial action with experimental data...")
    
    initial_action = await kg.add_entity(
        type="Action",
        name="Generate_Review_Improve_Hypothesis",
        properties={
            "description": "Alveolar macrophages infected with the dengue virus were observed to have the following gene expression changes: upregulated genes: BRAP, RGL1 downregulated genes: RASSF7, HRAS, and RASAL1",
            "completion_criteria": "A scientific hypothesis is generated, reviewed, and improved based on feedback",
            "active": True,
            "state": "unsatisfied",
            "creation_time": datetime.datetime.now().isoformat()
        }
    )
    print(f"Created Initial Action with ID: {initial_action['id']}")
    
    # Save a snapshot to NDEx
    print("Saving snapshot to NDEx...")
    
    try:
        ndex_username, ndex_password = load_ndex_credentials()
        if not ndex_username or not ndex_password:
            print("NDEx credentials not configured. Skipping snapshot.")
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            network_name = f"Memento_TaskChaining_Test_{timestamp}"
            network_description = "Memento Knowledge Graph for Task Chaining Test"
            
            uuid = await kg.save_to_ndex(name=network_name, description=network_description)
            print(f"Snapshot saved to NDEx with UUID: {uuid}")
            print(f"Network name: {network_name}")
    except Exception as e:
        print(f"Error saving to NDEx: {str(e)}")
    
    # Summary of created entities
    print("\nSUMMARY:")
    print(f"Hypothesis Generation Template ID: {hypothesis_template['id']}")
    print(f"Hypothesis Review Template ID: {review_template['id']}")
    print(f"Hypothesis Improvement Template ID: {improvement_template['id']}")
    print(f"Initial Action ID: {initial_action['id']}")
    print("\nYou can now use these IDs in your task definitions.")
    print("Example task chain:")
    print(f"""
1. Generate hypothesis using template {hypothesis_template['id']} with the action data
2. Review the hypothesis using template {review_template['id']}
3. Improve the hypothesis using template {improvement_template['id']} with the original hypothesis and review
""")

    # Close connection to KG
    await runner.cleanup()
    print("Connection to KG server closed")
    
    # Provide example task definitions
    print("\nExample task definitions for the web UI:")
    print("""
{
  "reasoning": "We will test the task chaining functionality by creating a multi-stage workflow where the output of one task is used as input for subsequent tasks. The workflow will involve generating a scientific hypothesis based on gene expression data, reviewing the hypothesis, and then improving it based on the review feedback.",
  "tasks": [
    {
      "type": "query_llm_using_template",
      "output_var": "hypothesis_result",
      "requires": [],
      "template_id": """ + str(hypothesis_template['id']) + """,
      "arguments": {
        "data": "Alveolar macrophages infected with the dengue virus were observed to have the following gene expression changes: upregulated genes: BRAP, RGL1 downregulated genes: RASSF7, HRAS, and RASAL1"
      },
      "description": "Generate an initial scientific hypothesis based on the experimental data"
    },
    {
      "type": "query_llm_using_template",
      "output_var": "review_result",
      "requires": ["hypothesis_result"],
      "template_id": """ + str(review_template['id']) + """,
      "arguments": {
        "hypothesis": "${hypothesis_result.content}"
      },
      "description": "Review the generated hypothesis to identify strengths, weaknesses, and areas for improvement"
    },
    {
      "type": "query_llm_using_template",
      "output_var": "improved_hypothesis",
      "requires": ["hypothesis_result", "review_result"],
      "template_id": """ + str(improvement_template['id']) + """,
      "arguments": {
        "hypothesis": "${hypothesis_result.content}",
        "review": "${review_result.content}"
      },
      "description": "Generate an improved hypothesis based on the original hypothesis and review feedback"
    },
    {
      "type": "create_action",
      "output_var": "document_action",
      "requires": ["hypothesis_result", "review_result", "improved_hypothesis"],
      "name": "Document Hypothesis Development Process",
      "description": "Document the complete hypothesis development process including the initial hypothesis, review feedback, and the final improved hypothesis",
      "completion_criteria": "Complete documentation of the hypothesis development process",
      "active": "TRUE",
      "state": "unsatisfied"
    }
  ]
}
""")

if __name__ == "__main__":
    asyncio.run(initialize_kg())
