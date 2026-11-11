import os

# Test configuration must be in place before config.py is imported.
# These override anything in a local .env (load_dotenv never overrides).
os.environ.update({
    "DATABASE_URL": "mongodb://test-host/",
    "DATABASE_NAME": "fast_read_test",
    "SECRET_KEY": "test-secret-key-not-used-anywhere-else-0123456789",
    "EMAIL_SENDER": "sender@test.invalid",
    "EMAIL_PASSWORD": "test-password",
    "CONTACT_EMAIL": "contact@test.invalid",
    "CORS_ORIGINS": "http://localhost:3000",
    "SERVER_IP": "http://localhost:5000/",
    "FLASK_DEBUG": "false",
})

import mongomock
import pytest

import db.db as db_module

db_module.client_factory = mongomock.MongoClient
db_module.reset_clients()

import app as app_module  # noqa: E402  (must follow the patches above)
import const  # noqa: E402
from jwtgenerate import JWT_Token  # noqa: E402


@pytest.fixture
def mongo():
    database = db_module.get_client(os.environ["DATABASE_URL"])[os.environ["DATABASE_NAME"]]
    for name in database.list_collection_names():
        database.drop_collection(name)
    yield database
    for name in database.list_collection_names():
        database.drop_collection(name)


@pytest.fixture
def client(mongo):
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def student_token(mongo):
    mongo.users.insert_one({"user_name": "ali", "user_type": const.student, "activate": True,
                            "level": 1, "teacher_name": "teacher1", "password": "x"})
    return JWT_Token().generate_token(user_id=None, role=const.student, name="Ali", user_name="ali", level=1)


@pytest.fixture
def admin_token(mongo):
    mongo.users.insert_one({"user_name": "admin", "user_type": const.admin, "password": "x"})
    return JWT_Token().generate_token_teacher(user_id=None, role=const.admin, name="Admin", user_name="admin")


@pytest.fixture
def teacher_token(mongo):
    mongo.users.insert_one({"user_name": "teacher1", "user_type": const.teacher, "password": "x"})
    return JWT_Token().generate_token_teacher(user_id=None, role=const.teacher, name="T", user_name="teacher1")
