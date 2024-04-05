from datetime import datetime

from decouple import config
from pymongo import MongoClient


def get_document(document_uuid, user_id):
    mongo_client = MongoClient(config('MONGODB_CONNECTION_STRING'))
    db = mongo_client.myaicofounder
    return db.documents.find_one({"uuid": document_uuid, "userId": user_id})

def update_document(document_uuid, content):
    mongo_client = MongoClient(config('MONGODB_CONNECTION_STRING'))
    db = mongo_client.myaicofounder
    db.documents.update_one({"uuid": document_uuid}, {"$set": {"content": content}})

def create_document(user_id, content, uuid):
    mongo_client = MongoClient(config('MONGODB_CONNECTION_STRING'))
    db = mongo_client.myaicofounder
    new_doc = {
        "userId": user_id,
        "content": content,
        "uuid": uuid,
        "createdAt": datetime.now()
    }
    db.documents.insert_one(new_doc)
    return new_doc