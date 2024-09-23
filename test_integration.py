from fastapi.testclient import TestClient
from main import app
import redis
from uuid import uuid4

client = TestClient(app)

# Configurer la connexion à Redis pour les tests
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

def test_verify_user():
    response = client.post("/api/verify_user", json={"first_name": "Laurie", "last_name": "Pailhet"})
    assert response.status_code == 200
    assert response.json()["found"] == True

def test_verify_user_not_found():
    response = client.post("/api/verify_user", json={"first_name": "fake", "last_name": "user"})
    assert response.status_code == 200
    assert response.json()["found"] == False

def test_chat():
    session_id = str(uuid4())
    client.post("/api/verify_user", json={"first_name": "Laurie", "last_name": "Pailhet", "session_id": session_id})
    response = client.post("/api/chat", json={"first_name": "Laurie", "last_name": "Pailhet", "message": "Qui est mon gestionnaire de dossier?", "session_id": session_id})
    assert response.status_code == 200
    assert "gestionnaire de dossier" in response.json()["response"]

def test_chat_user_not_found():
    session_id = str(uuid4())
    response = client.post("/api/chat", json={"first_name": "fake", "last_name": "user", "message": "Qui est mon gestionnaire de dossier?", "session_id": session_id})
    assert response.status_code == 200
    assert "Je ne trouve pas vos informations dans notre base de données." in response.json()["response"]

def clean_redis():
    # Nettoyer les sessions créées pendant les tests
    keys = redis_client.keys()
    for key in keys:
        redis_client.delete(key)

# Nettoyer Redis après les tests
clean_redis()
