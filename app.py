import hmac
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, request,g,abort
from pymongo import ReturnDocument
from flask_cors import CORS
from routes.student_blueprint import student_blueprint
from routes.education_blueprint import education_blueprint
import const
app = Flask(__name__)

from db.db import MongoDB
import config
from model import model
from smtpserver import EmailVerification,EmailVerificationCode
from model.model import User,Egzersiz,Story

from jwtgenerate import JWT_Token
from passwords import hash_password, verify_password

db_url = config.DATABASE_URL
db_name = config.DATABASE_NAME

token_handler= JWT_Token()

app.register_blueprint(student_blueprint, url_prefix='/student')
app.register_blueprint(education_blueprint, url_prefix='/teacher')



CORS(app, origins=config.CORS_ORIGINS)


@app.route('/login',methods=["POST"])
def login():
    content = request.get_json()
    if not isinstance(content, dict):
        return jsonify({"error":"eksik bilgi doldurunuz"}),400

    if "username" not in content or "password" not in content:
        return jsonify({"error": "kullanıcı adı yada şifre eksik"}),400
    
    user_name = content["username"]
    password = content["password"]
    if not isinstance(user_name, str) or not isinstance(password, str):
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400

    db = MongoDB(db_name=db_name,url=db_url)
    user = db.find_one("users",query={"user_name":user_name})

    if type(user)!=dict:
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400

    matches, needs_rehash = verify_password(user.get("password"), password)
    if not matches:
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400

    if needs_rehash:
        # Lazy migration: replace the legacy plaintext password with a hash.
        db.update_one(collection_name="users",query={"_id":user["_id"]},data={"password":hash_password(password)})

    if user.get("user_type")==const.student:
        if user.get("activate") in (False, "False"):
            return jsonify({"message":"lütfen üyeliğinizin aktifliğini bekleyin"}),200
        token = token_handler.generate_token(user_id=None,role=const.student,name=user.get("name"),user_name=user["user_name"],level=user.get("level"))
    else:
        token = token_handler.generate_token_teacher(user_id=None,role=user.get("user_type"),name=user.get("name"),user_name=user["user_name"])

    # Kept for compatibility; auth relies on the JWT signature, not this field.
    # Not checking modified_count: two logins in the same second yield the
    # same token, which would be reported as "not modified".
    db.update_one(collection_name="users",query={"_id":user["_id"]},data={"token":token})
    return jsonify({"message":"giriş başarılı","token":token,"name":user.get("name")}),200


PUBLIC_PATHS = {"/login", "/contact", "/sendcode", "/teacher/updatepassword"}


@app.before_request
def auth_middleware():
    # CORS preflight requests never carry the token header.
    if request.method == "OPTIONS" or request.path in PUBLIC_PATHS:
        return None

    token = request.headers.get("token")
    if not token:
        return jsonify({"error":"yetkisiz erişim"}),401

    payload, _error = token_handler.decode_token(token=token)
    if payload is None or "role" not in payload or "user_name" not in payload:
        return jsonify({"error":"tekrar giriş yapınız"}),401

    g.user_type = payload["role"]
    g.token = token
    g.user_name = payload["user_name"]
    if g.user_type == const.student:
        g.level = payload.get("level")



@app.route('/contact',methods=["POST"])
def index():
    content = request.get_json(silent=True)
    content = content.get("formData") if isinstance(content, dict) else None
    if not isinstance(content, dict) or not content.get("subject") or not content.get("email"):
        return jsonify({"error":"eksik bilgi doldurunuz"}),400
    try:
        EmailVerification(config.CONTACT_EMAIL,konu=content["subject"],kimden=content["email"])
    except Exception:
        app.logger.exception("Failed to send contact email")
        return jsonify({"error":"sunucu hatası"}),500
    return jsonify({"message":"mesajınız gönderildi"}),200

RESET_COLLECTION = "update_password"
RESET_CODE_TTL = timedelta(minutes=10)
RESET_CODE_MAX_TRIES = 3


