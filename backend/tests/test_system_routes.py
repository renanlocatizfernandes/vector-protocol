import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app


@pytest.mark.asyncio
async def test_supervisor_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/system/supervisor/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "interventions_tail" in data
        assert "flag_path" in data
        assert "log_path" in data
        assert isinstance(data["interventions_tail"], list)


@pytest.mark.asyncio
async def test_logs_endpoint_handles_missing_component():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Usa um prefixo inexistente para garantir comportamento 404 (ou 200 se o arquivo existir por acaso)
        resp = await client.get("/api/system/logs", params={"component": "__nope__", "tail": 5})
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            payload = resp.json()
            assert "component" in payload
            assert "file" in payload
            assert "lines" in payload and isinstance(payload["lines"], list)
