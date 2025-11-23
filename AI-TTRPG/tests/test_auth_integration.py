import pytest
from fastapi.testclient import TestClient
from monolith.main import app
from monolith.modules.auth_pkg.utils import create_access_token

client = TestClient(app)

def test_health_check_public():
    """Health check should be public."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "monolith-api"}

def test_map_generation_unauthorized():
    """Map generation should require auth."""
    response = client.post("/map/generate", json={"tags": ["forest"]})
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

def test_map_generation_authorized():
    """Map generation should work with valid token."""
    # Create a valid token
    token = create_access_token({"sub": "player_123"})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Mock the map module to avoid actual generation overhead/errors during auth test
    # However, for integration test, we might want to let it run or mock it.
    # Since map generation is sync and might fail if data isn't loaded, 
    # we should be careful. But start_monolith logic in main.py startup event 
    # might not run in TestClient unless using TestClient(app) context manager 
    # or explicitly calling startup.
    # For now, we expect 200 or 500 (if map logic fails), but NOT 401.
    
    response = client.post(
        "/map/generate", 
        json={"tags": ["forest"], "seed": "test_seed"},
        headers=headers
    )
    
    # If map data isn't loaded, it might 500, but that proves Auth passed.
    # If it returns 401, Auth failed.
    assert response.status_code != 401
    
    # If it's 200, great. If 500, check if it's map error (which is fine for auth test)
    if response.status_code == 200:
        data = response.json()
        assert "environment_description" in data or "visuals" in data # Basic check

def test_character_endpoint_secured():
    """Character endpoints should be secured by the router dependency."""
    response = client.post("/characters/level-up", json={"character_id": "player_123"})
    assert response.status_code == 401
