from pymongo import MongoClient
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class Database:
    _instance = None

    def __init__(self):
        load_dotenv()
        self.client = None
        self.db = None
        self.connect()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def connect(self):
        try:
            mongodb_uri = os.getenv('MONGODB_URI')
            db_name = os.getenv('DB_NAME', 'wordgame')

            if not mongodb_uri:
                raise ValueError("MONGODB_URI environment variable is not set")

            self.client = MongoClient(mongodb_uri)
            self.db = self.client[db_name]

            # Create indexes
            self.db.users.create_index('user_id', unique=True)
            self.db.groups.create_index('group_id', unique=True)
            self.db.user_groups.create_index([('user_id', 1), ('group_id', 1)], unique=True)

            logger.info("Successfully connected to MongoDB")
            return self.db

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise Exception(f"MongoDB connection failed: {str(e)}")

    def get_db(self):
        if self.db is None:  # MongoDB bağlantısını yoxlayırıq
            logger.warning("MongoDB connection is None. Reconnecting...")
            self.connect()  # Əgər əlaqə yoxdursa, yenidən əlaqə qururuq
        return self.db


def get_db():
    return Database.get_instance().get_db()