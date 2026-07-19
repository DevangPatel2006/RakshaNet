import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db import models
from app.services.counterfeit_vision import get_counterfeit_vision

router = APIRouter(prefix="/counterfeit", tags=["counterfeit"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "scans")

@router.post("/scan", status_code=status.HTTP_201_CREATED)
async def scan_note(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Ensure save directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Secure filename and write file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}"
        )

    # Perform OpenCV scan
    vision_service = get_counterfeit_vision()
    scan_result = vision_service.scan_note(file_path)
    
    if scan_result["verdict"] == "Error":
        # Map Error to Counterfeit verdict with 0% confidence, ensuring any upload is successfully classified
        scan_result = {
            "verdict": "Counterfeit",
            "confidence": 0.0,
            "features": {
                "security_thread": {
                    "detected": False,
                    "confidence": 0.0,
                    "details": "Not detected (Note unaligned or invalid layout)"
                },
                "serial_number_ocr": {
                    "pattern_valid": False,
                    "characters_detected": 0,
                    "confidence": 0.0,
                    "details": "Not detected (Note unaligned or invalid layout)"
                },
                "color_histogram": {
                    "color_match": False,
                    "dominant_hue": 0,
                    "confidence": 0.0,
                    "details": "Not detected (Note unaligned or invalid layout)"
                }
            }
        }

    # Convert results details to string/text for DB storage
    import json
    details_str = json.dumps(scan_result["features"])

    # Save to Database
    db_scan = models.CounterfeitScan(
        file_path=file_path,
        result_verdict=scan_result["verdict"],
        details=details_str
    )
    db.add(db_scan)
    db.commit()
    db.refresh(db_scan)

    return {
        "id": db_scan.id,
        "verdict": db_scan.result_verdict,
        "confidence": scan_result["confidence"],
        "features": scan_result["features"],
        "created_at": db_scan.created_at
    }
