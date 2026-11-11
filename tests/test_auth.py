from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

import app as app_module
import const
from jwtgenerate import JWT_Token
from passwords import is_password_hash


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _add_user(mongo, user_name, password, user_type=const.teacher, **extra):
    doc = {"user_name": user_name, "password": password, "user_type": user_type,
           "name": user_name.title(), "token": "old"}
    doc.update(extra)
    mongo.users.insert_one(doc)


# --- login -----------------------------------------------------------------

def test_login_with_hashed_password(client, mongo):
    _add_user(mongo, "teacher1", generate_password_hash("s3cret"))

    ok = client.post("/login", json={"username": "teacher1", "password": "s3cret"})
    bad = client.post("/login", json={"username": "teacher1", "password": "wrong"})

    assert ok.status_code == 200
    payload, error = JWT_Token().decode_token(ok.get_json()["token"])
    assert error is None and payload["role"] == const.teacher
    assert bad.status_code == 400


def test_login_migrates_plaintext_password(client, mongo):
    _add_user(mongo, "legacy", "plain-pass")

    first = client.post("/login", json={"username": "legacy", "password": "plain-pass"})
    stored = mongo.users.find_one({"user_name": "legacy"})["password"]
    second = client.post("/login", json={"username": "legacy", "password": "plain-pass"})
    wrong = client.post("/login", json={"username": "legacy", "password": "nope"})

    assert first.status_code == 200
    assert is_password_hash(stored) and stored != "plain-pass"
    assert second.status_code == 200
    assert wrong.status_code == 400


def test_login_rejects_operator_injection(client, mongo):
    _add_user(mongo, "teacher1", generate_password_hash("s3cret"))
    res = client.post("/login", json={"username": {"$ne": None}, "password": "s3cret"})
    assert res.status_code == 400


def test_student_login_issues_fresh_token(client, mongo):
    _add_user(mongo, "ali", generate_password_hash("pw"), user_type=const.student, activate=True, level=2)

    res = client.post("/login", json={"username": "ali", "password": "pw"})

    assert res.status_code == 200
    token = res.get_json()["token"]
    assert token != "old"
    payload, _ = JWT_Token().decode_token(token)
    assert payload["role"] == const.student and payload["level"] == 2


# --- middleware / roles ----------------------------------------------------

def test_missing_token_returns_401(client):
    assert client.get("/teacher/user").status_code == 401
    assert client.get("/student/dashboard").status_code == 401


def test_invalid_token_returns_401(client):
    assert client.get("/teacher/user", headers={"token": "garbage"}).status_code == 401


def test_cors_preflight_not_blocked(client):
    res = client.options("/teacher/user", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert res.status_code == 200
    assert res.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


def test_student_blocked_from_teacher_route(client, student_token):
    assert client.get("/teacher/user", headers={"token": student_token}).status_code == 403
    assert client.get("/teacher/messages", headers={"token": student_token}).status_code == 403


def test_teacher_blocked_from_student_route(client, admin_token):
    assert client.get("/student/dashboard", headers={"token": admin_token}).status_code == 403


def test_user_listing_hides_passwords(client, mongo, admin_token):
    _add_user(mongo, "teacher1", generate_password_hash("s3cret"))
    res = client.get("/teacher/user", headers={"token": admin_token})
    assert res.status_code == 200
    assert all("password" not in u and "token" not in u for u in res.get_json())


def test_update_user_empty_password_keeps_hash(client, mongo, admin_token):
    original = generate_password_hash("keep-me")
    _add_user(mongo, "ali", original, user_type=const.student)

    res = client.post("/teacher/updateuser/ali", headers={"token": admin_token},
                      json={"password": "", "name": "Ali Veli"})
    assert res.status_code == 200
    assert mongo.users.find_one({"user_name": "ali"})["password"] == original

    res = client.post("/teacher/updateuser/ali", headers={"token": admin_token},
                      json={"password": "new-pass"})
    stored = mongo.users.find_one({"user_name": "ali"})["password"]
    assert res.status_code == 200 and is_password_hash(stored) and stored != original


# --- password reset ----------------------------------------------------------

def _reset_body(code, password="new-pass"):
    return {"formData": {"email": "t@x.com", "password": password, "rpassword": password, "code": code}}


def test_sendcode_stores_code_with_expiry(client, mongo, monkeypatch):
    mongo.users.insert_one({"user_name": "t", "email": "t@x.com", "password": "x"})

    class FakeEmail:
        def __init__(self, **kwargs):
            self.code = "123456"

    monkeypatch.setattr(app_module, "EmailVerificationCode", FakeEmail)
    res = client.post("/sendcode", json={"email": "t@x.com"})
    record = mongo.update_password.find_one({"email": "t@x.com"})

    assert res.status_code == 200
    assert record["try"] == 3 and isinstance(record["created_at"], datetime)


def test_reset_code_try_limit(client, mongo):
    mongo.users.insert_one({"user_name": "t", "email": "t@x.com", "password": "old"})
    mongo.update_password.insert_one({"email": "t@x.com", "code": "123456", "try": 3, "created_at": _now()})

    r1 = client.post("/teacher/updatepassword", json=_reset_body("000000"))
    r2 = client.post("/teacher/updatepassword", json=_reset_body("000000"))
    r3 = client.post("/teacher/updatepassword", json=_reset_body("000000"))
    # Correct code after the limit: the code has been deleted.
    r4 = client.post("/teacher/updatepassword", json=_reset_body("123456"))

    assert (r1.status_code, r1.get_json()["try"]) == (400, 2)
    assert (r2.status_code, r2.get_json()["try"]) == (400, 1)
    assert (r3.status_code, r3.get_json()["try"]) == (400, 0)
    assert r4.status_code == 400
    assert mongo.update_password.find_one({"email": "t@x.com"}) is None
    assert mongo.users.find_one({"email": "t@x.com"})["password"] == "old"


def test_reset_code_success_hashes_password(client, mongo):
    mongo.users.insert_one({"user_name": "t", "email": "t@x.com", "password": "old"})
    mongo.update_password.insert_one({"email": "t@x.com", "code": "123456", "try": 3, "created_at": _now()})

    res = client.post("/teacher/updatepassword", json=_reset_body("123456"))

    assert res.status_code == 200
    assert is_password_hash(mongo.users.find_one({"email": "t@x.com"})["password"])
    assert mongo.update_password.find_one({"email": "t@x.com"}) is None


def test_reset_code_expires(client, mongo):
    mongo.users.insert_one({"user_name": "t", "email": "t@x.com", "password": "old"})
    mongo.update_password.insert_one({"email": "t@x.com", "code": "123456", "try": 3,
                                      "created_at": _now() - timedelta(minutes=11)})

    res = client.post("/teacher/updatepassword", json=_reset_body("123456"))

    assert res.status_code == 400
    assert mongo.update_password.find_one({"email": "t@x.com"}) is None
