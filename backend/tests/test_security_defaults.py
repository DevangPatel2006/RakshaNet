import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.core.config import settings

def test_startup_dev_warnings():
    # If ENV == "dev", startup should proceed without error
    # even if JWT_SECRET or NEO4J_PASSWORD are default values
    with patch("app.core.config.settings.ENV", "dev"), \
         patch("app.core.config.settings.JWT_SECRET", "supersecretkeyforrakshanetdev"), \
         patch("app.core.config.settings.NEO4J_PASSWORD", "neo4jpassword"), \
         patch("app.main.SessionLocal") as mock_session, \
         patch("app.main.init_db") as mock_init_db, \
         patch("app.main.get_event_bus") as mock_get_event_bus:
        
        mock_get_event_bus.return_value.start_consumer = AsyncMock()
        from app.main import startup_event
        # Should not raise exception
        startup_event()

def test_startup_prod_refuses_default_jwt_secret():
    # If ENV == "prod" and JWT_SECRET is default, raise RuntimeError
    with patch("app.core.config.settings.ENV", "prod"), \
         patch("app.core.config.settings.JWT_SECRET", "supersecretkeyforrakshanetdev"), \
         patch("app.core.config.settings.NEO4J_PASSWORD", "securepassword"):
        
        from app.main import startup_event
        with pytest.raises(RuntimeError) as exc_info:
            startup_event()
        assert "CRITICAL SECURITY ERROR" in str(exc_info.value)
        assert "JWT_SECRET" in str(exc_info.value)

def test_startup_prod_refuses_default_neo4j_password():
    # If ENV == "prod" and NEO4J_PASSWORD is default, raise RuntimeError
    with patch("app.core.config.settings.ENV", "prod"), \
         patch("app.core.config.settings.JWT_SECRET", "securejwtsecret"), \
         patch("app.core.config.settings.NEO4J_PASSWORD", "neo4jpassword"):
        
        from app.main import startup_event
        with pytest.raises(RuntimeError) as exc_info:
            startup_event()
        assert "CRITICAL SECURITY ERROR" in str(exc_info.value)
        assert "NEO4J_PASSWORD" in str(exc_info.value)

def test_startup_prod_allows_non_defaults():
    # If ENV == "prod" and both secrets are changed, allow startup
    with patch("app.core.config.settings.ENV", "prod"), \
         patch("app.core.config.settings.JWT_SECRET", "securejwtsecret"), \
         patch("app.core.config.settings.NEO4J_PASSWORD", "securepassword"), \
         patch("app.main.SessionLocal") as mock_session, \
         patch("app.main.init_db") as mock_init_db, \
         patch("app.main.get_event_bus") as mock_get_event_bus:
        
        mock_get_event_bus.return_value.start_consumer = AsyncMock()
        from app.main import startup_event
        startup_event()
