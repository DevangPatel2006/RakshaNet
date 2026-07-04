from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db import models
from app.services.graph_service import get_graph_service

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("/entity/{value}", status_code=status.HTTP_200_OK)
def get_entity_graph(value: str, db: Session = Depends(get_db)):
    # Look up in Postgres first
    entity = db.query(models.Entity).filter(models.Entity.value == value).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found"
        )
    
    # Query its surroundings in Neo4j
    graph_service = get_graph_service()
    all_data = graph_service.get_all_entities_and_links()
    
    # Filter nodes and links connected to this entity's value_hash
    import hashlib
    vh = hashlib.sha256(value.encode()).hexdigest()
    
    connected_hashes = {vh}
    for link in all_data["links"]:
        if link["source"] == vh:
            connected_hashes.add(link["target"])
        elif link["target"] == vh:
            connected_hashes.add(link["source"])
            
    filtered_nodes = [n for n in all_data["nodes"] if n["value_hash"] in connected_hashes]
    filtered_links = [l for l in all_data["links"] if l["source"] in connected_hashes or l["target"] in connected_hashes]
    
    # Add cluster mappings
    cluster_mappings = graph_service.get_cluster_mappings()
    for n in filtered_nodes:
        n["cluster_id"] = cluster_mappings.get(n["value_hash"], -1)
        
    return {
        "entity": {
            "id": entity.id,
            "type": entity.type,
            "value": entity.value,
            "value_hash": entity.value_hash,
            "risk_score": entity.risk_score
        },
        "network": {
            "nodes": filtered_nodes,
            "links": filtered_links
        }
    }

@router.get("/cluster", status_code=status.HTTP_200_OK)
def get_clusters_graph():
    graph_service = get_graph_service()
    all_data = graph_service.get_all_entities_and_links()
    cluster_mappings = graph_service.get_cluster_mappings()
    
    # Enrich nodes with cluster IDs
    for node in all_data["nodes"]:
        node["cluster_id"] = cluster_mappings.get(node["value_hash"], -1)
        
    return all_data
