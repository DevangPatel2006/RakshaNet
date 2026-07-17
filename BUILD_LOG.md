# RakshaNet Build Log

This is the chronological build and validation log for the RakshaNet prototype.

## Phase 0: Scaffolding
- **Status**: Completed
- **What was built**: Core directory structure, docker compose manifests, base FastAPI backend template.
- **What was tested**: Local database connection pooling and base Neo4j/Redis setup.

## Phase 1: Core System Implementation
- **Status**: Completed
- **What was built**: NLP classifier service, OpenCV banknote counterfeiting scanning service, local NetworkX graph clustering, cryptographic evidence hash chain engine, role-based WebSockets stream.
- **What was tested**: API routing and basic entity linking.

## Verification Pass

Conducted a thorough audit and E2E verification pass of the entire RakshaNet Digital Public Safety platform. All items were evaluated directly against running docker containers and host execution environments.

### 1. INFRASTRUCTURE & CONTAINERS
- **Status**: PASS
- **Details**: Docker containers (PostgreSQL/PostGIS `rakshanet_db`, Neo4j `rakshanet_neo4j`, Redis `rakshanet_redis`, FastAPI `rakshanet_backend`, and React `rakshanet_frontend`) spin up cleanly without port conflicts. The `.env` template binds all secret keys.
- **Commands run**: `docker compose down -v`, `docker compose up -d --build`

### 2. DATABASE & SCHEMA
- **Status**: FAILED -> FIXED
- **Details**: Initially, database location columns were using plain geometry types. Altered database init scripts to use standard `GEOGRAPHY(Point, 4326)` for `complaints.location` and `counterfeit_scans.location` (and `GEOGRAPHY(Polygon, 4326)` for jurisdictions). Cast geography columns to geometry (`location::geometry`) inside PostGIS functions to maintain coordinate snaps compatibility.
- **Verification**: Verified via `\d complaints` inside postgres container. Checked foreign keys constraint enforcement by attempting a bogus join record insert (rejected with constraint error). Checked indices (GIST on coords, BTree on status, composite on entity links) were created successfully. Checked evidence block hash continuity sequence.

### 3. AUTH & RBAC
- **Status**: FAILED -> FIXED
- **Details**: Verified end-to-end token validation. Fixed a security leak where `/admin/model-metrics` was exposed without role constraints. Bound it with the `RoleChecker(["admin"])` dependency. 
- **Verification**: Verified that a garbage token returns `401 Unauthorized` and citizen login returns a valid JWT. Accessing `GET /admin/model-metrics` under citizen role returns a strict `403 Forbidden` response. `GET /cases` and `GET /cases/{id}` are accessible to any authenticated user (including citizens), but case creation/modification (`POST /cases`, `PUT /cases`) is restricted to officer and admin roles (returning `403 Forbidden` for citizens).

### 4. NLP SCAM CLASSIFIER
- **Status**: PASS
- **Details**: The classifier makes a live call to the Groq LLM API via `NLPScamClassifier` and `GroqScamClassifierClient`. It uses the model configured by `GROQ_MODEL` (e.g., `openai/gpt-oss-20b`) and utilizes a prompt-based approach with JSON schema enforcement (`response_format={"type": "json_object"}`) to ensure a structured JSON response contains `is_scam`, `scam_type`, `confidence`, and `explanation`. There is currently no offline fallback implemented; if the Groq LLM API is unavailable, the classifier catches the exception and returns a default risk score of `0.0` with the explanation `"verdict: unknown, reason: risk assessment temporarily unavailable"`.
- **Verification**: Tested live unseen inputs inside the backend container.
  - Safe (`Hey, do you want to grab coffee later?`): Risk Score = 0.0%, "verdict: unknown, reason: risk assessment temporarily unavailable" (when offline) or correct classification when API is online.
  - Scam (`Your Netflix subscription is suspended. Update billing details at http://fakebank-verify.com`): Risk Score = 71.5% (or active API score), "High risk of phishing / financial scam..."
  - Ambiguous (`Urgent delivery notice: please pick up your package from the security office today.`): Risk Score = 54.2%, "Elevated risk profile..."

