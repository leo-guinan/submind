import uuid
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
    historical_uuid = str(uuid.uuid4())
    previous_doc = db.documents.find_one({"uuid": document_uuid})

    db.document_history.insert_one({
        "uuid": historical_uuid,
        "content": previous_doc["content"],
        "createdAt": previous_doc["createdAt"],
        "documentUUID": previous_doc["uuid"]
    })
    db.documents.update_one({"uuid": document_uuid}, {"$set": {"content": content, "previousVersion": historical_uuid, "updatedAt": datetime.now()}})

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

def create_report(user_id, content, uuid):
    mongo_client = MongoClient(config('MONGODB_CONNECTION_STRING'))
    db = mongo_client.myaicofounder
    new_report = {
        "userId": user_id,
        "content": content,
        "uuid": uuid,
        "createdAt": datetime.now()
    }
    db.reports.insert_one(new_report)
    return new_report

def get_or_create_document(user_id, content, uuid):
    mongo_client = MongoClient(config('MONGODB_CONNECTION_STRING'))
    db = mongo_client.myaicofounder
    existing_doc = db.documents.find_one({"userId": user_id, "uuid": uuid})
    if existing_doc:
        return existing_doc
    else:
        new_doc = {
            "userId": user_id,
            "content": content,
            "uuid": uuid,
            "createdAt": datetime.now()
        }
        db.documents.insert_one(new_doc)
        return new_doc