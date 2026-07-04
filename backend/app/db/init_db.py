from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import Base, engine
from app.core.security import get_password_hash
from app.db import models

def init_db(db: Session):
    print("Enabling PostGIS extension...")
    db.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    db.commit()

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    db.commit()

    # Add geography column to complaints if not exists or is geometry
    print("Checking spatial columns...")
    res = db.execute(text(
        "SELECT udt_name FROM information_schema.columns "
        "WHERE table_name='complaints' AND column_name='location';"
    )).first()
    if not res or res[0] != 'geography':
        print("Adding/recreating location geography column on complaints...")
        db.execute(text("ALTER TABLE complaints DROP COLUMN IF EXISTS location;"))
        db.execute(text("ALTER TABLE complaints ADD COLUMN location GEOGRAPHY(Point, 4326);"))
        db.commit()

    # Add geography column to counterfeit_scans if not exists
    res = db.execute(text(
        "SELECT udt_name FROM information_schema.columns "
        "WHERE table_name='counterfeit_scans' AND column_name='location';"
    )).first()
    if not res or res[0] != 'geography':
        print("Adding/recreating location geography column on counterfeit_scans...")
        db.execute(text("ALTER TABLE counterfeit_scans DROP COLUMN IF EXISTS location;"))
        db.execute(text("ALTER TABLE counterfeit_scans ADD COLUMN location GEOGRAPHY(Point, 4326);"))
        db.commit()

    # Add geography column to jurisdictions if not exists
    res = db.execute(text(
        "SELECT udt_name FROM information_schema.columns "
        "WHERE table_name='jurisdictions' AND column_name='polygon_geom';"
    )).first()
    if not res or res[0] != 'geography':
        print("Adding/recreating polygon_geom geography column on jurisdictions...")
        db.execute(text("ALTER TABLE jurisdictions DROP COLUMN IF EXISTS polygon_geom;"))
        db.execute(text("ALTER TABLE jurisdictions ADD COLUMN polygon_geom GEOGRAPHY(Polygon, 4326);"))
        db.commit()

    # Seed initial jurisdictions
    print("Seeding initial data...")
    delhi = db.query(models.Jurisdiction).filter(models.Jurisdiction.name == "Delhi Police").first()
    if not delhi:
        delhi = models.Jurisdiction(name="Delhi Police")
        db.add(delhi)
        db.commit()
        db.refresh(delhi)
        
        # Add Delhi polygon using geography helper
        db.execute(text(
            f"UPDATE jurisdictions SET polygon_geom = ST_GeogFromText("
            f"'POLYGON((77.10 28.50, 77.30 28.50, 77.30 28.70, 77.10 28.70, 77.10 28.50))') "
            f"WHERE id = {delhi.id};"
        ))
        db.commit()

    # Seed default users
    roles_to_seed = [
        ("admin", "admin", "admin_pass"),
        ("officer", "officer_delhi", "officer_pass"),
        ("citizen", "citizen_john", "citizen_pass"),
        ("bank_analyst", "bank_analyst_sam", "bank_pass"),
        ("telecom_analyst", "telecom_analyst_tina", "telecom_pass"),
    ]

    for role, username, password in roles_to_seed:
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            print(f"Seeding user: {username} ({role})...")
            hashed_pw = get_password_hash(password)
            jur_id = delhi.id if role == "officer" else None
            user = models.User(
                username=username,
                hashed_password=hashed_pw,
                role=role,
                jurisdiction_id=jur_id
            )
            db.add(user)
            db.commit()

    # Model metrics will be written genuinely via evaluation scripts or remain not_yet_evaluated
    print("Database initialization and schema setup completed.")

    # Create database indexes if not exist
    print("Creating database indexes...")
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_complaints_location ON complaints USING GIST(location);"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_cases_status ON cases(status);"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_risk_score ON transactions(risk_score);"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_entity_links_ab ON entity_links(entity_a_id, entity_b_id);"))
    db.commit()

    print("Database initialization and seeding completed successfully.")
