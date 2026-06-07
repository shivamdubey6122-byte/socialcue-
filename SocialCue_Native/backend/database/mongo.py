import pymongo
from datetime import datetime

MONGO_URI = "mongodb://localhost:27017/"
try:
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client["socialcue_native"]
    users_collection = db["users"]
    logs_collection = db["logs"]
    commands_collection = db["commands"]
    settings_collection = db["settings"]
except Exception as e:
    print(f"MongoDB connection warning: {e}")
    users_collection = None
    logs_collection = None
    commands_collection = None
    settings_collection = None

DEFAULT_SETTINGS = {
    "camera_source": "esp32",
    "esp32_stream_url": "http://10.81.203.182/",
    "esp32_ip": "10.81.203.182",
    "hardware_enabled": True,
    "backend_tts_enabled": True,
}


def init_db():
    if settings_collection is None:
        return
    if settings_collection.count_documents({}) == 0:
        settings_collection.insert_one(DEFAULT_SETTINGS.copy())



def get_settings():
    if settings_collection is None:
        return DEFAULT_SETTINGS.copy()
    init_db()
    doc = settings_collection.find_one({}, {"_id": 0})
    if not doc:
        return DEFAULT_SETTINGS.copy()
    merged = DEFAULT_SETTINGS.copy()
    merged.update(doc)
    return merged


def update_settings(new_settings: dict):
    if settings_collection is None:
        return False
    init_db()
    settings_collection.update_one({}, {"$set": new_settings}, upsert=True)
    return True

def get_user(name):
    if users_collection is None: return None
    return users_collection.find_one({"name": name.lower()})

def add_user(name, relation):
    if users_collection is None: return None
    user = {
        "name": name.lower(),
        "relation": relation,
        "created_at": datetime.now(),
        "visit_count": 1,
        "last_seen": datetime.now()
    }
    users_collection.update_one(
        {"name": name.lower()},
        {"$set": user},
        upsert=True
    )
    return user

def log_interaction(name, relation, status, confidence=1.0):
    if logs_collection is None: return
    logs_collection.insert_one({
        "timestamp": datetime.now(),
        "person_name": name,
        "relation": relation,
        "confidence": confidence,
        "status": status
    })

def log_command(command, result):
    if commands_collection is None: return
    commands_collection.insert_one({
        "command": command,
        "timestamp": datetime.now(),
        "result": result
    })

def get_all_users():
    if users_collection is None: return []
    return list(users_collection.find({}, {"_id": 0}))

def delete_user(name):
    if users_collection is None: return False
    res = users_collection.delete_one({"name": name.lower()})
    return res.deleted_count > 0

def update_user_relation(name, relation):
    if users_collection is None: return False
    res = users_collection.update_one(
        {"name": name.lower()},
        {"$set": {"relation": relation, "last_seen": datetime.now()}}
    )
    return res.modified_count > 0
