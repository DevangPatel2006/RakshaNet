import re
import hashlib
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import models
from app.services.nlp_classifier import get_nlp_classifier
from app.services.graph_service import get_graph_service
from app.services.risk_fusion import get_risk_fusion
from app.services.evidence_engine import EvidenceEngine
from app.services.geospatial import GeospatialService
from app.services.event_bus import get_event_bus

class AIOrchestrator:
    @staticmethod
    async def process_complaint_signal(
        db: Session,
        text_content: str,
        reporter_name: Optional[str] = None,
        phone: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None
    ) -> models.Complaint:
        """
        Main ingestion pipeline for citizen reports and transcripts.
        1. NLP scoring
        2. Entity parsing (Regex search for phones & bank accounts in transcript)
        3. Graph cross-reference & risk propagation
        4. Risk fusion
        5. DB persistence + PostGIS placement
        6. Graph nodes/links creation & Neo4j sync (Compound Fingerprinting)
        7. Tamper-evident evidence chain binding
        8. Geospatial jurisdiction lookup
        9. Auto-case linking / creation
        10. Redis stream alert publishing
        """
        print(f"Orchestrator: Ingesting report from {reporter_name or 'Anonymous'}...")

        # 1. NLP scoring
        nlp_classifier = get_nlp_classifier()
        nlp_result = nlp_classifier.predict(text_content)
        nlp_score = nlp_result["risk_score"]

        # 2. Entity parsing (extract accounts and phones from transcript)
        entities_found = []
        if phone:
            # Clean and add explicit phone
            clean_phone = re.sub(r'\s+', '', phone)
            entities_found.append(("phone", clean_phone))

        # Find 10-14 digit numbers in the text that look like bank accounts or mobile numbers
        # Filter out numbers that match the explicit phone
        numeric_strings = re.findall(r'\b\d{10,14}\b', text_content)
        for num in numeric_strings:
            # Heuristic: if it looks like a phone (starts with 9, 8, 7) or general account
            ent_type = "phone" if num.startswith(('7', '8', '9')) and len(num) == 10 else "account"
            if not phone or num not in phone:
                entities_found.append((ent_type, num))

        # Remove duplicates from entities_found
        entities_found = list(set(entities_found))

        # 3. Graph cross-reference
        graph_service = get_graph_service()
        graph_score = 0.0
        linked_case_id = None

        # Cross-reference found entities against existing records to propagate risk
        postgres_entities = []
        for ent_type, ent_val in entities_found:
            value_hash = hashlib.sha256(ent_val.encode()).hexdigest()
            existing_entity = db.query(models.Entity).filter(models.Entity.value_hash == value_hash).first()
            if existing_entity:
                graph_score = max(graph_score, existing_entity.risk_score)
                postgres_entities.append(existing_entity)
                
                # Check for active cases linking this entity
                matching_comp = db.query(models.Complaint).filter(
                    (models.Complaint.phone == ent_val) | (models.Complaint.text_content.like(f"%{ent_val}%")),
                    models.Complaint.cases.any()
                ).first()
                if matching_comp and matching_comp.cases:
                    linked_case_id = matching_comp.cases[0].id
            else:
                # Create entity model locally to save later
                new_ent = models.Entity(
                    type=ent_type,
                    value=ent_val,
                    value_hash=value_hash,
                    risk_score=0.0
                )
                db.add(new_ent)
                postgres_entities.append(new_ent)

        db.commit()

        # 4. Risk Fusion
        risk_fusion = get_risk_fusion()
        fused = risk_fusion.fuse_scores(
            nlp_score=nlp_score,
            graph_score=graph_score if entities_found else None
        )
        final_score = fused["overall_score"]
        explanation = fused["explanation"]

        # 5. Postgres Ingestion
        complaint = models.Complaint(
            reporter_name=reporter_name,
            phone=phone,
            text_content=text_content,
            risk_score=final_score,
            risk_explanation=explanation
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)

        # Apply PostGIS coordinates
        if lat is not None and lng is not None:
            db.execute(
                text("UPDATE complaints SET location = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) WHERE id = :id"),
                {"lng": lng, "lat": lat, "id": complaint.id}
            )
            db.commit()

        # 6. Graph nodes/links creation & Neo4j sync (Compound Fingerprinting)
        # Update entity risk scores in database
        for ent in postgres_entities:
            ent.risk_score = max(ent.risk_score, final_score)
            db.commit()
            
            # Sync to Neo4j
            graph_service.add_entity(
                entity_id=ent.id,
                entity_type=ent.type,
                value=ent.value,
                risk_score=ent.risk_score
            )

        # Create LINKED_TO connections in Neo4j between all entities found in this complaint
        for i in range(len(postgres_entities)):
            for j in range(i + 1, len(postgres_entities)):
                ent_a = postgres_entities[i]
                ent_b = postgres_entities[j]
                
                # Save link in Neo4j
                graph_service.add_link(
                    val_a=ent_a.value,
                    val_b=ent_b.value,
                    relation_type="shared_complaint",
                    weight=1.0
                )
                
                # Save link in Postgres
                link_exists = db.query(models.EntityLink).filter(
                    ((models.EntityLink.entity_a_id == ent_a.id) & (models.EntityLink.entity_b_id == ent_b.id)) |
                    ((models.EntityLink.entity_a_id == ent_b.id) & (models.EntityLink.entity_b_id == ent_a.id))
                ).first()
                if not link_exists:
                    link = models.EntityLink(
                        entity_a_id=ent_a.id,
                        entity_b_id=ent_b.id,
                        relation_type="shared_complaint",
                        weight=1.0
                    )
                    db.add(link)
                    db.commit()

        # 7. Bind to Evidence Chain
        evidence = EvidenceEngine.create_evidence_item(
            db=db,
            complaint_id=complaint.id,
            ev_type="transcript",
            description=f"Citizen report transcript (Risk Score: {final_score}%)"
        )

        # 8. Geospatial Jurisdiction Routing
        assigned_officer_id = None
        jurisdiction_name = "General Headquarters"
        if lat is not None and lng is not None:
            delhi_jur = db.query(models.Jurisdiction).filter(models.Jurisdiction.name == "Delhi Police").first()
            if delhi_jur:
                inside = GeospatialService.is_complaint_in_jurisdiction(db, lat, lng, delhi_jur.id)
                if inside:
                    officer = db.query(models.User).filter(
                        models.User.role == "officer",
                        models.User.jurisdiction_id == delhi_jur.id
                    ).first()
                    if officer:
                        assigned_officer_id = officer.id
                        jurisdiction_name = "Delhi Police Jurisdiction"

        # 9. Auto Case Linking / Creation
        case = None
        if final_score >= 40.0:
            if linked_case_id:
                case = db.query(models.Case).filter(models.Case.id == linked_case_id).first()
                if case:
                    case.complaints.append(complaint)
                    db.commit()
            else:
                title = f"Campaign Alert: Phone {phone}" if phone else "Scam Alert: Ingestion Pipeline"
                case = models.Case(
                    title=title,
                    status="Open",
                    severity="High" if final_score >= 75.0 else "Medium",
                    assigned_officer_id=assigned_officer_id
                )
                db.add(case)
                db.commit()
                db.refresh(case)
                case.complaints.append(complaint)
                db.commit()
                print(f"Orchestrator: Auto-created case #{case.id} and assigned to officer ID {assigned_officer_id}")

        # 10. Alert stream publication
        severity_tag = "Critical" if final_score >= 75.0 else ("High" if final_score >= 40.0 else "Low")
        eb = get_event_bus()
        if final_score >= 40.0:
            desc = f"New report with risk score {final_score}%. Routed to {jurisdiction_name}. Details: {text_content[:60]}..."
            await eb.publish_alert(
                title="Suspicious Scam Call Ingested",
                description=desc,
                severity=severity_tag,
                target_role="officer"
            )

        if reporter_name:
            await eb.send_to_user(
                reporter_name,
                {
                    "title": "Your report has been analyzed",
                    "description": f"Risk Score: {final_score}%. {explanation}",
                    "severity": severity_tag,
                    "target_role": "citizen"
                }
            )

        db.refresh(complaint)
        return complaint
