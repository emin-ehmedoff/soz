# database/scores.py
from .models import get_db

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

def get_top_users(limit=25):
    db = get_db()
    return list(db.users.find(
        {},
        {'_id': 0, 'user_id': 1, 'first_name': 1, 'totalScore': 1}
    ).sort('totalScore', -1).limit(limit))

def get_top_groups(limit=25):
    db = get_db()
    return list(db.groups.find(
        {},
        {'_id': 0, 'group_id': 1, 'groupName': 1, 'totalScore': 1}
    ).sort('totalScore', -1).limit(limit))

def get_group_top_users(group_id, limit=25):
    db = get_db()
    return list(db.user_groups.find(
        {'group_id': group_id},
        {'_id': 0, 'user_id': 1, 'first_name': 1, 'score': 1}
    ).sort('score', -1).limit(limit))