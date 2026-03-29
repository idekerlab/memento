import json
import logging
from typing import Dict, Any, Optional

class SchemaManager:
    """Manages knowledge graph schema documentation and validation"""
    
    def __init__(self, kg):
        self.kg = kg

    async def get_schema_documentation(self) -> dict:
        """Get full schema documentation from vocabulary definitions
        
        Returns:
            Dict containing types, relationships, properties and example queries
        """
        try:
            schema = {
                'types': {},
                'relationships': {},
                'properties': {},
                'query_examples': {}
            }

            # Get type definitions with their valid properties
            type_query = """
                SELECT t.value,
                       t_desc.value as description,
                       array_agg(DISTINCT CASE WHEN ap.key = 'allowed_properties' THEN ap.value ELSE NULL END) as allowed_properties
                FROM entities e 
                JOIN properties t ON e.id = t.entity_id AND t.key = 'defines_type'
                LEFT JOIN properties t_desc ON e.id = t_desc.entity_id AND t_desc.key = 'description'
                LEFT JOIN properties ap ON e.id = ap.entity_id
                WHERE e.type = 'TypeDefinition'
                GROUP BY t.value, t_desc.value
            """
            types_result = await self.kg.query_database(type_query)
            
            for row in types_result['results']:
                schema['types'][row['value']] = {
                    'description': row.get('description', None),
                    'allowed_properties': json.loads(row.get('allowed_properties', '[]'))
                }

            # Get relationship definitions with constraints
            rel_query = """
                SELECT r.value as relationship_name,
                       r_desc.value as description,
                       source_types.value as valid_sources,
                       target_types.value as valid_targets
                FROM entities e
                JOIN properties r ON e.id = r.entity_id AND r.key = 'defines_relationship'
                LEFT JOIN properties r_desc ON e.id = r_desc.entity_id AND r_desc.key = 'description'
                LEFT JOIN properties source_types ON e.id = source_types.entity_id AND source_types.key = 'valid_source_types'
                LEFT JOIN properties target_types ON e.id = target_types.entity_id AND target_types.key = 'valid_target_types'
                WHERE e.type = 'RelationshipDefinition'
            """
            rels_result = await self.kg.query_database(rel_query)
            
            for row in rels_result['results']:
                schema['relationships'][row['relationship_name']] = {
                    'description': row.get('description', None),
                    'valid_sources': json.loads(row.get('valid_sources', '[]')),
                    'valid_targets': json.loads(row.get('valid_targets', '[]'))
                }

            # Add standard query examples
            schema['query_examples'] = {
                "find_by_type": """
                    SELECT e.* 
                    FROM entities e 
                    WHERE e.type = 'Action'
                """,
                "find_by_property": """
                    SELECT e.* 
                    FROM entities e 
                    JOIN properties p ON e.id = p.entity_id 
                    WHERE e.type = 'Action' 
                    AND p.key = 'status' 
                    AND p.value = 'active'
                """,
                "find_related": """
                    -- Find all Actions that depend on Action with id=123
                    SELECT e2.* 
                    FROM entities e1
                    JOIN relationships r ON e1.id = r.source_id
                    JOIN entities e2 ON r.target_id = e2.id
                    WHERE e1.id = 123 
                    AND r.type = 'depends_on'
                    AND e2.type = 'Action'
                """
            }

            return schema

        except Exception as e:
            print(f"Error getting schema documentation: {str(e)}")
            raise

    async def validate_type(self, type_name: str) -> bool:
        """Validate if a type exists in the schema"""
        schema = await self.get_schema_documentation()
        return type_name in schema['types']

    async def validate_properties(self, type_name: str, properties: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate properties against type definition
        
        Args:
            type_name: Entity type to validate against
            properties: Properties to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            schema = await self.get_schema_documentation()
            if type_name not in schema['types']:
                return False, f"Unknown type: {type_name}"
                
            allowed = set(schema['types'][type_name]['allowed_properties'])
            provided = set(properties.keys())
            
            invalid = provided - allowed
            if invalid:
                return False, f"Invalid properties for type {type_name}: {invalid}"
                
            return True, None
            
        except Exception as e:
            print(f"Error validating properties: {str(e)}")
            return False, str(e)
