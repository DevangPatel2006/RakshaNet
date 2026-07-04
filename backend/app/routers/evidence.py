import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db import models
from app.services.evidence_engine import EvidenceEngine

router = APIRouter(prefix="/evidence", tags=["evidence"])

@router.get("/verify", status_code=status.HTTP_200_OK)
def verify_evidence_chain(db: Session = Depends(get_db)):
    return EvidenceEngine.verify_chain_integrity(db)

@router.get("/{id}", status_code=status.HTTP_200_OK)
def get_evidence_details(id: int, db: Session = Depends(get_db)):
    ev = db.query(models.EvidenceItem).filter(models.EvidenceItem.id == id).first()
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence item not found"
        )
    
    # Run dynamic integrity check on this item
    recalculated_hash = EvidenceEngine.calculate_payload_hash(
        ev.complaint_id,
        ev.type,
        ev.description,
        ev.file_path,
        ev.previous_hash
    )
    is_valid = (ev.sha256_hash == recalculated_hash)

    return {
        "id": ev.id,
        "complaint_id": ev.complaint_id,
        "type": ev.type,
        "description": ev.description,
        "file_path": ev.file_path,
        "sha256_hash": ev.sha256_hash,
        "previous_hash": ev.previous_hash,
        "created_at": ev.created_at,
        "verification": {
            "valid": is_valid,
            "calculated_hash": recalculated_hash
        }
    }

@router.get("/{id}/export", response_class=FileResponse)
def export_evidence_dossier(id: int, db: Session = Depends(get_db)):
    ev = db.query(models.EvidenceItem).filter(models.EvidenceItem.id == id).first()
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence item not found"
        )
    
    # Try to find a linked case
    case = None
    complaint = ev.complaint
    if complaint and complaint.cases:
        case = complaint.cases[0]

    # Create temporary PDF file
    temp_dir = tempfile.gettempdir()
    pdf_filename = f"evidence_dossier_ev_{id}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_filename)

    try:
        if case:
            EvidenceEngine.export_case_dossier_pdf(db, case.id, pdf_path)
        else:
            # Create a fallback PDF dossier for a single complaint evidence
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
            story = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontSize=22, textColor=colors.HexColor("#1A365D"), spaceAfter=15)
            body_style = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10, leading=14)
            
            story.append(Paragraph("RAKSHANET COMPLAINT EVIDENCE DOSSIER", title_style))
            story.append(Paragraph(f"Generated on: {models.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Status: Unlinked to Case", styles["Normal"]))
            story.append(Spacer(1, 15))
            
            # Evidence Details
            recalc_hash = EvidenceEngine.calculate_payload_hash(ev.complaint_id, ev.type, ev.description, ev.file_path, ev.previous_hash)
            verified = "VERIFIED" if recalc_hash == ev.sha256_hash else "CORRUPTED/MUTATED"
            
            ev_data = [
                [Paragraph("<b>Evidence ID:</b>", body_style), Paragraph(f"EV-#{ev.id}", body_style)],
                [Paragraph("<b>Complaint ID:</b>", body_style), Paragraph(f"COMP-#{ev.complaint_id}", body_style)],
                [Paragraph("<b>Reporter:</b>", body_style), Paragraph(complaint.reporter_name or "Anonymous", body_style)],
                [Paragraph("<b>Evidence Type:</b>", body_style), Paragraph(ev.type.upper(), body_style)],
                [Paragraph("<b>Description:</b>", body_style), Paragraph(ev.description or "", body_style)],
                [Paragraph("<b>Cryptographic Fingerprint:</b>", body_style), Paragraph(f"<font size='8' face='Courier'>{ev.sha256_hash}</font>", body_style)],
                [Paragraph("<b>Previous block Hash:</b>", body_style), Paragraph(f"<font size='8' face='Courier'>{ev.previous_hash}</font>", body_style)],
                [Paragraph("<b>Chain Verification:</b>", body_style), Paragraph(f"<b>{verified}</b>", body_style)]
            ]
            t = Table(ev_data, colWidths=[130, 390])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(t)
            doc.build(story)

        # Return file response
        return FileResponse(
            path=pdf_path,
            filename=f"evidence_dossier_{id}.pdf",
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate evidence PDF: {str(e)}"
        )
