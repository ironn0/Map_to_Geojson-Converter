from fastapi.testclient import TestClient
from main import app


def test_signup_login_and_workspace_project_flow():
    client = TestClient(app)

    signup = client.post(
        "/api/auth/signup",
        json={
            "email": "demo@example.com",
            "password": "strong-pass-123",
            "full_name": "Demo User",
            "workspace_name": "Demo Workspace",
        },
    )
    assert signup.status_code == 200
    payload = signup.json()
    token = payload["token"]
    workspace_id = payload["workspace"]["id"]
    auth = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/auth/me", headers=auth)
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "demo@example.com"

    create_project = client.post(
        f"/api/workspaces/{workspace_id}/projects",
        json={"name": "First Project", "description": "Initial conversion batch"},
        headers=auth,
    )
    assert create_project.status_code == 200
    project = create_project.json()["project"]
    assert project["name"] == "First Project"

    list_projects = client.get(f"/api/workspaces/{workspace_id}/projects", headers=auth)
    assert list_projects.status_code == 200
    assert len(list_projects.json()["projects"]) == 1

    login = client.post(
        "/api/auth/login",
        json={"email": "demo@example.com", "password": "strong-pass-123"},
    )
    assert login.status_code == 200
