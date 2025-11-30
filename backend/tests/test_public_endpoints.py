import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app


@pytest.mark.asyncio
async def test_version_endpoint():
    # Desativa lifespan para evitar execução de criação de tabelas/DB durante o teste
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/version")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert data["version"] == "1.1.0"


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "online"
        assert data.get("docs") == "/docs"
