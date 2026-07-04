import hashlib
import networkx as nx
from neo4j import GraphDatabase
from app.core.config import settings

class GraphService:
    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.driver = None
        self.connect()

    def connect(self):
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        except Exception as e:
            print(f"Error connecting to Neo4j: {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def clear_graph(self):
        query = "MATCH (n) DETACH DELETE n"
        with self.driver.session() as session:
            session.run(query)

    def add_entity(self, entity_id: int, entity_type: str, value: str, risk_score: float = 0.0):
        # We hash the value for privacy compliance as requested in schema
        value_hash = hashlib.sha256(value.encode()).hexdigest()
        query = (
            "MERGE (e:Entity {value_hash: $value_hash}) "
            "SET e.id = $id, e.type = $type, e.value = $value, e.risk_score = $risk_score "
            "RETURN e"
        )
        with self.driver.session() as session:
            session.run(query, value_hash=value_hash, id=entity_id, type=entity_type, value=value, risk_score=risk_score)
        return value_hash

    def add_link(self, val_a: str, val_b: str, relation_type: str, weight: float = 1.0):
        hash_a = hashlib.sha256(val_a.encode()).hexdigest()
        hash_b = hashlib.sha256(val_b.encode()).hexdigest()
        query = (
            "MERGE (a:Entity {value_hash: $hash_a}) "
            "MERGE (b:Entity {value_hash: $hash_b}) "
            "MERGE (a)-[r:LINKED_TO {relation_type: $relation_type}]->(b) "
            "SET r.weight = $weight "
            "RETURN r"
        )
        with self.driver.session() as session:
            session.run(query, hash_a=hash_a, hash_b=hash_b, relation_type=relation_type, weight=weight)

    def get_all_entities_and_links(self):
        nodes_query = "MATCH (e:Entity) RETURN e.id as id, e.type as type, e.value as value, e.value_hash as value_hash, e.risk_score as risk_score"
        links_query = "MATCH (a:Entity)-[r:LINKED_TO]->(b:Entity) RETURN a.value_hash as source, b.value_hash as target, r.relation_type as relation_type, r.weight as weight"
        
        nodes = []
        links = []
        with self.driver.session() as session:
            nodes_res = session.run(nodes_query)
            for record in nodes_res:
                nodes.append({
                    "id": record["id"],
                    "type": record["type"],
                    "value": record["value"],
                    "value_hash": record["value_hash"],
                    "risk_score": record["risk_score"]
                })
            
            links_res = session.run(links_query)
            for record in links_res:
                links.append({
                    "source": record["source"],
                    "target": record["target"],
                    "relation_type": record["relation_type"],
                    "weight": record["weight"]
                })
        return {"nodes": nodes, "links": links}

    def detect_clusters(self) -> list[set[str]]:
        """
        Retrieves the entire graph structure, populates a NetworkX graph,
        and performs community detection (Label Propagation) locally.
        Returns a list of sets containing entity value_hashes.
        """
        graph_data = self.get_all_entities_and_links()
        
        G = nx.Graph()
        # Add all node hashes
        for node in graph_data["nodes"]:
            G.add_node(node["value_hash"])
            
        # Add all edges
        for link in graph_data["links"]:
            G.add_edge(link["source"], link["target"])
            
        if len(G.nodes) == 0:
            return []

        # Run label propagation community detection
        communities = list(nx.community.label_propagation_communities(G))
        return communities

    def get_cluster_mappings(self) -> dict[str, int]:
        """
        Returns a mapping of entity value_hash -> cluster_id
        """
        clusters = self.detect_clusters()
        mapping = {}
        for idx, cluster in enumerate(clusters):
            for node_hash in cluster:
                mapping[node_hash] = idx
        return mapping

# Global instance helper
_graph_service = None

def get_graph_service() -> GraphService:
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
