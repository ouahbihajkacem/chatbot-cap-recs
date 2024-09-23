# CAP Recouvrement Chatbot

## Description
Le CAP Recouvrement Chatbot est un projet développé pour faciliter l'interaction avec les débiteurs de CAP Recouvrement. Ce chatbot est capable de répondre aux questions des utilisateurs en utilisant un modèle NLP basé sur Transformers.

## Fonctionnalités
- Vérification de l'identité de l'utilisateur à partir des données des débiteurs.
- Réponse automatique aux questions basées sur un ensemble prédéfini de questions-réponses et des réponses personnalisées.
- Mémoire utilisateur gérée avec une stratégie LRU.
- API FastAPI pour intégrer le chatbot avec un frontend.
- Interface utilisateur avec Streamlit pour faciliter les interactions.

## Technologies Utilisées
- Python
- Pandas
- TensorFlow et Transformers pour l'IA/NLP
- FAISS pour la recherche vectorielle
- Streamlit pour l'interface utilisateur
- FastAPI pour l'API backend
- Redis pour la gestion des sessions
- Logging pour le suivi des interactions et des erreurs

## Prérequis
- Python 3.8 ou supérieur
- Redis en cours d'exécution

## Installation
1. Clonez le repository:
   ```bash
   git clone https://votre-repo-git
   cd votre-repo

2. Installez les dépendances:
pip install -r requirements.txt

3. Exécutez l'application Streamlit:
streamlit run app.py

4. Exécutez l'API FastAPI:
uvicorn main:app --reload

## Utilisation
- Une fois que l'application est lancée, vous pouvez accéder à l'interface utilisateur via votre navigateur.
- Le chatbot vous demandera de vous identifier avant de poser des questions.

## Exemples 
Voici quelques exemples de questions que vous pouvez poser :
- "Qui est mon gestionnaire de dossier ?"
- "A qui dois-je de l'argent ?"
- "Qui est mon créditeur ?"