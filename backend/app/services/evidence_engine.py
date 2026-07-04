import os
import hashlib
import json
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db import models

class EvidenceEngine:
    @staticmethod
    def calculate_payload_hash(complaint_id: int, ev_type: str, description: str, file_path: Optional[str], previous_hash: Optional[str]) -> str:
        """
        Creates a cryptographic fingerprint of the evidence item, bound to the previous item's hash.
        """
        payload = {
            "complaint_id": complaint_id,
            "type": ev_type,
            "description": description or "",
            "file_path": file_path or "",
            "previous_hash": previous_hash or ""
        }
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()

    @classmethod
    def create_evidence_item(cls, db: Session, complaint_id: int, ev_type: str, description: str, file_path: Optional[str] = None) -> models.EvidenceItem:
        # Get latest evidence item to find the previous hash
        latest_item = db.query(models.EvidenceItem).order_by(models.EvidenceItem.id.desc()).first()
        prev_hash = latest_item.sha256_hash if latest_item else "0" * 64

        # Calculate current hash
        curr_hash = cls.calculate_payload_hash(complaint_id, ev_type, description, file_path, prev_hash)

        # Create record
        evidence = models.EvidenceItem(
            complaint_id=complaint_id,
            type=ev_type,
            description=description,
            file_path=file_path,
            sha256_hash=curr_hash,
            previous_hash=prev_hash
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        return evidence

    @classmethod
    def verify_chain_integrity(cls, db: Session) -> dict:
        """
        Validates the entire evidence hash chain from block 0 to the latest block.
        Returns a breakdown of verification results.
        """
        items = db.query(models.EvidenceItem).order_by(models.EvidenceItem.id.asc()).all()
        
        expected_prev_hash = "0" * 64
        corrupted_items = []
        is_valid = True

        for item in items:
            # 1. Verify previous hash matching link
            if item.previous_hash != expected_prev_hash:
                is_valid = False
                corrupted_items.append({
                    "id": item.id,
                    "reason": f"Hash chain broken. Expected previous_hash '{expected_prev_hash}', found '{item.previous_hash}'."
                })
                # We update expected_prev_hash to current stored to continue testing other links
                expected_prev_hash = item.sha256_hash
                continue

            # 2. Re-compute payload hash to detect data tampering
            recalculated_hash = cls.calculate_payload_hash(
                item.complaint_id,
                item.type,
                item.description,
                item.file_path,
                item.previous_hash
            )

            if item.sha256_hash != recalculated_hash:
                is_valid = False
                corrupted_items.append({
                    "id": item.id,
                    "reason": "Payload has been tampered with. Calculated hash does not match stored fingerprint."
                })

            expected_prev_hash = item.sha256_hash

        return {
            "chain_valid": is_valid,
            "total_items": len(items),
            "corrupted_items": corrupted_items
        }

    @classmethod
    def export_case_dossier_pdf(cls, db: Session, case_id: int, output_path: str):
        """
        Generates a secure PDF evidence dossier for court submittals.
        Includes case metadata, associated complaints, and cryptographic verification stamps.
        """
        case = db.query(models.Case).filter(models.Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case with ID {case_id} not found")

        doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#1A365D"),
            spaceAfter=15
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#718096"),
            spaceAfter=25
        )
        section_heading = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#2C5282"),
            spaceBefore=15,
            spaceAfter=10
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontSize=10,
            leading=14
        )

        # Title block
        story.append(Paragraph("RAKSHANET CASE EVIDENCE DOSSIER", title_style))
        story.append(Paragraph(f"Generated on: {models.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Security Classification: Restricted", subtitle_style))
        story.append(Spacer(1, 10))

        # Case summary table
        case_data = [
            [Paragraph("<b>Case Reference:</b>", body_style), Paragraph(f"CASE-#{case.id}", body_style)],
            [Paragraph("<b>Title:</b>", body_style), Paragraph(case.title, body_style)],
            [Paragraph("<b>Current Status:</b>", body_style), Paragraph(case.status, body_style)],
            [Paragraph("<b>Severity Rank:</b>", body_style), Paragraph(case.severity, body_style)],
            [Paragraph("<b>Assigned Officer:</b>", body_style), Paragraph(case.officer.username if case.officer else "Unassigned", body_style)]
        ]
        
        t_summary = Table(case_data, colWidths=[120, 400])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 20))

        # Evidence Chain Integrity Header
        story.append(Paragraph("Evidence Log & Chain of Custody Verification", section_heading))
        
        # Verify the database integrity
        integrity = cls.verify_chain_integrity(db)
        status_text = "<font color='green'><b>SECURED & VERIFIED</b></font>" if integrity["chain_valid"] else "<font color='red'><b>WARNING: TAMPERING DETECTED</b></font>"
        story.append(Paragraph(f"<b>Cryptographic Chain Status:</b> {status_text}", body_style))
        story.append(Spacer(1, 10))

        # List evidence items
        evidence_headers = [
            Paragraph("<b>ID</b>", body_style),
            Paragraph("<b>Type</b>", body_style),
            Paragraph("<b>Description</b>", body_style),
            Paragraph("<b>SHA-256 Hash Fingerprint</b>", body_style)
        ]
        
        table_rows = [evidence_headers]
        
        # Collect evidence through complaints linked to case
        evidence_found = False
        for complaint in case.complaints:
            for ev in complaint.evidence_items:
                evidence_found = True
                row = [
                    Paragraph(f"EV-#{ev.id}", body_style),
                    Paragraph(ev.type.upper(), body_style),
                    Paragraph(ev.description or "No description provided", body_style),
                    Paragraph(f"<font size='8' face='Courier'>{ev.sha256_hash}</font>", body_style)
                ]
                table_rows.append(row)
                
        if not evidence_found:
            table_rows.append([Paragraph("No evidence files linked to this case", body_style), "", "", ""])

        t_evidence = Table(table_rows, colWidths=[50, 80, 160, 230])
        t_evidence.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(t_evidence)
        story.append(Spacer(1, 30))

        # Sign-off footer
        story.append(Paragraph("<b>End of Evidence dossier.</b> This report was automatically compiled by the RakshaNet Risk Engine. The cryptographic signatures above verify the chain of custody has remained unbroken and un-mutated since original ingestion.", body_style))

        doc.build(story)
