"""Index definitions for every collection the API queries.

Idempotent: run it after each deploy or schema change.

    python -m db.indexes
"""
from pymongo import ASCENDING

# collection -> list of (keys, options)
INDEXES = {
    "users": [
        ([("user_name", ASCENDING)], {"unique": True}),
        # Password reset looks users up by email.
        ([("email", ASCENDING)], {}),
        # Student lists and counts, optionally narrowed to one teacher.
        ([("user_type", ASCENDING), ("teacher_name", ASCENDING)], {}),
        ([("teacher_name", ASCENDING)], {}),
    ],
    "process": [
        ([("user_name", ASCENDING)], {}),
    ],
    "days": [
        ([("day", ASCENDING), ("level", ASCENDING)], {"unique": True}),
    ],
    "exercise": [
        ([("name", ASCENDING), ("level", ASCENDING)], {"unique": True}),
    ],
    "after_exercise": [
        ([("user_name", ASCENDING), ("exercise_name", ASCENDING)], {}),
    ],
    "messages": [
        ([("receiver", ASCENDING), ("teacher_scope", ASCENDING)], {}),
        # Legacy documents address the recipient through "user_name".
        ([("user_name", ASCENDING)], {}),
        ([("sender", ASCENDING)], {}),
        ([("id", ASCENDING)], {}),
    ],
    "task": [
        ([("who", ASCENDING), ("task_id", ASCENDING)], {}),
    ],
    "knowledge": [
        ([("id", ASCENDING)], {}),
        ([("publish", ASCENDING)], {}),
    ],
    "videos": [
        ([("name", ASCENDING)], {}),
        # Legacy documents store the name as "video_name".
        ([("video_name", ASCENDING)], {}),
    ],
    "update_password": [
        ([("email", ASCENDING)], {}),
        # Matches RESET_CODE_TTL in app.py: expired codes are removed.
        ([("created_at", ASCENDING)], {"expireAfterSeconds": 600}),
    ],
}


def ensure_indexes(database):
    """Create every missing index; return the names per collection."""
    created = {}
    for collection_name, specs in INDEXES.items():
        collection = database[collection_name]
        created[collection_name] = [
            collection.create_index(keys, **options) for keys, options in specs
        ]
    return created


if __name__ == "__main__":
    import pymongo

    import config

    client = pymongo.MongoClient(config.DATABASE_URL)
    for name, index_names in ensure_indexes(client[config.DATABASE_NAME]).items():
        print(name, index_names)
