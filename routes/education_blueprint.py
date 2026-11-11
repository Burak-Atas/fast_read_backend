from flask import Blueprint, request, jsonify, g, current_app
from db.db import MongoDB
import config
import const
from passwords import hash_password
from model.model import Story,Egzersiz,Process,User,Video,Messages,Task,Teacher
from datetime import datetime, timedelta, timezone
from werkzeug.utils import secure_filename
from bson import ObjectId
import os
import uuid

db_url = config.DATABASE_URL
db_name = config.DATABASE_NAME
SERVER_IP = config.SERVER_IP



education_blueprint = Blueprint('education_blueprint', __name__)


def _json_body():
    """Request JSON as a dict, or None if missing/invalid."""
    content = request.get_json(silent=True)
    return content if isinstance(content, dict) else None


def _strip_private_fields(user):
    for field in ("_id", "token", "password", "password_changed_at"):
        user.pop(field, None)
    return user


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_admin():
    return g.user_type == const.admin


def _parse_level(value):
    """Level as a positive int (accepts digit strings), else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    return value if isinstance(value, int) and value > 0 else None


def _is_scalar(value):
    # Plain values only: a dict here would let callers inject query
    # operators such as {"$ne": ...} or {"$where": ...}.
    return isinstance(value, (str, int, float, bool)) or value is None


def _owns_student(db, user_name):
    """Admins see every student; teachers only their own."""
    if _is_admin():
        return True
    student = db.find_one(collection_name="users", query={"user_name": user_name, "user_type": const.student})
    return isinstance(student, dict) and student.get("teacher_name") == g.user_name


ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".ogg", ".ogv"}


def _video_dir():
    return current_app.static_folder

@education_blueprint.before_request
def check_user_type():
    if request.method == "OPTIONS":
        return None
    # Allowlist: only teachers and admins may use /teacher/* routes.
    if getattr(g, "user_type", None) not in (const.teacher, const.admin):
        return jsonify({"error": "yetkisiz erişim"}), 403


"""
    KULLANICI İŞLEMLERİ 
