"""
Fixtures compartidos para toda la suite de tests.
Usa SQLite en memoria para aislar los tests de la BD de producción.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db

_TEST_DB_URL = "sqlite:///./test_temp.db"

_engine = create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=_engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def usuario_autenticado(client):
    """Crea un usuario y devuelve (client, token) listos para usar."""
    client.post("/usuarios/", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "username": "testuser",
        "password": "password123",
    })
    token = resp.json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}
