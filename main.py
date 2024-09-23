import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
from uuid import uuid4
from chatbot import cap_chatbot
from data_loader import debtor_data, encrypt_data, decrypt_data
import redis
import json
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("La clé secrète JWT n'est pas définie. Veuillez la définir dans la variable d'environnement 'SECRET_KEY'.")


app = FastAPI()

# Add CORS Middleware to allow requests from le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connecter à Redis pour la persistance des sessions
try:
    redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
except redis.ConnectionError:
    raise HTTPException(status_code=500, detail="Impossible de se connecter à Redis.")

def get_session(session_id: str):
    """
    Récupère les données de session depuis Redis, déchiffrées.
    """
    session_data = redis_client.get(session_id)
    if session_data:
        return decrypt_data(session_data)
    else:
        return {"history": [], "user_verified": False, "first_name": "", "last_name": ""}

def save_session(session_id: str, session_data: dict, expiration=3600):
    """
    Enregistre les données de session chiffrées dans Redis.
    """
    encrypted_data = encrypt_data(session_data)
    redis_client.set(session_id, encrypted_data, ex=expiration)

def create_jwt_token(user_data):
    """
    Génère un JWT pour l'authentification de l'utilisateur.
    """
    payload = {
        "user": user_data,
        "exp": datetime.utcnow() + timedelta(hours=1)  # Expire dans 1 heure
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def decode_jwt_token(token: str):
    """
    Décode un JWT pour vérifier l'utilisateur.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Le token a expiré")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")

class Message(BaseModel):
    first_name: str
    last_name: str
    message: str
    session_id: Optional[str] = None

class UserVerification(BaseModel):
    first_name: str
    last_name: str

@app.post("/api/verify_user")
async def verify_user(user: UserVerification):
    """
    Vérifie si l'utilisateur existe dans la base de données des débiteurs.
    """
    first_name = user.first_name.strip().lower()
    last_name = user.last_name.strip().lower()
    user_data = debtor_data[(debtor_data['prenom_debiteur'].str.lower() == first_name) &
                            (debtor_data['nom_debiteur'].str.lower() == last_name)]
    if not user_data.empty:
        session_id = str(uuid4())
        session_data = get_session(session_id)
        session_data["user_verified"] = True
        session_data["first_name"] = first_name
        session_data["last_name"] = last_name
        save_session(session_id, session_data)
        return {"found": True, "session_id": session_id, "token": create_jwt_token(session_data)}
    else:
        return {"found": False}

@app.post("/api/chat")
async def chat(message: Message, token: str = Depends(decode_jwt_token)):
    """
    Gère la conversation avec l'utilisateur en fonction de l'entrée utilisateur.
    """
    session_data = get_session(message.session_id)
    if session_data["user_verified"]:
        first_name = session_data["first_name"]
        last_name = session_data["last_name"]
        user = debtor_data[(debtor_data['prenom_debiteur'].str.lower() == first_name) &
                           (debtor_data['nom_debiteur'].str.lower() == last_name)]
        if not user.empty:
            response = cap_chatbot.get_response(message.message, first_name, last_name, message.session_id, debtor_data)
            session_data["history"].append({"user": message.message, "bot": response})
            save_session(message.session_id, session_data)
            return {"response": response, "session_id": message.session_id}
        else:
            return {"response": "Je ne trouve pas vos informations dans notre base de données.", "session_id": message.session_id}
    else:
        raise HTTPException(status_code=401, detail="Utilisateur non vérifié")