"""

# bir yılı geçmiş kullanıcıyı silme işlemi
@education_blueprint.route("/firstdelluser", methods=["GET"])
def first_dell_user():
    if g.user_type != const.admin:
        return jsonify({"error": "lütfen admin hesabı ile giriş yapınız"}), 403

    db = MongoDB(url=db_url, db_name=db_name)
    # Only students expire; teachers and admins are never removed here.
    users_cursor = db.find_many(collection_name="users", query={"user_type": const.student})
    users = [dict(user) for user in users_cursor]
    users_cursor.close()

    # Şu anki tarihten bir yıl öncesine giden tarih
    one_year_ago = datetime.now() - timedelta(days=365)

    for user in users:
        registered = user.get("kayit_tarihi")
        if isinstance(registered, datetime) and registered < one_year_ago:
            user_name = user.get("user_name")
            db.delete_one(collection_name="users", query={"user_name": user_name, "user_type": const.student})
            db.delete_one(collection_name="process", query={"user_name": user_name})

    return jsonify({"message": "Bir yılı geçen kullanıcılar başarıyla silindi"}), 200
    
    

@education_blueprint.route("/user", methods=["GET"])
def user():
    db = MongoDB(url=db_url, db_name=db_name)
    
    if g.user_type == const.teacher:
        users_cursor = db.find_many(collection_name="users", query={"teacher_name":g.user_name})
        users = [dict(user) for user in users_cursor]
        
        for user in users:
            _strip_private_fields(user)
        
        
        users_cursor.close()
        return jsonify(users), 200   
    
    users_cursor = db.find_many(collection_name="users", query={})
    users = [dict(user) for user in users_cursor]
    
    for user in users:
        _strip_private_fields(user)
    
    users_cursor.close()
    return jsonify(users), 200


@education_blueprint.route("/adduser", methods=["POST"])
def add_user():
    content = _json_body()
    if content is None or not isinstance(content.get("user_name"), str) or not isinstance(content.get("password"), str):
        return jsonify({"error": "Eksik bilgi"}), 400
    if not isinstance(content.get("name"), str) or "level" not in content:
        return jsonify({"error": "Eksik bilgi"}), 400
    
    username = content["user_name"].strip()
    password = content["password"].strip()
    if not username or not password:
        return jsonify({"error": "Eksik bilgi"}), 400
    name = content["name"].strip()
    phoneNumber = content.get("phone_number")
    if phoneNumber is not None and not isinstance(phoneNumber, str):
        return jsonify({"error": "Geçersiz telefon numarası"}), 400
    level = _parse_level(content["level"])
    if level is None:
        return jsonify({"error": "Geçersiz level değeri"}), 400
    
    db = MongoDB(db_name=db_name, url=db_url)
    
    users = db.find_one(collection_name="users",query={"user_name":username})
    if type(users)==dict:
        return jsonify({"error": "kullanıcı_adı  zaten  kayıtlı"}), 400
    
    userType = const.student
    basari_puani = 0
    
    createdTime = datetime.now()
    date = createdTime.strftime("%Y-%m-%d")
    time = createdTime.strftime("%H:%M:%S")
    newDate = (createdTime + timedelta(days=1)).strftime("%Y-%m-%d")

    new_id = ObjectId()

    activated = True

    if g.user_type == const.teacher:
        activated = False


    teacher_name = g.user_name

    usr = User(_id=new_id,basari_puani=basari_puani,kayit_tarihi=createdTime,password=hash_password(password),phone_number=phoneNumber,user_name=username,user_type=userType,token=None,name=name,level=level,activate=activated,teacher_name=teacher_name,count=0,last_seen_data=None).__dict__
    usr_proccess = Process(user_name=username,next_exercise=1,now_exercise=0,day="day1",next_day_date=newDate,okey=False,level=level).__dict__
    db.insert_one(collection_name="users",data=usr)
    db.insert_one(collection_name="process",data=usr_proccess)
    return jsonify({"message":"kullanıcı eklendi","username": username}), 200

@education_blueprint.route("/user/isactivate",methods=["POST"])
def activated():
    if g.user_type != const.admin:
        return jsonify({"error":"lütfen admin hesabı ile giriş yapınız"}),403
    
    content = _json_body()
    user_name = content.get("user_name") if content else None
    if not isinstance(user_name, str) or not user_name:
        return jsonify({"error": "Eksik bilgi"}), 400

    db = MongoDB(db_name=db_name, url=db_url)
    users = db.find_one(collection_name="users",query={"user_name":user_name})

    if type(users)!=dict:
        return jsonify({"error": "kullanıcı_adı  bulunamadı"}), 400
    
    
    if users.get("activate") in (True, "True"):
        return jsonify({"message":"kullanıcı zaten aktif"}),200
    
    activate = True
    
    result = db.update_one(collection_name="users",query={"user_name":user_name},data={"activate":activate})
    
    return jsonify({"message":"işlem başarılı"}),200

@education_blueprint.route("/addteacher",methods=["POST"])
def add_teacher():
    if g.user_type != const.admin:
        return jsonify({"error":"lütfen admin hesabı ile giriş yapınız"}),403
    
    content = _json_body()
    if content is None or not isinstance(content.get("user_name"), str) or not isinstance(content.get("password"), str):
        return jsonify({"error": "Eksik bilgi"}), 400
    if not content["user_name"].strip() or not content["password"].strip() or not isinstance(content.get("name"), str) or not isinstance(content.get("email"), str):
        return jsonify({"error": "Eksik bilgi"}), 400
    
    username = content["user_name"].strip()
    password = content["password"]
    name = content["name"].strip()
    email = content["email"].strip()
    
    db = MongoDB(db_name=db_name, url=db_url)
    
    users = db.find_one(collection_name="users",query={"user_name":username})
    if type(users)==dict:
        return jsonify({"error": "kullanıcı_adı  zaten  kayıtlı"}), 400
    
    new_id = ObjectId()
    userType = const.teacher
    
    createdTime = datetime.now()
    usr = Teacher(_id=new_id,kayit_tarihi=createdTime,password=hash_password(password),email=email,user_name=username,user_type=userType,token=None,name=name).__dict__
    db.insert_one(collection_name="users",data=usr)
    return jsonify({"message":"öğretmen başarılı bir şekilde eklendi","username": username}), 200


@education_blueprint.route("/deluser", methods=["GET"])
def del_user():
    if g.user_type != const.admin:
        return jsonify({"error":"lütfen admin hesabı ile giriş yapınız"}),403
    
    name = (request.headers.get("username") or "").strip()
    
    if name == "":
        return jsonify({"message": "Kullanıcı adı belirtilmemiş."}), 400
    
    db = MongoDB(db_name=db_name, url=db_url)
    # Admin accounts cannot be deleted through the API (avoids lock-out).
    deleted_user = db.delete_one("users", query={"user_name": name, "user_type": {"$ne": const.admin}})

    if deleted_user :
        db.delete_one("process", query={"user_name": name})
        return jsonify({"message": "Kullanıcı başarılı şekilde silindi."}), 200
    else:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

@education_blueprint.route("/alldeluser",methods=["DELETE"])
def all_del_user():
    if g.user_type != const.admin:
        return jsonify({"error":"lütfen admin hesabı ile giriş yapınız"}),403
    
    db = MongoDB(url=db_url,db_name=db_name)

    # Admin accounts are kept so the system stays manageable.
    deleted = db.delete_many(collection_name="users",query={"user_type": {"$ne": const.admin}})
    db.delete_many(collection_name="process",query={})
    
    return jsonify({"deleted": deleted}),200

@education_blueprint.route("/updateuser/<string:old_name>", methods=["POST"])
def update_user(old_name):
    if g.user_type != const.admin:
        return jsonify({"error": "Lütfen admin hesabı ile giriş yapınız"}), 403  # Hata kodu değiştirildi
    
    content = _json_body()
    if content is None or ("user_name" not in content and "password" not in content):
        return jsonify({"error": "Eksik bilgi"}), 400
    
    #new_username = content.get("user_name")
    new_password = content.get("password")
    name = content.get("name")
    phone_number = content.get("phone_number")
    level = content.get("level")
    
    query = {"user_name": old_name}
    
    new_values = {}

    # Mevcut bilgileri güncellemek için kontroller
    """
    if new_username:
        new_values["username"] = new_username
    """
    # Empty or missing password keeps the existing (hashed) password.
    if new_password is not None and not isinstance(new_password, str):
        return jsonify({"error": "Eksik bilgi"}), 400
    if new_password and new_password.strip():
        new_values["password"] = hash_password(new_password)
        # Invalidates tokens issued before this change (see auth middleware).
        new_values["password_changed_at"] = _utcnow()
    if name is not None and not isinstance(name, str):
        return jsonify({"error": "Eksik bilgi"}), 400
    if phone_number is not None and not isinstance(phone_number, str):
        return jsonify({"error": "Geçersiz telefon numarası"}), 400
    if name:
        new_values["name"] = name
    if phone_number:
        new_values["phone_number"] = phone_number
    if level not in (None, ""):
        level = _parse_level(level)
        if level is None:
            return jsonify({"error": "Geçersiz level değeri"}), 400
        new_values["level"] = level

    if not new_values:
        return jsonify({"error": "Güncellenecek bilgi bulunamadı"}), 400
    
    db = MongoDB(db_name=db_name, url=db_url)
    updated_user = db.update_one(collection_name="users", query=query, data=new_values)
  
    if updated_user==1:
        return jsonify({"message": "Kullanıcı başarılı şekilde güncellendi"}), 200
    else:
        return jsonify({"error": "Kullanıcı güncellenirken hata oluştu"}), 400
        

@education_blueprint.route("/user/countuser",methods=["GET"])
def count_user():
    db = MongoDB(url=db_url,db_name=db_name)
    query = {} if _is_admin() else {"teacher_name": g.user_name}
    count_document = db.count_documents(collection_name="users",query=query)
    
    return jsonify({"kullanici_sayisi":count_document})
    
    
"""
    KULLANICI İŞLEMLERİ TAMAMLANDI
    (UPDATEUSER DENEMESİ YAPILMADI)
