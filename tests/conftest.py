import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from app.core import database
from main import app

# Fixture para simular la base de datos MongoDB en memoria
@pytest_asyncio.fixture(autouse=True)
async def mock_mongodb():
    """
    Reemplaza el cliente de MongoDB real por uno simulado (mongomock_motor)
    antes de ejecutar cada test. Esto asegura que los tests no toquen la DB real.
    """
    # Creamos un cliente falso en memoria
    mock_client = AsyncMongoMockClient()
    mock_db = mock_client["test_db"]
    
    # Sobrescribimos las variables globales en database.py
    database.db.client = mock_client
    database.db.db = mock_db
    
    yield mock_db
    
    # Limpieza después del test (opcional con mongomock, pero buena práctica)
    database.db.client = None
    database.db.db = None

# Fixture para el cliente HTTP de la API (TestClient)
@pytest_asyncio.fixture
async def async_client():
    """
    Proporciona un cliente HTTP asíncrono para probar los endpoints de FastAPI.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

# Fixture de datos de prueba
@pytest.fixture
def mock_job_offers_data():
    return [
        {
            "puesto": "Desarrollador Python",
            "empresa": "Tech Solutions",
            "fuente": "Computrabajo",
            "url_origen": "http://test.com/1",
            "habilidades_requeridas": ["Python", "SQL"],
            "vector_semantico": [0.8, 0.1, -0.5, 0.2, 0.9],
            "salario_normalizado_usd": 1500.0
        },
        {
            "puesto": "Analista de Datos",
            "empresa": "Data Corp",
            "fuente": "Computrabajo",
            "url_origen": "http://test.com/2",
            "habilidades_requeridas": ["Python", "Power BI", "SQL"],
            "vector_semantico": [0.7, 0.3, -0.4, 0.1, 0.8],
            "salario_normalizado_usd": 1200.0
        }
    ]
