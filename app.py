import hmac
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, request, g
from pymongo import ReturnDocument
from flask_cors import CORS
from routes.student_blueprint import student_blueprint
from routes.education_blueprint import education_blueprint
import const
app = Flask(__name__)

from db.db import MongoDB
import config
from smtpserver import EmailVerification,EmailVerificationCode

from jwtgenerate import JWT_Token
from passwords import hash_password, verify_password
import ratelimit
from werkzeug.middleware.proxy_fix import ProxyFix

db_url = config.DATABASE_URL
db_name = config.DATABASE_NAME

token_handler= JWT_Token()

app.register_blueprint(student_blueprint, url_prefix='/student')
app.register_blueprint(education_blueprint, url_prefix='/teacher')



CORS(app, origins=config.CORS_ORIGINS)

# Reject oversized bodies before they are read into memory (413).
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

if config.TRUSTED_PROXY_COUNT:
    # Only when running behind N trusted reverse proxies; otherwise clients
    # could spoof X-Forwarded-For and dodge per-IP rate limits.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=config.TRUSTED_PROXY_COUNT, x_proto=config.TRUSTED_PROXY_COUNT)

KNOWN_ROLES = (const.student, const.teacher, const.admin)

# Used to spend the same time on unknown users as on real ones, so response
# timing does not reveal which usernames exist.
_DUMMY_PASSWORD_HASH = hash_password("timing-equalizer")

LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_MAX_FAILURES_PER_USER = 10
LOGIN_MAX_FAILURES_PER_IP = 30


def _too_many_requests():
    return jsonify({"error":"çok fazla deneme yaptınız, lütfen daha sonra tekrar deneyin"}),429


@app.route('/login',methods=["POST"])
def login():
    content = request.get_json(silent=True)
    if not isinstance(content, dict):
        return jsonify({"error":"eksik bilgi doldurunuz"}),400

    if "username" not in content or "password" not in content:
        return jsonify({"error": "kullanıcı adı yada şifre eksik"}),400
    
    user_name = content["username"]
    password = content["password"]
    if not isinstance(user_name, str) or not isinstance(password, str):
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400

    db = MongoDB(db_name=db_name,url=db_url)
    user_key = "login:user:" + user_name.strip().lower()
    ip_key = "login:ip:" + ratelimit.client_ip()
    if (ratelimit.too_many(db, user_key, LOGIN_MAX_FAILURES_PER_USER, LOGIN_WINDOW)
            or ratelimit.too_many(db, ip_key, LOGIN_MAX_FAILURES_PER_IP, LOGIN_WINDOW)):
        return _too_many_requests()

    user = db.find_one("users",query={"user_name":user_name})

    if type(user)!=dict:
        verify_password(_DUMMY_PASSWORD_HASH, password)
        ratelimit.hit(db, user_key)
        ratelimit.hit(db, ip_key)
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400

    matches, needs_rehash = verify_password(user.get("password"), password)
    if not matches:
        ratelimit.hit(db, user_key)
        ratelimit.hit(db, ip_key)
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400
    ratelimit.clear(db, user_key)

    if needs_rehash:
        # Lazy migration: replace the legacy plaintext password with a hash.
        db.update_one(collection_name="users",query={"_id":user["_id"]},data={"password":hash_password(password)})

    user_type = user.get("user_type")
    if user_type not in KNOWN_ROLES:
        app.logger.warning("Login refused: user %r has unknown user_type", user["user_name"])
        return jsonify({"error":"yetkisiz erişim"}),403

    if user_type==const.student:
        if user.get("activate") in (False, "False"):
            return jsonify({"message":"lütfen üyeliğinizin aktifliğini bekleyin"}),200
        token = token_handler.generate_token(user_id=None,role=const.student,name=user.get("name"),user_name=user["user_name"],level=user.get("level"))
    else:
        token = token_handler.generate_token_teacher(user_id=None,role=user_type,name=user.get("name"),user_name=user["user_name"])

    # Kept for compatibility; auth relies on the JWT signature, not this field.
    # Not checking modified_count: two logins in the same second yield the
    # same token, which would be reported as "not modified".
    db.update_one(collection_name="users",query={"_id":user["_id"]},data={"token":token})
    return jsonify({"message":"giriş başarılı","token":token,"name":user.get("name")}),200


PUBLIC_PATHS = {"/login", "/contact", "/sendcode", "/teacher/updatepassword"}