"""


@education_blueprint.route("/addeducation",methods=["POST"])
def add_education():
    # Previously crashed on every call (insert_one without data) and
    # returned nothing. Not implemented.
    return jsonify({"error": "bu özellik henüz desteklenmiyor"}), 501
    


"""
    VİDEO İŞLMELERİ
"""
@education_blueprint.route("/addvideo", methods=["POST"])
def upload_video():
    # Check if the request contains a 'video' part
    if 'video' not in request.files:
        return jsonify({"error": "No video part"}), 400

    video = request.files['video']

    if video.filename == '':
        return jsonify({"error": "No selected video"}), 400

    if not SERVER_IP:
        current_app.logger.error("SERVER_IP is not configured")
        return jsonify({"error": "sunucu hatası"}), 500

    extension = os.path.splitext(video.filename)[1].lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        return jsonify({"error": "desteklenmeyen video formatı"}), 400

    if video:
        # Client filename is only stored as metadata, never used as a path.
        filename = secure_filename(video.filename) or "video" + extension
        name = str(uuid.uuid4()) + extension
        os.makedirs(_video_dir(), exist_ok=True)
        video.save(os.path.join(_video_dir(), name))
        url =  SERVER_IP+"static/"+name
        db = MongoDB(url=db_url,db_name=db_name)
        db.insert_one(collection_name="videos",data={
            "name":name,
            "filename":filename,
            "url": url
        })

        return jsonify({"message": "Video successfully uploaded", "filename": filename,"name":name,"url":url}), 200
  
    
@education_blueprint.route("/videos",methods=["GET"])
def videos():
    db = MongoDB(url=db_url, db_name=db_name)
    videos_curser = db.find_many(collection_name="videos", query={})
    
    videos = [dict(video) for video in videos_curser]
    for video in videos:
        video['_id'] = str(video['_id'])
    videos_curser.close()
    return jsonify(videos), 200

@education_blueprint.route("/video/<string:name>",methods=["GET"])
def get_video(name):
    # upload_video stores "name"/"url"; "video_name"/"video_url" kept for
    # older documents.
    query = {"$or": [{"name": name}, {"video_name": name}]}
       
    db = MongoDB(url=db_url,db_name=db_name)
    videos = db.find_one(collection_name="videos",query=query)

    if type(videos)!=dict:
        return jsonify({"error":"video bulunamadı"}),400

    return jsonify({"video_url":videos.get("url") or videos.get("video_url")}),200

@education_blueprint.route("/delvideo", methods=["DELETE"])
def del_video():
    name = request.headers.get("name")
    
    # Names are server-generated; anything with a path component is invalid.
    if not name or name != os.path.basename(name) or name in (".", ".."):
        return jsonify({"error": "Video adı belirtilmedi."}), 400
    
    db = MongoDB(url=db_url, db_name=db_name)
    deleted_video = db.delete_one(collection_name="videos", query={"name": name})

    if deleted_video == 1:
        # Dosya sisteminden videoyu sil
        video_path = os.path.join(_video_dir(), name)
        if os.path.exists(video_path):
            os.remove(video_path)
            return jsonify({"message": "Video başarıyla silindi."}), 200
        else:
            return jsonify({"message": "Veritabanından silindi ancak dosya sisteminde video bulunamadı."}), 200
    else:
        return jsonify({"error": "Belirtilen video bulunamadı veya zaten silinmiş olabilir."}), 404

"""
    VİDEO İŞLMELERİ BİTTİ
