import pymongo

class MongoDB:
    def __init__(self, url, db_name):
        self.client = pymongo.MongoClient(url)
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

    def count_documents(self, collection_name, query):
        collection = self.db[collection_name]
        count = collection.count_documents(query)
        return count
    