def _issued_before_password_change(payload, user):
    changed_at = user.get("password_changed_at")
    if not isinstance(changed_at, datetime):
        return False
    iat = payload.get("iat")
    if not isinstance(iat, (int, float)):
        # Legacy token without "iat" cannot prove it is newer than the change.
        return True
    return int(iat) < int(changed_at.replace(tzinfo=timezone.utc).timestamp())


@app.before_request
def auth_middleware():
    # CORS preflight requests never carry the token header.
    if request.method == "OPTIONS" or request.path in PUBLIC_PATHS:
        return None

    token = request.headers.get("token")
    if not token:
        return jsonify({"error":"yetkisiz erişim"}),401

    payload, _error = token_handler.decode_token(token=token)
    if payload is None or not isinstance(payload.get("role"), str) or not isinstance(payload.get("user_name"), str):
        return jsonify({"error":"tekrar giriş yapınız"}),401

    # The token alone is not enough: the account must still exist with the
    # same role. This makes deletion, role changes, deactivation and password
    # resets take effect immediately instead of after token expiry.
    db = MongoDB(db_name=db_name,url=db_url)
    user = db.find_one("users",query={"user_name":payload["user_name"]})
    if (type(user)!=dict
            or user.get("user_type") != payload["role"]
            or payload["role"] not in KNOWN_ROLES
            or _issued_before_password_change(payload, user)):
        return jsonify({"error":"tekrar giriş yapınız"}),401
    if payload["role"] == const.student and user.get("activate") in (False, "False"):
        return jsonify({"error":"üyeliğiniz aktif değil"}),403

    g.user_type = payload["role"]
    g.token = token
    g.user_name = user["user_name"]
    if g.user_type == const.student:
        # Level from the database so admin changes apply without re-login.
        g.level = user.get("level", payload.get("level"))


@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if not request.path.startswith("/static/"):
        # API responses carry personal data and tokens; never cache them.
        response.headers.setdefault("Cache-Control", "no-store")
    return response



@app.route('/contact',methods=["POST"])
def index():
    content = request.get_json(silent=True)
    content = content.get("formData") if isinstance(content, dict) else None
    if not isinstance(content, dict) or not content.get("subject") or not content.get("email"):
        return jsonify({"error":"eksik bilgi doldurunuz"}),400
    db = MongoDB(url=db_url,db_name=db_name)
    if ratelimit.check_and_hit(db, "contact:ip:" + ratelimit.client_ip(), 5, timedelta(hours=1)):
        return _too_many_requests()
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

    # Same answer whether or not the address is registered (no enumeration).
    generic = jsonify({"message":"e-posta adresi kayıtlıysa doğrulama kodu gönderildi, lütfen mailinizi kontrol edin"}),200

    db = MongoDB(url=db_url,db_name=db_name)
    if (ratelimit.check_and_hit(db, "sendcode:ip:" + ratelimit.client_ip(), 10, timedelta(hours=1))
            or ratelimit.check_and_hit(db, "sendcode:email:" + email.lower(), 3, timedelta(minutes=15))):
        return _too_many_requests()

    users = db.find_one(collection_name="users",query={"email":email})
    if type(users)!=dict:
        return generic

    try:
        code = EmailVerificationCode(email_receiver=email,subject="şifre güncelleme kodu",sender_name="GELISTRİO").code
    except Exception:
        app.logger.exception("Failed to send password reset email")
        return jsonify({"error":"sunucu hatası"}),500

    # A new code replaces any previous one and resets the try counter.
    db.delete_many(RESET_COLLECTION,{"email":email})
    inserted = db.insert_one(RESET_COLLECTION,{"code":code,"email":email,"try":RESET_CODE_MAX_TRIES,"created_at":_utcnow()})
    if inserted:
        return generic
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
    if ratelimit.check_and_hit(db, "resetpw:ip:" + ratelimit.client_ip(), 20, timedelta(minutes=15)):
        return _too_many_requests()
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

    updated = db.update_one(collection_name="users",query={"email":email},data={"password":hash_password(password),"password_changed_at":_utcnow()})
    db.delete_one(collection_name=RESET_COLLECTION,query={"_id":record["_id"]})
    if updated==1:
        return jsonify({"message":"şifreniz başarılı bir şekilde güncellendi"}),200
    return jsonify({"error":"şifreniz  güncellenirken hata oluştu"}),400


if __name__ == '__main__':
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
