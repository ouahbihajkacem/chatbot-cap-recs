import faiss
import numpy as np
from transformers import AutoTokenizer, TFAutoModel
from data_loader import qa_pairs
import os

# Charger le modèle de transformers
tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
model = TFAutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')

INDEX_FILE_PATH = "faiss_index.bin"
METADATA_FILE_PATH = "metadata.npy"

def create_vector_db(qa_pairs, batch_size=32):
    """
    Crée une base de données vectorielle pour les paires de questions-réponses.

    Args:
        qa_pairs (list): Liste de paires de questions-réponses.
        batch_size (int, optional): Taille du batch pour l'embedding des questions. Par défaut 32.

    Returns:
        tuple: (index, metadata) où index est l'index FAISS et metadata est la liste des métadonnées.
    """
    embeddings = []
    metadata = []
   
    for i in range(0, len(qa_pairs), batch_size):
        batch = qa_pairs[i:i+batch_size]
        batch_questions = [q[0] for q in batch]
        inputs = tokenizer(batch_questions, return_tensors="tf", padding=True, truncation=True)
        outputs = model(**inputs)
        question_embeddings = outputs.last_hidden_state[:, 0, :].numpy()
        embeddings.extend(question_embeddings)
        for question, response in batch:
            metadata.append({'question': question, 'response': response})
   
    embeddings = np.array(embeddings).astype('float32')
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
   
    # Sauvegarder l'index et les metadata
    faiss.write_index(index, INDEX_FILE_PATH)
    np.save(METADATA_FILE_PATH, metadata)
   
    return index, metadata

def load_vector_db():
    """
    Charge la base de données vectorielle à partir du disque ou la crée si elle n'existe pas.

    Returns:
        tuple: (index, metadata) où index est l'index FAISS et metadata est la liste des métadonnées.
    """
    if os.path.exists(INDEX_FILE_PATH) and os.path.exists(METADATA_FILE_PATH):
        index = faiss.read_index(INDEX_FILE_PATH)
        metadata = np.load(METADATA_FILE_PATH, allow_pickle=True).tolist()
        return index, metadata
    else:
        return create_vector_db(qa_pairs)

# Charger ou créer l'index et les metadata
vector_db, metadata = load_vector_db()
