# System Architecture Document

This document outlines the software engineering design, algorithms, threat calculation mathematics, and schemas implemented inside **RakshaNet**.

---

## 1. Multi-Model Ingestion & Risk Fusion Mathematics

Threat evaluation leverages a dynamic normalization system. Standard arithmetic averages penalize scores if inputs are missing; instead, RakshaNet dynamically normalizes across *active* signals, adjusting the weight denominator.

### Mathematical Formulation
Let $S_i$ be the score contribution of model $i \in \{ \text{NLP}, \text{Graph}, \text{Audio}, \text{CV} \}$, and $W_i$ be its default priority weight:
$$W_{\text{NLP}} = 0.50, \quad W_{\text{Graph}} = 0.50, \quad W_{\text{Audio}} = 0.20, \quad W_{\text{CV}} = 0.30$$

If signal $i$ is absent, its score $S_i$ is ignored, and its weight $W_i$ is dropped from the denominator. The fused threat index $R$ is calculated as:
$$R = \frac{\sum_{i \in \text{Active}} S_i \cdot W_i}{\sum_{i \in \text{Active}} W_i}$$

This guarantees that an entity lacking voice audit or counterfeit note scans is scored fairly over NLP and Graph relations without artificially dragging down the output.

---

## 2. Connected Graph Campaign Clustering (Neo4j)

RakshaNet tracks criminal rings utilizing a localized spring-embedder network representation linked to a Neo4j database. 

### Label Propagation
- Entities are saved as `:Entity` nodes (`phone` or `account`).
- Connections are created when entities appear in the same complaint transcript (`:LINKED_TO {relation_type: "shared_complaint"}`).
- Community detection is computed dynamically by converting the graph into an undirected NetworkX graph and running **Label Propagation**:
  - Each node starts with its own label.
  - In each iteration, nodes update their label to match the majority label of their neighbors.
  - The resulting community groupings are pushed back to PostgreSQL as campaign IDs, surfacing clusters automatically in the Police Command view.

---

## 3. Geospatial PostGIS Infrastructure

### Grid Heatmap Density
Crime grid cells are aggregated on a grid width of approximately 5.5 km using spatial snapping queries:
```sql
SELECT 
    ST_Centroid(ST_Collect(location)) as centroid,
    COUNT(id) as density
FROM complaints
WHERE location IS NOT NULL
GROUP BY ST_SnapToGrid(location, 0.05);
```
This query maps incoming coordinates into discrete bounding boxes, returning GeoJSON cells to build the frontend heatmap without client-side clustering overhead.

### Jurisdictional Spatial Routing
Incoming complaints check if they lie within Delhi Police's bounds (`ST_Contains`):
```sql
SELECT id FROM jurisdictions 
WHERE ST_Contains(polygon_geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326));
```
If a coordinate intersects a jurisdiction's bounds, case files are automatically assigned to that jurisdiction's designated precinct officer.

---

## 4. Cryptographic Chain-of-Custody Schema

Evidence files are logged sequentially. Each block links back to the preceding hash, forming an immutable ledger.

```
+-------------------------------------------------------+
|                 Evidence Chain Block                  |
+-------------------------------------------------------+
|  id: Integer (Auto-increment)                         |
|  complaint_id: Integer (Foreign key)                 |
|  type: String ("transcript", "audio", "banknote")     |
|  description: String                                  |
|  file_path: String                                    |
|  sha256_hash: String (SHA-256 of metadata + payload)  |
|  previous_hash: String (Copied from last row hash)    |
|  created_at: DateTime                                 |
+-------------------------------------------------------+
```

### Verification Algorithm
To check for administrative database tampering, the system performs a sequential check on every record:
1. Re-calculates the block's current hash using its database attributes.
2. Asserts that the re-calculated hash matches the database value `sha256_hash`.
3. Verifies that the block's `previous_hash` matches the `sha256_hash` of the preceding record in the database.
If any value mismatch is detected, the verification fails, indicating tampering.

---

## 5. Storage and Parameter Paths

- **NLP Model**: Utilizes live calls to the Groq LLM API (model configured via `GROQ_MODEL`) with structured JSON schema responses.
- **Counterfeit Detection Histograms**: Hardcoded HSV ranges configured inside `backend/app/services/counterfeit_vision.py`.
- **Case Dossiers**: Exported case documents compile to PDF binaries dynamically on request using ReportLab canvas stream operations.
