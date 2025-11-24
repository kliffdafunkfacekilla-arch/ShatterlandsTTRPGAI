import pytest
from fastapi.testclient import TestClient
from monolith.main import app
from monolith.modules.auth_pkg.utils import create_access_token

client = TestClient(app)

def test_reload_rules_unauthorized():
    """Reload endpoint should require auth."""
    response = client.post("/admin/reload-rules")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

def test_reload_rules_authorized():
    """Reload endpoint should work with valid token."""
    token = create_access_token({"sub": "admin_user"})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post("/admin/reload-rules", headers=headers)
    
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Game rules and map data reloaded successfully."}
