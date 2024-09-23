import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
from chatbot import cap_chatbot
from data_loader import debtor_data, encrypt_data, decrypt_data
import redis
import json
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis un fichier .env
load_dotenv()

# Configurer le logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Récupérer la clé secrète JWT depuis les variables d'environnement
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("La clé secrète JWT n'est pas définie. Veuillez la définir dans la variable d'environnement 'SECRET_KEY'.")

app = FastAPI()

# Définir le schéma de sécurité avec HTTPBearer
security = HTTPBearer()

# Ajouter le middleware CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modifier selon vos besoins de sécurité
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connecter à Redis pour la persistance des sessions
try:
    redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    logger.info("Connexion à Redis réussie.")
except redis.ConnectionError:
    logger.error("Impossible de se connecter à Redis.")
    raise HTTPException(status_code=500, detail="Impossible de se connecter à Redis.")

def get_session(session_id: str):
    """
    Récupère les données de session depuis Redis, déchiffrées.
    """
    session_data = redis_client.get(session_id)
    if session_data:
        try:
            return decrypt_data(session_data)
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement des données de session : {e}")
            return {"history": [], "user_verified": False, "first_name": "", "last_name": "", "code_client": ""}
    else:
        return {"history": [], "user_verified": False, "first_name": "", "last_name": "", "code_client": ""}

def save_session(session_id: str, session_data: dict, expiration=3600):
    """
    Enregistre les données de session chiffrées dans Redis.
    """
    try:
        encrypted_data = encrypt_data(session_data)
        redis_client.set(session_id, encrypted_data, ex=expiration)
        logger.info(f"Session {session_id} sauvegardée avec expiration de {expiration} secondes.")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la session {session_id} : {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde de la session.")

def create_jwt_token(user_data):
    """
    Génère un JWT pour l'authentification de l'utilisateur.
    """
    payload = {
        "user": user_data,
        "exp": datetime.utcnow() + timedelta(hours=1)  # Expire dans 1 heure
    }
    try:
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        logger.info("Jeton JWT généré.")
        return token
    except Exception as e:
        logger.error(f"Erreur lors de la génération du jeton JWT : {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du jeton.")

def decode_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Décode un JWT pour vérifier l'utilisateur.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        logger.info("Jeton JWT décodé avec succès.")
        return payload["user"]
    except jwt.ExpiredSignatureError:
        logger.warning("Le jeton JWT a expiré.")
        raise HTTPException(status_code=401, detail="Le token a expiré")
    except jwt.InvalidTokenError:
        logger.warning("Jeton JWT invalide.")
        raise HTTPException(status_code=401, detail="Token invalide")

# Définir les modèles Pydantic
class Message(BaseModel):
    message: str
    session_id: Optional[str] = None

class UserVerification(BaseModel):
    first_name: str
    last_name: str
    code_client: str

@app.post("/api/verify_user")
async def verify_user(user: UserVerification):
    """
    Vérifie si l'utilisateur existe dans la base de données des débiteurs.
    """
    first_name = user.first_name.strip().lower()
    last_name = user.last_name.strip().lower()
    code_client = user.code_client.strip()

    # Convertir code_client en chaîne de caractères
    code_client = str(code_client)

    # Convertir code_client dans debtor_data en chaîne de caractères
    debtor_data['code_client'] = debtor_data['code_client'].astype(str).str.strip()

    # Rechercher l'utilisateur dans les données des débiteurs
    user_data_df = debtor_data[
        (debtor_data['prenom_debiteur'].str.lower() == first_name) &
        (debtor_data['nom_debiteur'].str.lower() == last_name) &
        (debtor_data['code_client'] == code_client)
    ]

    if not user_data_df.empty:
        session_id = str(uuid4())
        session_data = {
            "user_verified": True,
            "first_name": first_name,
            "last_name": last_name,
            "code_client": code_client,
            "history": []
        }
        try:
            save_session(session_id, session_data)
            token = create_jwt_token(session_data)
            logger.info(f"Utilisateur {first_name} {last_name} vérifié avec succès. Session ID: {session_id}")
            return {"found": True, "session_id": session_id, "token": token}
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'utilisateur : {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de la vérification de l'utilisateur.")
    else:
        logger.info(f"Utilisateur {first_name} {last_name} avec code client {code_client} non trouvé.")
        return {"found": False}

@app.post("/api/chat")
async def chat(message: Message, user_data: dict = Depends(decode_jwt_token)):
    """
    Gère la conversation avec l'utilisateur en fonction de l'entrée utilisateur.
    """
    try:
        logger.info(f"Message reçu: {message.message} | Session ID: {message.session_id}")
        session_data = get_session(message.session_id)
        logger.info(f"Données de session récupérées: {session_data}")

        if session_data and session_data.get("user_verified"):
            first_name = user_data.get("first_name")
            last_name = user_data.get("last_name")
            code_client = user_data.get("code_client")

            # Vérifier que les données utilisateur correspondent
            user = debtor_data[
                (debtor_data['prenom_debiteur'].str.lower() == first_name.lower()) &
                (debtor_data['nom_debiteur'].str.lower() == last_name.lower()) &
                (debtor_data['code_client'].astype(str) == str(code_client))
            ]

            logger.info(f"Utilisateur trouvé dans la base de données: {not user.empty}")

            if not user.empty:
                # Appel corrigé à get_response avec le bon nombre d'arguments
                response = cap_chatbot.get_response(
                    message.message, first_name, last_name, code_client, message.session_id
                )
                # Mettre à jour l'historique de la session
                session_data["history"].append({"user": message.message, "bot": response})
                save_session(message.session_id, session_data)
                logger.info(f"Réponse du chatbot: {response}")
                return {"response": response, "session_id": message.session_id}
            else:
                logger.warning("Informations de l'utilisateur non trouvées dans la base de données.")
                return {
                    "response": "Je ne trouve pas vos informations dans notre base de données.",
                    "session_id": message.session_id,
                }
        else:
            logger.warning("Session invalide ou utilisateur non vérifié.")
            raise HTTPException(status_code=401, detail="Utilisateur non vérifié ou session invalide")
    except Exception as e:
        logger.error(f"Erreur dans /api/chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Une erreur est survenue.")
