from fastapi.testclient import TestClient

from backend.api import app
from backend.database import session_scope
from backend.models import User, UserRole


def test_fastapi_auth_cookie_bearer_and_admin_summary():
    email = "api.admin@example.com"
    password = "Strong@123"
    with TestClient(app) as client:
        register = client.post("/api/v1/auth/register", json={"full_name": "API Admin", "email": email, "password": password})
        assert register.status_code in {201, 409}
        with session_scope() as session:
            user = session.query(User).filter(User.email == email).one()
            user.role = UserRole.ADMIN

        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        payload = login.json()
        token = payload["access_token"]
        assert client.cookies.get("finguard_access_token")

        me_cookie = client.get("/api/v1/me")
        assert me_cookie.status_code == 200
        assert me_cookie.json()["email"] == email

        me_bearer = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert me_bearer.status_code == 200

        summary = client.get("/api/v1/admin/summary", headers={"Authorization": f"Bearer {token}"})
        assert summary.status_code == 200
        assert "total_users" in summary.json()

        database = client.get("/api/v1/admin/database", headers={"Authorization": f"Bearer {token}"})
        assert database.status_code == 200
        assert database.json()["integrity"] == "ok"
        assert "users" in database.json()["table_counts"]

        logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert logout.status_code == 200
