import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app

@pytest.fixture(autouse=True)
def mock_redis_publish():
    with patch("app.services.event_bus.RedisEventBus.publish_alert", new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture(autouse=True)
def mock_groq():
    from app.services.groq_client import get_groq_client
    client = get_groq_client()
    client.mock_mode = True
    
    # Configure mock prediction rules to mimic old local model features for unit tests
    def mock_classify(text):
        txt_lower = text.lower()
        if any(k in txt_lower for k in ["cbi", "arrest", "police", "contraband", "skype", "money laundering"]):
            return {
                "is_scam": True,
                "scam_type": "digital_arrest",
                "confidence": 82.5,
                "explanation": "Detected digital arrest keywords."
            }
        elif any(k in txt_lower for k in ["kyc", "block", "link", "risk check"]):
            return {
                "is_scam": True,
                "scam_type": "phishing",
                "confidence": 70.0,
                "explanation": "Detected phishing keywords."
            }
        else:
            return {
                "is_scam": False,
                "scam_type": "none",
                "confidence": 15.0,
                "explanation": "No scam features detected."
            }
            
    client.mock_client = mock_classify
    yield
    client.mock_mode = False
    client.mock_client = None

# Dedicated test database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/rakshanet", "/rakshanet_test")

@pytest.fixture(scope="session")
def engine():
    # Connect to default postgres DB first to create the test database
    default_url = settings.DATABASE_URL.replace("/rakshanet", "/postgres")
    default_engine = create_engine(default_url)
    
    # Enable autocommit for database creation
    with default_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        try:
            conn.execute(text("CREATE DATABASE rakshanet_test;"))
            print("\nCreated test database 'rakshanet_test'")
        except Exception:
            # Database already exists
            pass
            
    # Return engine pointing to the test database
    engine = create_engine(TEST_DATABASE_URL)
    return engine

@pytest.fixture(scope="session")
def tables(engine):
    # Ensure PostGIS extension is loaded in the test database
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    
    Base.metadata.create_all(bind=engine)
    
    # Check/add spatial columns as GEOGRAPHY
    with engine.begin() as conn:
        res = conn.execute(text(
            "SELECT udt_name FROM information_schema.columns "
            "WHERE table_name='complaints' AND column_name='location';"
        )).first()
        if not res or res[0] != 'geography':
            conn.execute(text("ALTER TABLE complaints DROP COLUMN IF EXISTS location;"))
            conn.execute(text("ALTER TABLE complaints ADD COLUMN location GEOGRAPHY(Point, 4326);"))
            
        res = conn.execute(text(
            "SELECT udt_name FROM information_schema.columns "
            "WHERE table_name='jurisdictions' AND column_name='polygon_geom';"
        )).first()
        if not res or res[0] != 'geography':
            conn.execute(text("ALTER TABLE jurisdictions DROP COLUMN IF EXISTS polygon_geom;"))
            conn.execute(text("ALTER TABLE jurisdictions ADD COLUMN polygon_geom GEOGRAPHY(Polygon, 4326);"))
            
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine, tables):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    from fastapi.testclient import TestClient
    
    # Override get_db dependency to use the test transaction
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = _get_test_db
    yield TestClient(app)
    app.dependency_overrides.clear()