"""  



"""
    KULLANICI BAZLI  İŞLMELER
"""  

@education_blueprint.route("/sendmessage",methods=["POST"])
def send_message():
    content = _json_body()
    if content is None or "content" not in content or "header" not in content or "user_name" not in content:
        return jsonify({"error":"Hatalı header"}), 400
    
    header = content["header"]
    messages = content["content"]
    user_name = content["user_name"]
    if not all(isinstance(v, str) and v.strip() for v in (header, messages, user_name)):
        return jsonify({"error":"Hatalı header"}), 400
    
    db = MongoDB(url=db_url, db_name=db_name)
    # "all" is a broadcast; otherwise teachers may only message their own students.
    if user_name != "all" and not _owns_student(db, user_name):
        return jsonify({"error":"kullanıcı bulunamadı"}), 404
    
    
    current_datetime = datetime.now()
    current_date = current_datetime.date()
    current_time_str = current_datetime.strftime("%H:%M:%S")

    data = Messages(header=header,sender=g.user_name, receiver=user_name, content=messages, cender_date=current_date, date=current_time_str).__dict__
    
    db.insert_one(collection_name="messages", data=data)
    
    return jsonify({"messages":"Mesajınız gönderildi"}), 200


@education_blueprint.route("/messages", methods=["GET"])
def message():
    db = MongoDB(url=db_url, db_name=db_name)
    query = {} if _is_admin() else {"sender": g.user_name}
    messages_cursor = db.find_many(collection_name="messages", query=query)
    messages = [dict(msg) for msg in messages_cursor]
    
    for msg in messages:
        msg.pop('_id', None)
    
    messages_cursor.close()
    
    return jsonify(messages), 200


    

@education_blueprint.route("/delmessage", methods=["DELETE"])
def del_message():
    header = request.headers.get("header")
    if not header:
        return jsonify({"error": "Hatalı header"}), 400

    db = MongoDB(url=db_url, db_name=db_name)

    query = {"header": header}
    if not _is_admin():
        query["sender"] = g.user_name
    res = db.delete_one(collection_name="messages", query=query)

    if res > 0:
        return jsonify({"message": "Mesaj başarıyla silindi"}), 200
    else:
        return jsonify({"error": "Belirtilen başlıkla eşleşen bir mesaj bulunamadı"}), 404

"""
    KULLANICI BAZLI  İŞLMELER
