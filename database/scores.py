# database/scores.py
from .models import get_db
import os
from pymongo import MongoClient
from dotenv import load_dotenv
import logging

# .env faylını yükləyin
load_dotenv()

# MongoDB müştərisini yaradın (URL-i .env faylından oxuyun)
MONGODB_URI = os.getenv('MONGODB_URI')
client = MongoClient(MONGODB_URI)

# Verilənlər bazası adını .env faylından oxuyun
DB_NAME = os.getenv('DB_NAME')
if not DB_NAME:
    raise ValueError("DB_NAME mühit dəyişəni təyin edilməyib.")

db = client[DB_NAME]

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_user_group_info(user_id, group_id):
    user_group_info = db.user_groups.find_one({
        'user_id': user_id,
        'group_id': group_id
    })

    if user_group_info:
        return {
            'correct_answers': user_group_info.get('correct_answers', 0),
            'host_count': user_group_info.get('host_count', 0),
            'rank': get_group_rank(user_id, group_id),
            'total_score': user_group_info.get('score', 0)
        }
    else:
        return None

def get_user_global_info(user_id):
    user_global_info = db.user_groups.aggregate([
        {'$match': {'user_id': user_id}},
        {
            '$group': {
                '_id': '$user_id',
                'correct_answers': {'$sum': '$correct_answers'},
                'host_count': {'$sum': '$host_count'},
                'total_score': {'$sum': '$score'}
            }
        }
    ])

    user_global_info = list(user_global_info)
    if user_global_info:
        return {
            'correct_answers': user_global_info[0].get('correct_answers', 0),
            'host_count': user_global_info[0].get('host_count', 0),
            'rank': get_global_rank(user_id),
            'total_score': user_global_info[0].get('total_score', 0)
        }
    else:
        return None

def get_group_rank(user_id, group_id):
    scores = db.user_groups.find({'group_id': group_id}).sort('score', -1)
    rank = 1
    for score in scores:
        if score['user_id'] == user_id:
            return rank
        rank += 1
    return rank

def get_global_rank(user_id):
    scores = db.user_groups.aggregate([
        {
            '$group': {
                '_id': '$user_id',
                'total_score': {'$sum': '$score'}
            }
        },
        {'$sort': {'total_score': -1}}
    ])
    rank = 1
    for score in scores:
        if score['_id'] == user_id:
            return rank
        rank += 1
    return rank


def update_scores(user_id, first_name, group_id, group_name, points=1):
    db = get_db()

    # Update user score
    db.users.update_one(
        {'user_id': user_id},
        {
            '$set': {'first_name': first_name},
            '$inc': {'totalScore': points}
        },
        upsert=True
    )

    # Update group score
    db.groups.update_one(
        {'group_id': group_id},
        {
            '$set': {'groupName': group_name},
            '$inc': {'totalScore': points}
        },
        upsert=True
    )

    # Update user-group relationship
    db.user_groups.update_one(
        {
            'user_id': user_id,
            'group_id': group_id
        },
        {
            '$inc': {'score': points},
            '$set': {
                'first_name': first_name,
                'groupName': group_name
            }
        },
        upsert=True
    )


def get_top_groups(limit=25):
    db = get_db()
    try:
        groups = list(db.groups.find(
            {},
            {'_id': 0, 'group_id': 1, 'groupName': 1, 'totalScore': 1}
        ).sort('totalScore', -1).limit(limit))
        logger.info(f"Top groups fetched successfully.")
        return groups
    except Exception as e:
        logger.error(f"Error fetching top groups: {e}")
        return []

def get_group_top_users(group_id, limit=25):
    db = get_db()
    try:
        users = list(db.user_groups.find(
            {'group_id': group_id},
            {'_id': 0, 'user_id': 1, 'first_name': 1, 'score': 1}
        ).sort('score', -1).limit(limit))
        logger.info(f"Top users for group {group_id} fetched successfully.")
        return users
    except Exception as e:
        logger.error(f"Error fetching top users for group {group_id}: {e}")
        return []

def get_top_users(limit=25):
    db = get_db()
    try:
        users = list(db.users.find(
            {},
            {'_id': 0, 'user_id': 1, 'first_name': 1, 'totalScore': 1}
        ).sort('totalScore', -1).limit(limit))
        logger.info(f"Top users fetched successfully.")
        return users
    except Exception as e:
        logger.error(f"Error fetching top users: {e}")
        return []
