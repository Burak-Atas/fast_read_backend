import json
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

import const
from jwtgenerate import JWT_Token


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --- auth middleware ---------------------------------------------------------

def test_token_of_deleted_user_rejected(client, mongo, admin_token):
    mongo.users.delete_one({"user_name": "admin"})
    assert client.get("/teacher/user", headers={"token": admin_token}).status_code == 401


def test_token_role_must_match_database(client, mongo, teacher_token):
    forged = JWT_Token().generate_token_teacher(user_id=None, role=const.admin, name="T", user_name="teacher1")
    assert client.get("/teacher/alldeluser", headers={"token": forged}).status_code in (401, 405)
    assert client.delete("/teacher/alldeluser", headers={"token": forged}).status_code == 401


def test_inactive_student_token_rejected(client, mongo, student_token):
    mongo.users.update_one({"user_name": "ali"}, {"$set": {"activate": False}})
    assert client.get("/student/allmessages", headers={"token": student_token}).status_code == 403


def test_password_change_revokes_old_tokens(client, mongo, admin_token):
    mongo.users.update_one({"user_name": "admin"},
                           {"$set": {"password_changed_at": _now() + timedelta(seconds=5)}})
    assert client.get("/teacher/user", headers={"token": admin_token}).status_code == 401


def test_security_headers(client):
    res = client.post("/login", json={})
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["Cache-Control"] == "no-store"


# --- rate limiting / enumeration --------------------------------------------

def test_login_lockout_after_failures(client, mongo):
    mongo.users.insert_one({"user_name": "t", "password": generate_password_hash("pw"), "user_type": const.teacher})
    for _ in range(10):
        assert client.post("/login", json={"username": "t", "password": "bad"}).status_code == 400
    assert client.post("/login", json={"username": "t", "password": "pw"}).status_code == 429


def test_login_unknown_role_refused(client, mongo):
    mongo.users.insert_one({"user_name": "odd", "password": generate_password_hash("pw")})
    assert client.post("/login", json={"username": "odd", "password": "pw"}).status_code == 403


def test_sendcode_does_not_reveal_unknown_email(client, mongo):
    res = client.post("/sendcode", json={"email": "nobody@x.com"})
    assert res.status_code == 200


def test_sendcode_rate_limited(client, mongo):
    codes = [client.post("/sendcode", json={"email": "nobody@x.com"}).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


# --- teacher routes: injection & ownership ----------------------------------

def test_exercise_details_rejects_operator_injection(client, mongo, teacher_token):
    mongo.after_exercise.insert_one({"user_name": "other", "exercise_name": "e1"})
    res = client.post("/teacher/getexercisedetails", headers={"token": teacher_token},
                      json={"user_name": {"$ne": None}})
    assert res.status_code == 400


def test_exercise_details_only_own_students(client, mongo, teacher_token, student_token):
    mongo.users.insert_one({"user_name": "veli", "user_type": const.student, "teacher_name": "someone-else"})
    mongo.after_exercise.insert_many([{"user_name": "ali", "exercise_name": "e1"},
                                      {"user_name": "veli", "exercise_name": "e1"}])
    own = client.post("/teacher/getexercisedetails", headers={"token": teacher_token}, json={"user_name": "ali"})
    other = client.post("/teacher/getexercisedetails", headers={"token": teacher_token}, json={"user_name": "veli"})
    assert own.status_code == 200 and len(own.get_json()) == 1
    assert other.status_code == 404


def test_setpublish_requires_id(client, mongo, admin_token):
    mongo.knowledge.insert_one({"id": "k1", "content": "c", "publish": False})
    assert client.post("/teacher/setpublish", headers={"token": admin_token}, json={}).status_code == 400
    assert client.post("/teacher/setpublish", headers={"token": admin_token},
                       json={"id": {"$ne": None}}).status_code == 400
    assert client.post("/teacher/setpublish", headers={"token": admin_token}, json={"id": "k1"}).status_code == 200


def test_teacher_sees_only_own_messages(client, mongo, teacher_token):
    mongo.messages.insert_many([{"sender": "teacher1", "header": "a"}, {"sender": "admin", "header": "b"}])
    res = client.get("/teacher/messages", headers={"token": teacher_token})
    assert [m["header"] for m in res.get_json()] == ["a"]
    assert client.delete("/teacher/delmessage", headers={"token": teacher_token, "header": "b"}).status_code == 404


def test_adduser_by_teacher_returns_no_token(client, mongo, teacher_token):
    res = client.post("/teacher/adduser", headers={"token": teacher_token},
                      json={"user_name": "new", "password": "pw", "name": "N", "level": "2"})
    assert res.status_code == 200 and "token" not in res.get_json()
    stored = mongo.users.find_one({"user_name": "new"})
    assert stored["level"] == 2 and stored["activate"] is False


def test_alldeluser_keeps_admins(client, mongo, admin_token, teacher_token):
    res = client.delete("/teacher/alldeluser", headers={"token": admin_token})
    assert res.status_code == 200
    assert [u["user_name"] for u in mongo.users.find()] == ["admin"]


def test_delvideo_rejects_path_traversal(client, mongo, teacher_token):
    res = client.delete("/teacher/delvideo", headers={"token": teacher_token, "name": "../app.py"})
    assert res.status_code == 400


def test_addvideo_rejects_non_video(client, mongo, teacher_token):
    import io
    res = client.post("/teacher/addvideo", headers={"token": teacher_token},
                      data={"video": (io.BytesIO(b"<script>"), "x.html")}, content_type="multipart/form-data")
    assert res.status_code == 400


# --- student routes ---------------------------------------------------------

def test_student_messages_served_as_json(client, mongo, student_token):
    mongo.messages.insert_one({"receiver": "ali", "header": "<script>alert(1)</script>"})
    res = client.get("/student/allmessages", headers={"token": student_token})
    assert res.status_code == 200 and res.mimetype == "application/json"
    assert json.loads(res.data)[0]["header"].startswith("<script>")