def _utcnow():
    # Naive UTC, matching what PyMongo returns for stored datetimes.
    return datetime.now(timezone.utc).replace(tzinfo=None)


@app.route('/sendcode',methods=["POST"])
def send_code():
    content = request.get_json(silent=True)
    email = content.get("email") if isinstance(content, dict) else None
    if not isinstance(email, str) or not email.strip():
        return jsonify({"message":"lütfen mailiniz kontrol ediniz"}),400
    email = email.strip()

    db = MongoDB(url=db_url,db_name=db_name)
    users = db.find_one(collection_name="users",query={"email":email})
    if type(users)!=dict:
        return jsonify({"message":"lütfen mailiniz kontrol ediniz"}),400

    try:
        code = EmailVerificationCode(email_receiver=email,subject="şifre güncelleme kodu",sender_name="GELISTRİO").code
    except Exception:
        app.logger.exception("Failed to send password reset email")
        return jsonify({"error":"sunucu hatası"}),500

    # A new code replaces any previous one and resets the try counter.
    db.delete_many(RESET_COLLECTION,{"email":email})
    inserted = db.insert_one(RESET_COLLECTION,{"code":code,"email":email,"try":RESET_CODE_MAX_TRIES,"created_at":_utcnow()})
    if inserted:
        return jsonify({"message":"doğrulama kodunuz gönderildi lütfen mailinizi kontrol edin"}),200
    return jsonify({"error":"sunucu hatası"}),500


@app.route("/teacher/updatepassword",methods=["POST"])
def update_password():
    content = request.get_json(silent=True)
    content = content.get("formData") if isinstance(content, dict) else None
    if not isinstance(content, dict):
        return jsonify({"error":"eksik bilgi doldurunuz"}),400

    email = content.get("email")
    password = content.get("password")
    rpassword = content.get("rpassword")
    code = content.get("code")
    if not all(isinstance(v, str) and v for v in (email, password, rpassword, code)):
        return jsonify({"error":"eksik bilgi doldurunuz"}),400
    email = email.strip()
    code = code.strip()

    if password != rpassword:
        return jsonify({"error":"şifreler eşleşmiyor"}),400

    db = MongoDB(url=db_url,db_name=db_name)
    record = db.find_one(collection_name=RESET_COLLECTION,query={"email":email})
    if not record:
        return jsonify({"error":"lütfen tekrar kod alınız "}),400

    created_at = record.get("created_at")
    tries = record.get("try", 0)
    if not isinstance(created_at, datetime) or _utcnow() - created_at > RESET_CODE_TTL or not isinstance(tries, int) or tries <= 0:
        db.delete_one(collection_name=RESET_COLLECTION,query={"_id":record["_id"]})
        return jsonify({"error":"kodun süresi doldu lütfen tekrar kod alınız"}),400

    if not hmac.compare_digest(str(record.get("code", "")).encode("utf-8"), code.encode("utf-8")):
        # Atomic decrement so parallel requests cannot exceed the limit.
        updated = db.db[RESET_COLLECTION].find_one_and_update(
            {"_id":record["_id"],"try":{"$gt":0}},
            {"$inc":{"try":-1}},
            return_document=ReturnDocument.AFTER,
        )
        remaining = updated["try"] if updated else 0
        if remaining <= 0:
            db.delete_one(collection_name=RESET_COLLECTION,query={"_id":record["_id"]})
            return jsonify({"error":"çok fazla hatalı deneme yaptınız lütfen tekrar kod alınız","try":0}),400
        return jsonify({"error":"hatalı kod girdiniz","try":remaining}),400

    updated = db.update_one(collection_name="users",query={"email":email},data={"password":hash_password(password)})
    db.delete_one(collection_name=RESET_COLLECTION,query={"_id":record["_id"]})
    if updated==1:
        return jsonify({"message":"şifreniz başarılı bir şekilde güncellendi"}),200
    return jsonify({"error":"şifreniz  güncellenirken hata oluştu"}),400


if __name__ == '__main__':
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
