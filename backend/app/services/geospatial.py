from sqlalchemy import text
from sqlalchemy.orm import Session

class GeospatialService:
    @staticmethod
    def get_heatmap_geojson(db: Session, grid_size: float = 0.05) -> dict:
        """
        Groups complaints using PostGIS ST_SnapToGrid and aggregates them into count cells.
        Returns a GeoJSON FeatureCollection.
        """
        # Snap locations to a grid of size grid_size (e.g. 0.05 degrees ~= 5.5km)
        # We calculate the centroid of the snapped points as the grid cell point.
        # Cast location (geography) to geometry for ST_SnapToGrid and ST_Collect operations.
        query = text("""
            SELECT 
                ST_X(ST_Centroid(ST_Collect(location::geometry))) AS lng,
                ST_Y(ST_Centroid(ST_Collect(location::geometry))) AS lat,
                COUNT(id) AS count
            FROM complaints
            WHERE location IS NOT NULL
            GROUP BY ST_SnapToGrid(location::geometry, :grid_size);
        """)
        
        results = db.execute(query, {"grid_size": grid_size}).fetchall()
        
        features = []
        max_count = max([r[2] for r in results]) if results else 1

        for r in results:
            lng, lat, count = r
            if lng is None or lat is None:
                continue
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lng), float(lat)]
                },
                "properties": {
                    "count": int(count),
                    "intensity": round(float(count) / max_count, 2)
                }
            })
            
        return {
            "type": "FeatureCollection",
            "features": features
        }

    @staticmethod
    def is_complaint_in_jurisdiction(db: Session, complaint_lat: float, complaint_lng: float, jurisdiction_id: int) -> bool:
        """
        Checks if a point (lat, lng) lies inside a jurisdiction's polygon geography.
        """
        # Cast polygon_geom (geography) to geometry for ST_Contains check.
        query = text("""
            SELECT ST_Contains(
                (SELECT polygon_geom::geometry FROM jurisdictions WHERE id = :jur_id),
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
            );
        """)
        res = db.execute(query, {"jur_id": jurisdiction_id, "lng": complaint_lng, "lat": complaint_lat}).scalar()
        return bool(res)
