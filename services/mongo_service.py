from pymongo import MongoClient
import logging

class MongoService:
    def __init__(self):
        self.client = None
        self.db = None
        self.vocabulary_collection = None

    def init_app(self, app):
        mongo_uri = app.config.get('MONGO_URI')
        if not mongo_uri:
            logging.warning("MONGO_URI not set. Vocabulary data will not be available.")
            return

        try:
            # Connect to MongoDB
            self.client = MongoClient(mongo_uri)
            # The database name we used during upload is 'toeic_db'
            self.db = self.client['toeic_db']
            self.vocabulary_collection = self.db['vocabulary']
            
            # Ping to test connection
            self.client.admin.command('ping')
            logging.info("Successfully connected to MongoDB Atlas for Vocabulary.")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB Atlas: {e}")
            self.client = None

    def get_collection(self):
        return self.vocabulary_collection

# Create a singleton instance
mongo = MongoService()
