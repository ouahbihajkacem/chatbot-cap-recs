from transformers import AutoTokenizer, TFAutoModel
import pandas as pd
import tensorflow as tf
from data_loader import debtor_data
from indexer import vector_db, metadata
import logging
from pydantic import BaseModel, ValidationError
from collections import OrderedDict
import re

# Charger le modèle de transformers
try:
    tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
    model = TFAutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
except Exception as e:
    raise RuntimeError(f"Erreur lors du chargement du modèle de transformers: {e}")

class UserVerification(BaseModel):
    first_name: str  # Validation via la méthode validate_name
    last_name: str   
    code_client: str 

    @staticmethod
    def validate_name(name: str):
        """
        Validation manuelle du prénom et du nom avec regex.
        """
        if not re.match(r'^[a-zA-Z]+$', name):
            raise ValueError(f"Invalid name: {name}")

    def __init__(self, **data):
        super().__init__(**data)
        self.validate_name(self.first_name)
        self.validate_name(self.last_name)

def verify_user(first_name, last_name, code_client, debtor_data):
    """
    Vérifie si un utilisateur existe dans la base de données des débiteurs.

    Args:
        first_name (str): Prénom de l'utilisateur.
        last_name (str): Nom de l'utilisateur.
        code_client (str): Code client de l'utilisateur.
        debtor_data (pd.DataFrame): Données des débiteurs.

    Returns:
        pd.DataFrame or None: Les informations de l'utilisateur si trouvées, sinon None.
    """
    try:
        user = debtor_data[(debtor_data['prenom_debiteur'].str.lower() == first_name) &
                           (debtor_data['nom_debiteur'].str.lower() == last_name) &
                           (debtor_data['code_client'].astype(str) == code_client)]
        return user if not user.empty else None
    except Exception as e:
        logging.error(f"Erreur lors de la vérification de l'utilisateur: {e}")
        return None