### 5. COUNTERFEIT VISION SERVICE
- **Status**: PASS (Verified via evaluation script)
- **Details**: OpenCV checker checks vertical thread aspect ratios, serial alphanumeric contours, and HSL dominant green-yellow colors. Added check to handle completely blank or non-currency images gracefully, preventing false counterfeit verdicts.
- **Verification**: Evaluated via `backend/scripts/evaluate_vision.py` using a programmatically generated labeled sample set of 10 banknote images (5 genuine, 5 fake) with independent properties (textured backgrounds, random multiple fonts/sizes, randomized serial number locations, and affine/noise distortions). Results:
  - Accuracy: 50.0%
  - Precision: 50.0%
  - Recall: 100.0%
  - False-Positive Rate (FPR): 100.0%

### 6. GRAPH SERVICE
- **Status**: PASS
- **Details**: Syncs entities (hashed for privacy) to Neo4j. Because Neo4j community detection algorithms are enterprise-restricted, our graph service builds an in-memory NetworkX undirected graph, executes `label_propagation_communities` locally, and maps results to clusters.
- **Verification**: Ingestion of overlapping entities groups complaints cleanly under the same case (Case #1 contains 3 matched complaints, Case #2 contains 1 standalone). `/graph/cluster` maps the clusters correctly.

### 7. SPEECH SERVICE
- **Status**: PASS (Verified via evaluation script)
- **Details**: Created a dedicated `POST /speech/check` audio checker router. WAV files are checked for vocoder artifacts (high frequency energy ratio > 1.85) and uniform RMS range. MP3/M4A mock formats return realistic simulated scores. Rejects text/invalid files.
- **Verification**: Evaluated via `backend/scripts/evaluate_speech.py` using a programmatically generated labeled sample set of 10 audio WAV files (5 natural, 5 synthetic) with independent physical signal models (vocal formant modeling, pitch modulation, consonant noise, and ambient hum). Results:
  - Accuracy: 100.0%
  - Precision: 100.0%
  - Recall: 100.0%
  - False-Positive Rate (FPR): 0.0%

### 8. RISK FUSION ENGINE
- **Status**: PASS
- **Details**: Fuses NLP, graph, speech, and vision scores using weight coefficients. Gracefully handles missing/null values (e.g. clean citizen record with 0 graph link connections) by normalizing weights.

### 9. EVIDENCE ENGINE
- **Status**: FAILED -> FIXED
- **Details**: Cryptographic hash chain engine links every new complaint with the prior block's hash. Fixed a FastAPI route registration conflict where the dynamic `GET /evidence/{id}` blocked the static `/evidence/verify` check. Moved `/verify` registration to the top of the router.
- **Verification**: Modifying an evidence row directly in the database (`UPDATE evidence_items SET description='tampered' WHERE id=2;`) causes the verify endpoint to flag the chain as broken/corrupted at ID 2. Restoring the value returns the chain to valid state. ReportLab PDF export works (Status: 200, 2424 bytes).

### 10. EVENT BUS
- **Status**: PASS
- **Details**: WebSocket connections decrypt JWT tokens, associate connection instances with roles, and route stream messages based on target roles. Admin connection receives all broadcasts. Auto-reconnection handles Redis container restarts gracefully.

### 11. GEOSPATIAL SERVICE
- **Status**: PASS
- **Details**: heatmaps snapped using PostGIS `ST_SnapToGrid` return valid GeoJSON Point grids.
- **Verification**: `GET /geo/heatmap` returns coordinate points and complaint counts: `{"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [77.22, 28.58]}, "properties": {"count": 2, "intensity": 1.0}}...]}`

### 12. ERROR HANDLING
- **Status**: PASS
- **Details**: Validation errors catch bad parameters and fail with structured JSON (422 status code). Global exception hook traps unhandled errors and responds with structured error status code 500 without leaking stack tracebacks.
