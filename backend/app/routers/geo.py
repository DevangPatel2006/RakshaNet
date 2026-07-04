from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.geospatial import GeospatialService

router = APIRouter(prefix="/geo", tags=["geo"])

@router.get("/heatmap", status_code=status.HTTP_200_OK)
def get_heatmap(grid_size: float = Query(0.05, ge=0.001, le=1.0), db: Session = Depends(get_db)):
    return GeospatialService.get_heatmap_geojson(db, grid_size)