class CAPRecouvrementChatBot:
    """
    Classe pour gérer les interactions avec le chatbot CAP Recouvrement.

    Attributes:
        vector_db (faiss.Index): L'index FAISS pour la recherche de similarités.
        metadata (list): Métadonnées associées aux questions-réponses.
        memory (OrderedDict): Mémoire LRU des utilisateurs pour stocker les données récentes.
        memory_limit (int): Limite du nombre d'utilisateurs stockés en mémoire.
    """
   
    def __init__(self, vector_db, metadata, memory_limit=100):
        """
        Initialise le chatbot avec la base de données vectorielle et les métadonnées.

        Args:
            vector_db (faiss.Index): L'index FAISS pour la recherche.
            metadata (list): Liste des métadonnées pour chaque entrée de l'index.
            memory_limit (int, optional): Limite de la mémoire LRU. Par défaut 100.
        """
        self.vector_db = vector_db
        self.metadata = metadata
        self.memory = OrderedDict()  # Utilisation d'un OrderedDict pour LRU
        self.memory_limit = memory_limit

    def manage_memory(self, user_key):
        """
        Gère la mémoire LRU en supprimant le plus ancien utilisateur si la limite est atteinte.

        Args:
            user_key (str): Clé utilisateur unique basée sur le prénom, le nom et le code client.
        """
        if len(self.memory) >= self.memory_limit:
            oldest_user_key = next(iter(self.memory))
            logging.info(f"Limite de mémoire atteinte, suppression de l'utilisateur le plus ancien: {oldest_user_key}")
            self.memory.pop(oldest_user_key)

    def get_response(self, user_input, first_name, last_name, code_client, debtor_data):
        """
        Génère une réponse du chatbot en fonction de l'entrée utilisateur.

        Args:
            user_input (str): Question ou entrée de l'utilisateur.
            first_name (str): Prénom de l'utilisateur.
            last_name (str): Nom de l'utilisateur.
            code_client (str): Code client de l'utilisateur.
            debtor_data (pd.DataFrame): Données des débiteurs.

        Returns:
            str: Réponse générée par le chatbot.
        """
        try:
            user = verify_user(first_name, last_name, code_client, debtor_data)
            if user is not None:
                user_key = f"{first_name}_{last_name}_{code_client}"
                self.memory[user_key] = user.to_dict('records')[0]
                self.manage_memory(user_key)
                response_template = self.find_response_template(user_input)
                if response_template:
                    response = self.fill_template(response_template, self.memory[user_key], user_input)
                    return response
                else:
                    logging.warning("Aucun template de réponse trouvé pour l'entrée utilisateur.")
                    return "Désolé, je ne suis pas en mesure de trouver une réponse appropriée."
            else:
                return "Je ne trouve pas vos informations dans notre base de données."
        except Exception as e:
            logging.error(f"Une erreur est survenue lors de la génération de la réponse: {e}")
            return f"Une erreur est survenue lors de la génération de la réponse: {e}"

    def find_response_template(self, prompt):
        """
        Recherche le template de réponse correspondant à l'entrée utilisateur.

        Args:
            prompt (str): Entrée utilisateur.

        Returns:
            str or None: Template de réponse trouvé ou None si aucun template n'est trouvé.
        """
        try:
            inputs = tokenizer(prompt, return_tensors="tf")
            outputs = model(**inputs)
            user_input_embedding = outputs.last_hidden_state[:, 0, :].numpy().reshape(1, -1)
            D, I = self.vector_db.search(user_input_embedding, k=1)
            if I[0][0] != -1:
                response_template = self.metadata[I[0][0]]['response']
                return response_template
            else:
                return None
        except Exception as e:
            logging.error(f"Erreur lors de la recherche du template de réponse: {e}")
            return None
   
    def fill_template(self, template, user, user_input):
        """
        Remplit le template de réponse avec les données de l'utilisateur.

        Args:
            template (str): Template de réponse à compléter.
            user (dict): Données de l'utilisateur.
            user_input (str): Entrée utilisateur.

        Returns:
            str: Réponse générée après remplissage du template.
        """
        response = template
        try:
            if any(keyword in user_input.lower() for keyword in ["téléphone", "telephone", "numero", "numero de telephone", "phone", "numéro de téléphone", "phone number", "contact my account manager", "contacter mon gestionnaire"]):
                response = "Le numéro de téléphone de votre gestionnaire de compte est {telephone_gestionnaire_amiable}.".format(
                    telephone_gestionnaire_amiable=user['telephone_gestionnaire_amiable'])
            elif any(keyword in user_input.lower() for keyword in ["gestionnaire", "responsable", "responsable du dossier", "qui est mon gestionnaire", "dossier"]):
                response = "Votre gestionnaire de dossier est {prenom_gestionnaire_amiable} {nom_gestionnaire_amiable}. Vous pouvez le joindre au {telephone_gestionnaire_amiable}.".format(
                    prenom_gestionnaire_amiable=user['prenom_gestionnaire_amiable'],
                    nom_gestionnaire_amiable=user['nom_gestionnaire_amiable'],
                    telephone_gestionnaire_amiable=user['telephone_gestionnaire_amiable'])
            elif any(keyword in user_input.lower() for keyword in ["account manager", "corporate account", "manager", "call to pay"]):
                response = "Your account manager is {prenom_gestionnaire_amiable} {nom_gestionnaire_amiable}. You can reach him by calling {telephone_gestionnaire_amiable}.".format(
                    prenom_gestionnaire_amiable=user['prenom_gestionnaire_amiable'],
                    nom_gestionnaire_amiable=user['nom_gestionnaire_amiable'],
                    telephone_gestionnaire_amiable=user['telephone_gestionnaire_amiable'])
            elif any(keyword in user_input.lower() for keyword in ["argent", "somme", "payer", "demande", "dette"]):
                response = response.replace(',,,,,', str(user['decompte_total_solde']), 1)
                response = response.replace(',,,,,', user['raison_sociale_client'], 1)
            elif any(keyword in user_input.lower() for keyword in ["money", "amount", "sums", "pay", "request"]):
                response = response.replace(',,,,,', user['raison_sociale_client'], 1)
                response = response.replace(',,,,,', str(user['decompte_total_solde']), 1)
            elif any(keyword in user_input.lower() for keyword in ["créancier", "créditeur", "creancier", "crediteur", "salle de sport", "salle", "creditor", "gym"]):
                response = response.replace('Mettre le nom commercial du client orange bleue', user['raison_sociale_client'])
            elif any(keyword in user_input.lower() for keyword in ["au revoir", "bonne soirée"]):
                response = "Au revoir ! Passez une bonne journée !"
            return response
        except Exception as e:
            logging.error(f"Erreur lors du remplissage du template: {e}")
            return "Une erreur est survenue lors de la préparation de votre réponse."

# Initialiser le chatbot
cap_chatbot = CAPRecouvrementChatBot(vector_db, metadata)
