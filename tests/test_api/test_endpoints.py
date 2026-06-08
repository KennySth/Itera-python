import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Prueba que el endpoint de health check responda correctamente."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["database"] == "connected"

@pytest.mark.asyncio
async def test_get_offers_empty(async_client: AsyncClient):
    """Prueba obtener ofertas cuando la base de datos (mockeada) está vacía."""
    response = await async_client.get("/api/ia/offers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

@pytest.mark.asyncio
async def test_get_offers_with_data(async_client: AsyncClient, mock_mongodb, mock_job_offers_data):
    """Prueba obtener ofertas después de insertar datos de prueba en el mock de DB."""
    # Insertar datos en la base de datos en memoria
    await mock_mongodb["ofertas_laborales"].insert_many(mock_job_offers_data)
    
    response = await async_client.get("/api/ia/offers")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    assert data[0]["puesto"] == "Desarrollador Python"
    assert data[1]["empresa"] == "Data Corp"

@pytest.mark.asyncio
async def test_match_evaluate_endpoint(async_client: AsyncClient, mock_mongodb, mock_job_offers_data):
    """Prueba el endpoint RF-10 de evaluación de matching."""
    # Preparar la DB con ofertas
    await mock_mongodb["ofertas_laborales"].insert_many(mock_job_offers_data)
    
    payload = {
        "estudiante_id": "test-uuid-123",
        "vector_perfil": [0.8, 0.1, -0.5, 0.2, 0.9], # Mismo vector que "Desarrollador Python"
        "objetivo": "Python"
    }
    
    response = await async_client.post("/api/ia/match/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "score_general" in data
    assert "top_matches" in data
    assert len(data["top_matches"]) > 0
    # El mejor match debería ser "Desarrollador Python" por tener el mismo vector
    assert data["top_matches"][0]["puesto"] == "Desarrollador Python"
    assert data["top_matches"][0]["score"] > 90.0 # Aproximadamente 100%
