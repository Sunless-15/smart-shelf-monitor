"""Database layer with MongoDB support and an automatic In-Memory/JSON fallback.

If MongoDB is unreachable, the system automatically uses an in-memory store
persisted to backend/data/fallback_store.json with a warning flag, allowing
the application to function seamlessly offline.
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import Config

logger = logging.getLogger(__name__)

def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert MongoDB ObjectId or non-serializable types into serializable values."""
    if doc is None:
        return None
    d = dict(doc)
    if "_id" in d:
        str_id = str(d["_id"])
        d["_id"] = str_id
        if "id" not in d or not d["id"]:
            d["id"] = str_id
        # Also ensure string id
        d["id"] = str(d["id"])
    return d

def serialize_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Serialize a list of database documents."""
    return [serialize_doc(d) for d in docs]

def id_filter(id_val: Any) -> Dict[str, Any]:
    """Create a query filter matching either string id, string _id, or ObjectId."""
    str_val = str(id_val).strip()
    conditions = [{"id": str_val}, {"_id": str_val}]
    if ObjectId.is_valid(str_val):
        conditions.append({"_id": ObjectId(str_val)})
    return {"$or": conditions}


class FallbackCollection:
    """In-memory collection emulation with JSON file persistence."""

    def __init__(self, name: str, parent_db: "FallbackDB"):
        self.name = name
        self.parent = parent_db

    @property
    def data(self) -> List[Dict[str, Any]]:
        return self.parent.tables.setdefault(self.name, [])

    def _matches(self, doc: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        if not filter_dict:
            return True
        if "$or" in filter_dict and isinstance(filter_dict["$or"], list):
            return any(self._matches(doc, sub) for sub in filter_dict["$or"])
        for key, value in filter_dict.items():
            doc_val = doc.get(key)
            if key in ("_id", "id"):
                if str(doc.get("_id", doc.get("id"))) != str(value):
                    return False
            elif isinstance(value, dict):
                # Simple operator support ($gte, $lte, $gt, $lt, $ne, $in)
                for op, op_val in value.items():
                    if op == "$gte" and not (doc_val is not None and doc_val >= op_val):
                        return False
                    elif op == "$lte" and not (doc_val is not None and doc_val <= op_val):
                        return False
                    elif op == "$gt" and not (doc_val is not None and doc_val > op_val):
                        return False
                    elif op == "$lt" and not (doc_val is not None and doc_val < op_val):
                        return False
                    elif op == "$ne" and doc_val == op_val:
                        return False
                    elif op == "$in" and doc_val not in op_val:
                        return False
            elif doc_val != value:
                return False
        return True

    def find(self, filter_dict: Optional[Dict[str, Any]] = None, sort=None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        filter_dict = filter_dict or {}
        matches = [dict(doc) for doc in self.data if self._matches(doc, filter_dict)]
        
        if sort:
            # sort format: [("field", 1 or -1)]
            for field, order in reversed(sort):
                matches.sort(
                    key=lambda d: d.get(field, 0) or 0, 
                    reverse=(order == -1)
                )
                
        if limit and limit > 0:
            matches = matches[:limit]
        return matches

    def find_one(self, filter_dict: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        results = self.find(filter_dict, limit=1)
        return results[0] if results else None

    def insert_one(self, doc: Dict[str, Any]):
        new_doc = dict(doc)
        if "_id" not in new_doc:
            new_id = str(uuid.uuid4())
            new_doc["_id"] = new_id
            new_doc["id"] = new_id
        else:
            new_doc["id"] = str(new_doc["_id"])
            new_doc["_id"] = str(new_doc["_id"])
            
        self.data.append(new_doc)
        self.parent.save()
        
        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
        return InsertResult(new_doc["_id"])

    def update_one(self, filter_dict: Dict[str, Any], update_dict: Dict[str, Any], upsert: bool = False):
        existing = self.find_one(filter_dict)
        matched_count = 1 if existing else 0
        modified_count = 0
        
        if existing:
            # Apply $set or direct update
            set_vals = update_dict.get("$set", update_dict)
            for doc in self.data:
                if self._matches(doc, filter_dict):
                    doc.update(set_vals)
                    modified_count += 1
                    break
            self.parent.save()
        elif upsert:
            new_doc = dict(filter_dict)
            set_vals = update_dict.get("$set", update_dict)
            new_doc.update(set_vals)
            self.insert_one(new_doc)
            modified_count = 1
            
        class UpdateResult:
            def __init__(self, matched, modified):
                self.matched_count = matched
                self.modified_count = modified
        return UpdateResult(matched_count, modified_count)

    def delete_one(self, filter_dict: Dict[str, Any]):
        initial_len = len(self.data)
        for i, doc in enumerate(self.data):
            if self._matches(doc, filter_dict):
                del self.data[i]
                self.parent.save()
                break
        deleted_count = initial_len - len(self.data)
        
        class DeleteResult:
            def __init__(self, count):
                self.deleted_count = count
        return DeleteResult(deleted_count)

    def count_documents(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        return len(self.find(filter_dict))


class FallbackDB:
    """Manages JSON file-backed collections when MongoDB is unavailable."""

    def __init__(self, file_path: str = None):
        self.file_path = file_path or str(Config.DATA_DIR / "fallback_store.json")
        self.tables: Dict[str, List[Dict[str, Any]]] = {}
        self.load()

    def load(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.tables = json.load(f)
        except Exception:
            self.tables = {}

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.tables, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving fallback store: {e}")

    def __getitem__(self, name: str) -> FallbackCollection:
        return FallbackCollection(name, self)


class Database:
    """Database interface with automatic MongoDB connection & graceful fallback."""

    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db = None
        self.is_fallback: bool = False
        self.warning: Optional[str] = None
        self._init_connection()
        self._seed_default_zones()

    def _init_connection(self):
        try:
            logger.info(f"Attempting connection to MongoDB at {Config.MONGO_URI}...")
            self.client = MongoClient(
                Config.MONGO_URI,
                serverSelectionTimeoutMS=Config.MONGO_TIMEOUT_MS,
                connectTimeoutMS=Config.MONGO_TIMEOUT_MS,
            )
            # Test ping
            self.client.admin.command("ping")
            self.db = self.client[Config.DB_NAME]
            self.is_fallback = False
            self.warning = None
            logger.info("Successfully connected to local MongoDB.")
        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
            self.is_fallback = True
            self.warning = (
                f"MongoDB connection failed ({e.__class__.__name__}: {e}). "
                "Running in Fallback Mode (In-Memory/JSON store active)."
            )
            logger.warning(self.warning)
            self.db = FallbackDB()

    def _seed_default_zones(self):
        """Seed initial shelf zones if collection is empty."""
        try:
            zones_col = self.get_collection("zones")
            count = zones_col.count_documents({})
            if count == 0:
                default_zones = [
                    {
                        "name": "Zone A - Top Left",
                        "expected_class": "bottle",
                        "full_count": 4,
                        "low_threshold": 0.35,
                        "coords": {"x1": 0.08, "y1": 0.12, "x2": 0.46, "y2": 0.48},
                        "created_at": time.time(),
                    },
                    {
                        "name": "Zone B - Top Right",
                        "expected_class": "cup",
                        "full_count": 4,
                        "low_threshold": 0.35,
                        "coords": {"x1": 0.54, "y1": 0.12, "x2": 0.92, "y2": 0.48},
                        "created_at": time.time(),
                    },
                    {
                        "name": "Zone C - Bottom Shelf",
                        "expected_class": "bottle",
                        "full_count": 6,
                        "low_threshold": 0.35,
                        "coords": {"x1": 0.15, "y1": 0.58, "x2": 0.85, "y2": 0.92},
                        "created_at": time.time(),
                    },
                ]
                for z in default_zones:
                    zones_col.insert_one(z)
                logger.info(f"Seeded {len(default_zones)} default shelf zones.")
        except Exception as e:
            logger.error(f"Failed to seed default zones: {e}")

    def get_collection(self, name: str):
        """Return collection object (either PyMongo Collection or FallbackCollection)."""
        return self.db[name]

    @property
    def zones(self):
        return self.get_collection("zones")

    @property
    def alerts(self):
        return self.get_collection("alerts")

    @property
    def history(self):
        return self.get_collection("history")

    @property
    def jobs(self):
        return self.get_collection("jobs")

    @property
    def settings(self):
        return self.get_collection("settings")

    def get_status(self) -> Dict[str, Any]:
        """Return current database connection status."""
        return {
            "connected": True,
            "status": "fallback" if self.is_fallback else "connected",
            "type": "in_memory_fallback" if self.is_fallback else "mongodb",
            "database_name": Config.DB_NAME,
            "warning": self.warning,
        }

# Global database instance
db = Database()
