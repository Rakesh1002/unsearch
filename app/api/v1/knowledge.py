"""
Knowledge Graph API - Glean-like Features

Endpoints for:
- Entity extraction and management
- Relationship mapping
- Knowledge search
- People search
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib

from app.config import get_settings
from app.services.ai.cloudflare_ai import CloudflareAIService, CFModel

router = APIRouter(prefix="/knowledge", tags=["Knowledge Graph"])

settings = get_settings()


# Request/Response Models
class Entity(BaseModel):
    id: str
    type: str  # person, company, concept, document, location
    name: str
    description: Optional[str] = None
    source_count: int = 1
    metadata: Dict[str, Any] = {}
    

class Relationship(BaseModel):
    from_entity: str
    to_entity: str
    type: str  # works_at, mentions, related_to, etc.
    weight: float = 1.0
    source: Optional[str] = None


class ExtractEntitiesRequest(BaseModel):
    text: str
    types: Optional[List[str]] = None  # Filter to specific types


class ExtractEntitiesResponse(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]
    processing_time_ms: int


class KnowledgeSearchRequest(BaseModel):
    query: str
    entity_types: Optional[List[str]] = None
    max_results: int = 20
    include_relationships: bool = True


class KnowledgeSearchResponse(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]
    query: str


class PersonSearchRequest(BaseModel):
    query: str
    organization: Optional[str] = None
    role: Optional[str] = None
    max_results: int = 20


class Person(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    expertise: List[str] = []
    recent_activity: List[Dict[str, Any]] = []
    relevance_score: float


class PersonSearchResponse(BaseModel):
    people: List[Person]
    query: str


# In-memory storage (replace with Vectorize/D1 in production)
_entities: Dict[str, Entity] = {}
_relationships: List[Relationship] = []


def get_ai_service() -> CloudflareAIService:
    """Get CloudflareAI service instance."""
    return CloudflareAIService(
        account_id=settings.cloudflare_account_id,
        api_token=settings.cloudflare_api_token
    )


@router.post("/extract", response_model=ExtractEntitiesResponse)
async def extract_entities(request: ExtractEntitiesRequest):
    """
    Extract entities and relationships from text using AI.
    
    This is a Glean-like feature for building knowledge graphs
    from unstructured text.
    """
    start_time = datetime.now()
    
    ai = get_ai_service()
    
    types_filter = ""
    if request.types:
        types_filter = f"Only extract entities of types: {', '.join(request.types)}."
    
    prompt = f"""Extract all entities and relationships from this text.

{types_filter}

Text: {request.text[:4000]}