"""  



""" 
    TAKVİM İŞLEMLERİ
"""
@education_blueprint.route("/tasklist",methods=["GET"])
def calendar():
    db = MongoDB(db_name=db_name, url=db_url) 
    task_cursor = db.find_many(collection_name="task", query={"who":g.user_name})
    tasks = [dict(task) for task in task_cursor]
    
    for task in tasks:
        task.pop('_id', None)
    
    task_cursor.close()
    
    return jsonify(tasks), 200
    
    
@education_blueprint.route("/addtask",methods=["POST"])
def add_task():
    content = _json_body()
    if content is None or not isinstance(content.get("content"), str) or not isinstance(content.get("date"), str):
        return jsonify({"error":"Hatalı işlem"}), 400
    
    date = content["date"].strip()  
    content = content["content"].strip() 
    
    db = MongoDB(url=db_url, db_name=db_name)
    unique_id = str(uuid.uuid4())

    data = Task(content=content,date=date,who=g.user_name,id = unique_id).__dict__
    db.insert_one(collection_name="task", data=data)
    
    return jsonify({"id":unique_id}), 200



@education_blueprint.route("/deltask", methods=["DELETE"])
def del_task():
    task_id = request.headers.get("task_id")
    if not task_id:
        return jsonify({"error":"Hatalı işlem"}), 400
    db = MongoDB(db_name=db_name, url=db_url) 
    
    # Users may only delete their own tasks.
    deleted = db.delete_one(collection_name="task", query={"task_id":task_id,"who":g.user_name})
    if not deleted:
        return jsonify({"error": "görev bulunamadı"}), 404
    return jsonify({"message": "silindi"}),200



    """
    EGZERSİZ İŞELMLERİ
    """
@education_blueprint.route("/getexercisedetails", methods=["POST"])
def get_exercise():
    content = _json_body()
    user_name = content.get("user_name") if content else None
    exercise_name = content.get("exercise_name") if content else None
    if not isinstance(user_name, str) or not user_name:
        return jsonify({"error": "Eksik bilgi"}), 400
    if exercise_name is not None and not isinstance(exercise_name, str):
        return jsonify({"error": "Eksik bilgi"}), 400

    # Built from known fields only; the raw body used to be passed to
    # MongoDB, allowing operator injection and reading any student's data.
    query = {"user_name": user_name}
    if exercise_name:
        query["exercise_name"] = exercise_name

    try:
        db = MongoDB(db_name=db_name, url=db_url)
        if not _owns_student(db, user_name):
            return jsonify({"error": "öğrenci bulunamadı"}), 404
        cursor = db.find_many(collection_name="after_exercise", query=query)
        exercises = [dict(exercise) for exercise in cursor]

        # Her bir egzersiz verisinden '_id' alanını kaldırın
        for ex in exercises:
            ex.pop('_id', None)
        
        # JSON yanıtı döndürün
        return jsonify(exercises), 200

    except Exception:
        current_app.logger.exception("getexercisedetails failed")
        return jsonify({"error": "sunucu hatası"}), 500



@education_blueprint.route("/getexercises", methods=["GET"])
def get_exercises():
    level = request.args.get('level')
    try:
        level = int(level) if level is not None else None  # level parametresini int yap
    except ValueError:
        return jsonify({"error": "Geçersiz level değeri"}), 400  # Geçersiz level hatası
    
    db = MongoDB(db_name=db_name, url=db_url)
    query = {}
    if level is not None:
        query["level"] = level  # Eğer level varsa sorguya ekle
    
    cursor = db.find_many(collection_name="exercise", query=query)
    exercises = [dict(exercise) for exercise in cursor]
        
    cursor.close()
    for ex in exercises:
        ex.pop('_id', None)
    
    return jsonify(exercises), 200


@education_blueprint.route("/selecttext",methods=["GET"])
def select_text():
    if g.user_type==const.student:
        return jsonify({"error": "Lütfen admin veya öğretmen hesabı ile giriş yapınız"}), 403

    content = _json_body()
    if not content:
        return jsonify({"error": "Eksik bilgi"}), 400
    # Exact-match lookups on plain field values only (no query operators).
    if not all(isinstance(k, str) and not k.startswith("$") and _is_scalar(v) for k, v in content.items()):
        return jsonify({"error": "Eksik bilgi"}), 400
    
    db = MongoDB(db_name=db_name, url=db_url)
    
    cursor_all = db.find_one(collection_name="exercise",query=content)
    if type(cursor_all) != dict:
        return jsonify({"error": "egzersiz bulunamadı"}), 404
    
    return jsonify(cursor_all.get("data")),200
    


# faydalı bilgiler
from model.model import Knowledge

from pydantic import ValidationError

@education_blueprint.route("/setknowledge", methods=["POST"])
def set_knowledge():
    if g.user_type != const.admin:
        return jsonify({"error": "Lütfen admin hesabı ile giriş yapınız"}), 403
    
    content = _json_body()
    if content is None:
        return jsonify({"error": "Eksik bilgi"}), 400
    try:
        content["id"] = str(uuid.uuid4())  # Add a unique ID to the content
        knowledge = Knowledge(**content)
    except (ValidationError, TypeError):
        return jsonify({"error": "Geçersiz bilgi"}), 400

    db = MongoDB(url=db_url, db_name=db_name)
    res = db.insert_one(collection_name="knowledge", data=knowledge.model_dump())

    if res:
        return jsonify({"message": "Başarılı şekilde eklendi"}), 200
    else:
        return jsonify({"error": "Ekleme yapılırken hata oluştu"}), 500


@education_blueprint.route("/setpublish", methods=["POST"])
def set_publish():
    if g.user_type != const.admin:
        return jsonify({"error": "Lütfen admin hesabı ile giriş yapınız"}), 403

    content = _json_body()
    knowledge_id = content.get("id") if content else None
    if not isinstance(knowledge_id, str) or not knowledge_id:
        return jsonify({"error": "Eksik bilgi"}), 400

    db = MongoDB(url=db_url,db_name=db_name)
    res = db.update_one(collection_name="knowledge",query={"id": knowledge_id},data={"publish":True})

    if res==1:
        return jsonify({"message": "Faydalı  Bilgi Yayınlandı"}), 200
    else:
        return jsonify({"error":"faydalı bilgi yayınlanırken hata oluştu"}),400
@education_blueprint.route("/setnotpublish", methods=["POST"])
def set_not_publish():
    if g.user_type != const.admin:
        return jsonify({"error": "Lütfen admin hesabı ile giriş yapınız"}), 403

    content = _json_body()
    knowledge_id = content.get("id") if content else None
    if not isinstance(knowledge_id, str) or not knowledge_id:
        return jsonify({"error": "Eksik bilgi"}), 400

    db = MongoDB(url=db_url,db_name=db_name)
    res = db.update_one(collection_name="knowledge",query={"id": knowledge_id},data={"publish":False})

    

    if res==1:
        return jsonify({"message": "Faydalı  Bilgi Yayından kaldırıldı"}), 200
    else :
        return jsonify({"message": "kaldırma işlmei sırasında hata oluştur"}), 400
        


@education_blueprint.route("/getknowledge", methods=["GET"])
def get_knowledge():
    if g.user_type == const.student:
        return jsonify({"error": "Lütfen admin hesabı ile giriş yapınız"}), 403

    db = MongoDB(url=db_url, db_name=db_name)
    res = db.find_many(collection_name="knowledge", query={})
    cursor = []
    for document in res:
        document.pop('_id', None)  # _id alanını kaldır
        cursor.append(document)
    return jsonify(cursor), 200

@education_blueprint.route("/deleteknowledge",methods=["DELETE"])
def delete_knowledge():
    if g.user_type != const.admin:
        return jsonify({"error": "Lütfen admin hesabı ile giriş yapınız"}), 403

    id = request.headers.get("head")
    if not id:
        return jsonify({"error":"Eksik bilgi"}),400
    db = MongoDB(url=db_url, db_name=db_name)
    res = db.delete_one(collection_name="knowledge",query={"id":id})
    
    if res==1:
        return jsonify({"message":"başarılı bir şekilde silindi"}),200
    else:
        return jsonify({"error":"bulunamadı"}),404
    
    
    
""" 
    VACOBOLARY
"""

@education_blueprint.route("/getvocabolary", methods=["GET"])
def get_vocabolary():
    if g.user_type == const.student:
        return jsonify({"error": "Lütfen admin hesabı ile giriş yapınız"}), 403

    db = MongoDB(url=db_url, db_name=db_name)
    res = db.find_many(collection_name="vocabolary", query={})
    cursor = []
    for document in res:
        document.pop('_id', None)  # _id alanını kaldır
        cursor.append(document)
    return jsonify(cursor), 200