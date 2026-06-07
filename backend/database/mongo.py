import pymongo
from datetime import datetime

# Initialize MongoDB Client
MONGO_URI = "mongodb://localhost:27017/"
client = pymongo.MongoClient(MONGO_URI)
db = client["socialcue"]

# Collections
users_collection = db["users"]
logs_collection = db["logs"]
commands_collection = db["commands"]
settings_collection = db["settings"]

def init_db():
    """Initialize default settings if they don't exist"""
    if settings_collection.count_documents({}) == 0:
        settings_collection.insert_one({
            "voice_speed": 150,
            "threshold": 0.5,
            "selected_voice": "female"
        })

def add_user(name, relation, image_path):
    user = {
        "name": name.lower(),
        "relation": relation,
        "image_path": image_path,
        "embedding": [], # Placeholder for actual deepface embeddings
        "created_at": datetime.now(),
        "visit_count": 1,
        "last_seen": datetime.now(),
        "conversations": []
    }
    users_collection.update_one(
        {"name": name.lower()},
        {"$set": user},
        upsert=True
    )
    return user

def get_user(name):
    return users_collection.find_one({"name": name.lower()})

def update_user_visit(name):
    users_collection.update_one(
        {"name": name.lower()},
        {
            "$inc": {"visit_count": 1},
            "$set": {"last_seen": datetime.now()}
        }
    )

def log_interaction(name, relation, status, confidence=1.0):
    log = {
        "timestamp": datetime.now(),
        "person_name": name,
        "relation": relation,
        "confidence": confidence,
        "status": status
    }
    logs_collection.insert_one(log)

def log_command(command, result):
    cmd = {
        "command": command,
        "timestamp": datetime.now(),
        "result": result
    }
    commands_collection.insert_one(cmd)

def get_all_users():
    return list(users_collection.find({}, {"_id": 0}))

def get_logs():
    return list(logs_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(100))

def get_settings():
    setting = settings_collection.find_one({}, {"_id": 0})
    if not setting:
        init_db()
        return settings_collection.find_one({}, {"_id": 0})
    return setting

def update_settings(new_settings):
    settings_collection.update_one({}, {"$set": new_settings}, upsert=True)
