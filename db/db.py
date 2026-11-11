import threading

import pymongo

# MongoClient is thread-safe and maintains its own connection pool, so one
# client per URL is shared by the whole process instead of one per request.
client_factory = pymongo.MongoClient
_clients = {}
_clients_lock = threading.Lock()


def get_client(url):
    client = _clients.get(url)
    if client is None:
        with _clients_lock:
            client = _clients.get(url)
            if client is None:
                client = client_factory(url)
                _clients[url] = client
    return client


def reset_clients():
    """Drop cached clients (used by tests)."""
    with _clients_lock:
        _clients.clear()


class MongoDB:
    def __init__(self, url, db_name):
        self.client = get_client(url)
        self.db = self.client[db_name]
        
    def insert_one(self, collection_name, data):
        collection = self.db[collection_name]
        result = collection.insert_one(data)
        return result.inserted_id
        
    def find_one(self, collection_name, query):
        collection = self.db[collection_name]
        result = collection.find_one(query)
        return result
        
    def find_many(self, collection_name, query):
        collection = self.db[collection_name]
        result = collection.find(query)
        return result
        
    def update_one(self, collection_name, query, data):
        collection = self.db[collection_name]
        result = collection.update_one(query, {"$set": data})
        return result.modified_count
        
    def delete_one(self, collection_name, query):
        collection = self.db[collection_name]
        result = collection.delete_one(query)
        return result.deleted_count

    def delete_many(self, collection_name, query):
        collection = self.db[collection_name]
        result = collection.delete_many(query)
        return result.deleted_count
        
    def count_documents(self, collection_name, query):
        collection = self.db[collection_name]
        count = collection.count_documents(query)
        return count
