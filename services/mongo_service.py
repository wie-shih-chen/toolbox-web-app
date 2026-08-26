import os
import logging
import requests

class DataApiCursor:
    def __init__(self, coll, query, projection=None):
        self.coll = coll
        self.query = query
        self.projection = projection
        self._skip = 0
        self._limit = 10000
    
    def skip(self, s):
        self._skip = s
        return self
        
    def limit(self, l):
        self._limit = l
        return self
        
    def __iter__(self):
        payload = {"filter": self.query, "limit": self._limit, "skip": self._skip}
        if self.projection:
            payload["projection"] = self.projection
            
        res = self.coll._post("find", payload)
        docs = res.get('documents', []) if res else []
        return iter(docs)

class DataApiCollection:
    def __init__(self, url, api_key, cluster, database, collection):
        # Clean up URL to ensure it doesn't end with slash or /action
        if url.endswith('/'):
            url = url[:-1]
        if url.endswith('/action'):
            url = url[:-7]
            
        self.url = url
        self.api_key = api_key
        self.cluster = cluster
        self.database = database
        self.collection = collection
        self.headers = {
            'Content-Type': 'application/json',
            'Access-Control-Request-Headers': '*',
            'api-key': self.api_key
        }
        self.base_payload = {
            "dataSource": self.cluster,
            "database": self.database,
            "collection": self.collection
        }
    
    def _post(self, endpoint, payload):
        action_url = f"{self.url}/action/{endpoint}"
        data = {**self.base_payload, **payload}
        try:
            res = requests.post(action_url, headers=self.headers, json=data, timeout=10)
            if res.status_code == 200:
                return res.json()
            else:
                logging.error(f"Data API Error {res.status_code}: {res.text}")
                return None
        except Exception as e:
            logging.error(f"Data API Request Failed: {e}")
            return None

    def find_one(self, query):
        res = self._post("findOne", {"filter": query})
        return res.get('document') if res else None
    
    def find(self, query=None, projection=None):
        q = query or {}
        return DataApiCursor(self, q, projection)

    def count_documents(self, query):
        res = self._post("aggregate", {"pipeline": [{"$match": query}, {"$count": "total"}]})
        if res and res.get('documents') and len(res['documents']) > 0:
            return res['documents'][0].get('total', 0)
        return 0
        
    def estimated_document_count(self):
        return self.count_documents({})

class MongoService:
    def __init__(self):
        self.vocabulary_collection = None
        self.is_ready = False

    def init_app(self, app):
        url = os.environ.get('MONGO_DATA_API_URL')
        api_key = os.environ.get('MONGO_DATA_API_KEY')
        cluster = os.environ.get('MONGO_CLUSTER_NAME', 'Cluster0')
        
        if not url or not api_key:
            logging.warning("MONGO_DATA_API_URL or MONGO_DATA_API_KEY not set. Vocabulary data will not be available.")
            return
            
        self.vocabulary_collection = DataApiCollection(
            url=url,
            api_key=api_key,
            cluster=cluster,
            database='toeic_db',
            collection='vocabulary'
        )
        self.is_ready = True
        logging.info("Successfully configured MongoDB Data API.")

    def get_collection(self):
        if self.is_ready:
            return self.vocabulary_collection
        return None

mongo = MongoService()
