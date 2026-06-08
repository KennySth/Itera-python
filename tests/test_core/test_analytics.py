import pytest
from app.core.analytics import _categorize_job_title

def test_categorize_job_title():
    # Frontend
    assert _categorize_job_title("Desarrollador React Senior") == "Desarrollo Frontend"
    assert _categorize_job_title("Especialista UI/UX") == "Desarrollo Frontend"
    
    # Backend
    assert _categorize_job_title("Programador Java Backend") == "Desarrollo Backend"
    assert _categorize_job_title("Python Developer") == "Desarrollo Backend"
    
    # Fullstack
    assert _categorize_job_title("Desarrollador Full Stack") == "Desarrollo Fullstack"
    assert _categorize_job_title("Fullstack Developer Python/React") == "Desarrollo Fullstack"
    
    # Data / AI
    assert _categorize_job_title("Científico de Datos") == "Ciencia de Datos e IA"
    assert _categorize_job_title("Machine Learning Engineer") == "Ciencia de Datos e IA"
    
    # Infra / Cloud
    assert _categorize_job_title("Ingeniero DevOps AWS") == "Infraestructura y Cloud"
    assert _categorize_job_title("Administrador de Sistemas Cloud") == "Infraestructura y Cloud"
    
    # General (Fallback)
    assert _categorize_job_title("Programador Junior") == "Desarrollo de Software General"
    assert _categorize_job_title("Consultor TI") == "Desarrollo de Software General"