Return as JSON:
{{
  "entities": [
    {{"type": "person|company|concept|location", "name": "...", "description": "..."}}
  ],
  "relationships": [
    {{"from": "entity name", "to": "entity name", "type": "relationship type"}}
  ]
}}"""
    
    result = await ai.generate_text(
        prompt=prompt,
        model=CFModel.LLAMA_3_1_8B_FAST,
        max_tokens=1500
    )
    
    # Parse result
    import json
    entities = []
    relationships = []
    
    try:
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            data = json.loads(json_match.group())
            
            for e in data.get('entities', []):
                entity_id = hashlib.md5(f"{e['type']}:{e['name']}".encode()).hexdigest()[:12]
                entity = Entity(
                    id=entity_id,
                    type=e.get('type', 'concept'),
                    name=e['name'],
                    description=e.get('description')
                )
                entities.append(entity)
                _entities[entity_id] = entity
            
            for r in data.get('relationships', []):
                relationship = Relationship(
                    from_entity=r['from'],
                    to_entity=r['to'],
                    type=r['type']
                )
                relationships.append(relationship)
                _relationships.append(relationship)
    except Exception as e:
        # Return empty on parse error
        pass
    
    processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return ExtractEntitiesResponse(
        entities=entities,
        relationships=relationships,
        processing_time_ms=processing_time
    )


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(request: KnowledgeSearchRequest):
    """
    Search the knowledge graph for entities and relationships.
    
    Uses semantic search to find relevant entities.
    """
    ai = get_ai_service()
    
    # Generate embedding for query
    query_embedding = await ai.generate_embeddings([request.query])
    
    # In production, this would query Vectorize
    # For now, do simple text matching
    matched_entities = []
    query_lower = request.query.lower()
    
    for entity in _entities.values():
        if request.entity_types and entity.type not in request.entity_types:
            continue
        if query_lower in entity.name.lower() or (entity.description and query_lower in entity.description.lower()):
            matched_entities.append(entity)
    
    matched_entities = matched_entities[:request.max_results]
    
    # Get related relationships
    matched_relationships = []
    if request.include_relationships:
        entity_names = {e.name for e in matched_entities}
        for rel in _relationships:
            if rel.from_entity in entity_names or rel.to_entity in entity_names:
                matched_relationships.append(rel)
    
    return KnowledgeSearchResponse(
        entities=matched_entities,
        relationships=matched_relationships,
        query=request.query
    )


@router.post("/people", response_model=PersonSearchResponse)
async def search_people(request: PersonSearchRequest):
    """
    Search for people across connected data sources.
    
    This is a Glean-like feature for finding experts and colleagues.
    """
    ai = get_ai_service()
    
    # Filter to person entities
    people = []
    query_lower = request.query.lower()
    
    for entity in _entities.values():
        if entity.type != 'person':
            continue
        
        # Simple matching (in production, use vector search)
        if query_lower in entity.name.lower():
            # Find relationships to get org/title
            org = None
            title = None
            
            for rel in _relationships:
                if rel.from_entity == entity.name:
                    if rel.type in ['works_at', 'employed_by']:
                        org = rel.to_entity
                    elif rel.type in ['has_role', 'title']:
                        title = rel.to_entity
            
            # Apply filters
            if request.organization and org != request.organization:
                continue
            
            people.append(Person(
                id=entity.id,
                name=entity.name,
                title=title,
                organization=org,
                expertise=entity.metadata.get('expertise', []),
                relevance_score=1.0
            ))
    
    return PersonSearchResponse(
        people=people[:request.max_results],
        query=request.query
    )


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    """Get a specific entity by ID."""
    if entity_id not in _entities:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    entity = _entities[entity_id]
    
    # Get relationships
    related = []
    for rel in _relationships:
        if rel.from_entity == entity.name or rel.to_entity == entity.name:
            related.append(rel)
    
    return {
        "entity": entity,
        "relationships": related
    }


@router.get("/graph")
async def get_knowledge_graph(
    entity_types: Optional[List[str]] = Query(None),
    limit: int = 100
):
    """
    Get the knowledge graph structure.
    
    Returns entities and relationships for visualization.
    """
    entities = list(_entities.values())
    
    if entity_types:
        entities = [e for e in entities if e.type in entity_types]
    
    entities = entities[:limit]
    entity_names = {e.name for e in entities}
    
    relationships = [
        rel for rel in _relationships
        if rel.from_entity in entity_names and rel.to_entity in entity_names
    ]
    
    return {
        "nodes": [
            {"id": e.id, "name": e.name, "type": e.type}
            for e in entities
        ],
        "edges": [
            {"from": r.from_entity, "to": r.to_entity, "type": r.type, "weight": r.weight}
            for r in relationships
        ]
    }


@router.delete("/entities/{entity_id}")
async def delete_entity(entity_id: str):
    """Delete an entity from the knowledge graph."""
    if entity_id not in _entities:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    entity = _entities.pop(entity_id)
    
    # Remove related relationships
    global _relationships
    _relationships = [
        r for r in _relationships
        if r.from_entity != entity.name and r.to_entity != entity.name
    ]
    
    return {"deleted": True, "entity_id": entity_id}
