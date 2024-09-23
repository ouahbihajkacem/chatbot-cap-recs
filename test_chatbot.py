import unittest
from chatbot import CAPRecouvrementChatBot, verify_user
from data_loader import debtor_data
from indexer import vector_db, metadata

class TestChatBot(unittest.TestCase):
   
    def setUp(self):
        self.chatbot = CAPRecouvrementChatBot(vector_db, metadata)

    def test_verify_user(self):
        # Utilisateur existant (vérifions que ces données existent dans notre fichier Excel)
        user = verify_user('bis', 'dossier test', '100', debtor_data)
        self.assertIsNotNone(user)
       
        # Utilisateur inexistant
        user = verify_user('fake', 'user', '00000', debtor_data)
        self.assertIsNone(user)

    def test_find_response_template(self):
        response = self.chatbot.find_response_template("Qui est mon gestionnaire de dossier?")
        self.assertIsNotNone(response)

    def test_get_response(self):
        response = self.chatbot.get_response("Qui est mon gestionnaire de dossier?", "bis", "dossier test", "100", debtor_data)
        self.assertIn("gestionnaire de dossier", response)

    def test_get_response_no_user(self):
        response = self.chatbot.get_response("Qui est mon gestionnaire de dossier?", "fake", "user", "00000", debtor_data)
        self.assertEqual(response, "Je ne trouve pas vos informations dans notre base de données.")

    def test_memory_management(self):
        # Tester la gestion de la mémoire pour s'assurer que les anciens utilisateurs sont supprimés correctement
        for i in range(101):
            self.chatbot.get_response(f"Question {i}", "first_name", "last_name", str(i), debtor_data)
        self.assertEqual(len(self.chatbot.memory), 100)  # Limite fixée à 100

if __name__ == '__main__':
    unittest.main()
