"""
NDEx operations for Memento Access server.
Handles saving and loading knowledge graph state to/from NDEx.
"""

import logging
import datetime
from typing import Dict, Optional

from app.config import load_ndex_credentials
from app.memento_access.initialization import MementoComponents

logger = logging.getLogger("memento_access.ndex")

class NDExTools:
    """Handles NDEx-related operations"""
    
    def __init__(self, components: MementoComponents):
        self.components = components
    
    async def save_to_ndex(self, name: Optional[str] = None, description: Optional[str] = None) -> Dict:
        """Save the current knowledge graph to NDEx"""
        logger.info("Saving knowledge graph to NDEx")
        
        # Check for NDEx credentials
        username, password = load_ndex_credentials()
        if not username or not password:
            logger.warning("NDEx credentials not found")
            return {
                "success": False,
                "error": "NDEx credentials not found. Please configure NDEX_USERNAME and NDEX_PASSWORD in your config file."
            }
        
        # Generate default name and description if not provided
        if not name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"Memento_KG_Snapshot_{timestamp}"
        
        if not description:
            description = f"Snapshot of Memento knowledge graph state created on {datetime.datetime.now().isoformat()}"
        
        try:
            logger.info(f"Saving knowledge graph to NDEx with name: {name}")
            # Save to NDEx
            uuid = await self.components.knowledge_graph.save_to_ndex(name=name, description=description)
            logger.info(f"Knowledge graph saved to NDEx with UUID: {uuid}")
            
            return {
                "success": True,
                "uuid": uuid,
                "name": name,
                "description": description
            }
        except Exception as e:
            logger.error(f"Error saving to NDEx: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to save to NDEx: {str(e)}"
            }
    
    async def load_from_ndex(self, uuid: str) -> Dict:
        """Load a knowledge graph from NDEx"""
        logger.info(f"Loading knowledge graph from NDEx with UUID: {uuid}")
        
        # Check for NDEx credentials
        username, password = load_ndex_credentials()
        if not username or not password:
            logger.warning("NDEx credentials not found")
            return {
                "success": False,
                "error": "NDEx credentials not found. Please configure NDEX_USERNAME and NDEX_PASSWORD in your config file."
            }
        
        try:
            await self.components.knowledge_graph.load_from_ndex(uuid)
            logger.info(f"Successfully loaded knowledge graph from NDEx")
            
            return {
                "success": True,
                "message": f"Successfully loaded knowledge graph from NDEx network {uuid}"
            }
        except Exception as e:
            logger.error(f"Error loading from NDEx: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to load from NDEx: {str(e)}"
            }
