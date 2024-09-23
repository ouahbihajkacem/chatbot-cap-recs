import pandas as pd
import logging
from cryptography.fernet import Fernet
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Charger la clé de chiffrement depuis une variable d'environnement
key = os.getenv('ENCRYPTION_KEY')
if not key:
    raise ValueError("La clé de chiffrement n'est pas définie. Veuillez la définir dans la variable d'environnement 'ENCRYPTION_KEY'.")
else:
    # Si la clé est une chaîne de caractères, convertir en bytes
    if isinstance(key, str):
        key = key.encode()

cipher_suite = Fernet(key)

def encrypt_data(data):
    """
    Chiffrer les données avant de les stocker.
    """
    json_data = json.dumps(data).encode('utf-8')
    encrypted_data = cipher_suite.encrypt(json_data)
    return encrypted_data

def decrypt_data(encrypted_data):
    """
    Déchiffrer les données pour utilisation.
    """
    decrypted_data = cipher_suite.decrypt(encrypted_data)
    return json.loads(decrypted_data)

def validate_debtor_data(data):
    """
    Valide que les colonnes nécessaires sont présentes dans le fichier Excel.

    Args:
        data (pd.DataFrame): Les données chargées à partir du fichier Excel.

    Raises:
        ValueError: Si une colonne requise est manquante.
    """
    required_columns = ['prenom_debiteur', 'nom_debiteur', 'code_client']
    for col in required_columns:
        if col not in data.columns:
            raise ValueError(f"Le fichier Excel ne contient pas la colonne requise: {col}")

def load_excel_data(file_path):
    """
    Charge les données d'un fichier Excel et valide les colonnes nécessaires.

    Args:
        file_path (str): Chemin vers le fichier Excel.

    Returns:
        pd.DataFrame: Les données chargées ou None si une erreur s'est produite.
    """
    try:
        data = pd.read_excel(file_path)
        if data is None or data.empty:
            logging.error(f"Le fichier Excel {file_path} est vide ou n'a pas été chargé correctement.")
            return None
        validate_debtor_data(data)
        return data
    except FileNotFoundError:
        logging.error(f"Le fichier Excel {file_path} n'existe pas.")
        return None
    except ValueError as ve:
        logging.error(f"Erreur de validation: {ve}")
        return None
    except Exception as e:
        logging.error(f"Erreur lors du chargement du fichier Excel: {e}")
        return None

def load_chatbot_data(file_path):
    """
    Charge les données de question-réponse pour le chatbot à partir d'un fichier texte.

    Args:
        file_path (str): Chemin vers le fichier texte.

    Returns:
        list: Liste de paires question-réponse ou None si une erreur s'est produite.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            qa_pairs = [line.strip().split('::') for line in file.readlines() if '::' in line]
            for pair in qa_pairs:
                if len(pair) != 2:
                    raise ValueError("Chaque ligne doit contenir exactement une question et une réponse séparées par '::'")
            return qa_pairs
    except Exception as e:
        logging.error(f"Erreur lors du chargement du fichier de chatbot: {e}")
        return None

# Charger les données
debtor_data = load_excel_data('data/Classeur.xlsx')
qa_pairs = load_chatbot_data('data/Data_Chatbot.txt')
