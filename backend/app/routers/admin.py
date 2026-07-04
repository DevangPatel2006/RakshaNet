from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db import models
from app.routers.auth import RoleChecker

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/model-metrics", status_code=status.HTTP_200_OK)
def get_model_metrics(db: Session = Depends(get_db), current_user: models.User = Depends(RoleChecker(["admin"]))):
    metrics_list = db.query(models.ModelMetrics).all()
    metrics_by_name = {m.model_name: m for m in metrics_list}
    
    models_to_return = ["nlp_classifier", "counterfeit_vision", "speech_service", "graph_service"]
    response = []
    
    for name in models_to_return:
        m = metrics_by_name.get(name)
        if m and m.precision is not None and m.recall is not None and m.fpr is not None:
            response.append({
                "model_name": name,
                "status": "evaluated",
                "precision": round(m.precision, 2),
                "recall": round(m.recall, 2),
                "false_positive_rate": round(m.fpr, 2)
            })
        else:
            response.append({
                "model_name": name,
                "status": "not_yet_evaluated",
                "precision": None,
                "recall": None,
                "false_positive_rate": None
            })
            
    return response
