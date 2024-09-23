import streamlit as st
from data_loader import debtor_data
from chatbot import cap_chatbot
import redis
import logging
import json
from uuid import uuid4

st.title("CAP Recouvrement Chatbot")

# Connecter à Redis pour la persistance des sessions
try:
    redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
except redis.ConnectionError:
    st.error("Impossible de se connecter à Redis. Veuillez vérifier que le serveur Redis est en cours d'exécution !")
    st.stop()

def get_session(session_id):
    """
    Récupère les données de session depuis Redis.

    Args:
        session_id (str): Identifiant de la session.

    Returns:
        dict: Données de session, ou un dictionnaire par défaut si la session n'existe pas.
    """
    session_data = redis_client.get(session_id)
    if session_data:
        try:
            return json.loads(session_data)
        except json.JSONDecodeError as e:
            logging.error(f"Erreur lors du décodage JSON pour la session {session_id}: {e}")
            # Return default session data to avoid crashes
            return {"user_verified": False, "first_name": "", "last_name": "", "code_client": "", "qa_history": []}
    else:
        return {"user_verified": False, "first_name": "", "last_name": "", "code_client": "", "qa_history": []}
    
def save_session(session_id, session_data):
    """
    Enregistre les données de session dans Redis.

    Args:
        session_id (str): Identifiant de la session.
        session_data (dict): Données de session à enregistrer.
    """
    redis_client.set(session_id, json.dumps(session_data))

def clean_old_sessions():
    """
    Supprime les sessions obsolètes de Redis après une période d'inactivité définie.
    """
    session_keys = redis_client.keys()
    for key in session_keys:
        session_data = redis_client.get(key)
        if session_data:
            try:
                session_data = json.loads(session_data)  # Attempt to parse JSON
                # Add logic to check if session is obsolete
                if not session_data['user_verified'] and len(session_data['qa_history']) == 0:
                    logging.info(f"Suppression de la session obsolète: {key}")
                    redis_client.delete(key)
            except json.JSONDecodeError as e:
                logging.error(f"Erreur lors du décodage JSON de la session {key}: {e}")
                # Optionally handle this error, such as deleting the invalid session
                redis_client.delete(key)  # Remove corrupted session data

# Initialiser les variables de session
session_id = st.session_state.get('session_id', None)
if not session_id:
    session_id = str(uuid4())
    st.session_state['session_id'] = session_id

session_data = get_session(session_id)

if not session_data['user_verified']:
    first_name = st.text_input("Entrez votre prénom").strip().lower()
    last_name = st.text_input("Entrez votre nom").strip().lower()
    code_client = st.text_input("Entrez votre code client").strip()

    if st.button("Se Connecter"):
        if first_name and last_name:
            debtor_data['prenom_debiteur'] = debtor_data['prenom_debiteur'].str.strip().str.lower()
            debtor_data['nom_debiteur'] = debtor_data['nom_debiteur'].str.strip().str.lower()
            user = debtor_data[(debtor_data['prenom_debiteur'] == first_name) &
                               (debtor_data['nom_debiteur'] == last_name) &
                               (debtor_data['code_client'].astype(str) == code_client)]
            if not user.empty:
                session_data['user_verified'] = True
                session_data['first_name'] = first_name
                session_data['last_name'] = last_name
                session_data['code_client'] = code_client
                save_session(session_id, session_data)
                st.success(f"Bonjour {first_name.capitalize()} {last_name.capitalize()}, vous pouvez maintenant poser votre question.")
            else:
                st.error("Débiteur non trouvé dans la base de données de CAP Recouvrement! Veuillez vérifier vos informations et réessayer.")

if session_data['user_verified']:
    first_name = session_data['first_name']
    last_name = session_data['last_name']
    code_client = session_data['code_client']
   
    user_input = st.text_input("Posez votre question")
   
    if st.button("Envoyer") and user_input:
        response = cap_chatbot.get_response(user_input, first_name, last_name, code_client, debtor_data)
        session_data['qa_history'].append((user_input, response))
        save_session(session_id, session_data)
   
    for question, answer in session_data['qa_history']:
        st.markdown(f"""
        <div style='background-color: #e8f4f8; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>
            <p style='margin: 0; color: #333;'><strong>Question :</strong> {question}</p>
            <p style='margin: 0; color: #333;'><strong>Réponse :</strong> {answer}</p>
        </div>
        """, unsafe_allow_html=True)

    if user_input.lower() in ["au revoir", "bonne soirée"]:
        session_data = {"user_verified": False, "first_name": "", "last_name": "", "code_client": "", "qa_history": []}
        save_session(session_id, session_data)
        st.write("Au revoir ! Passez une bonne journée !")

clean_old_sessions()  # Nettoyer les sessions obsolètes
