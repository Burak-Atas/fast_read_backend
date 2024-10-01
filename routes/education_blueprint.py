from flask import Blueprint, request, jsonify, g
from db.db import MongoDB
from dotenv import dotenv_values
import const
from db.db import MongoDB
from jwtgenerate import JWT_Token
from model.model import Story,Egzersiz,Process,User,Video,Messages,Task,Teacher
from datetime import datetime, timedelta
from bson import ObjectId
import os
import uuid

import time

env_values = dotenv_values()
db_url = env_values.get("DATABASE_URL")
db_name = env_values.get("DATABASE_NAME")
SERVER_IP = env_values.get("SERVER_IP")



userId = 0


education_blueprint = Blueprint('education_blueprint', __name__)

@education_blueprint.before_request
def check_user_type():
    print("education",g.user_type)
    if g.user_type ==const.student:
        return jsonify({"error": "yetkisizdd erişim"}), 403


@education_blueprint.route("/", methods=["POST"])
def teach():
    content = request.get_json()
    if content is None or "username" not in content or "password" not in content:
        return jsonify({"error": "Eksik bilgi"}), 400
    username = content["username"]
    password = content["password"]
    
    return jsonify({"username": username, "password": password}), 200


"""
    KULLANICI İŞLEMLERİ 
"""

# bir yılı geçmiş kullanıcıyı silme işlemi
@education_blueprint.route("/firstdelluser", methods=["GET"])
def first_dell_user():
    if g.user_type != const.admin:
        return jsonify({"error": "lütfen admin hesabı ile giriş yapınız"}), 200

    db = MongoDB(url=db_url, db_name=db_name)
    users_cursor = db.find_many(collection_name="users", query=None)
    users = [dict(user) for user in users_cursor]

    # Şu anki tarihten bir yıl öncesine giden tarih
    one_year_ago = datetime.now() - timedelta(days=365)

    for user in users:
        if user["kayit_tarihi"] < one_year_ago:
            user_name = user["user_name"]
            db.delete_one(collection_name="users", query={"user_name": user_name})

    users_cursor.close()
    return jsonify({"message": "Bir yılı geçen kullanıcılar başarıyla silindi"}), 200
    
    

@education_blueprint.route("/user", methods=["GET"])
def user():
    db = MongoDB(url=db_url, db_name=db_name)
    print("atas",g.user_type)
    
    if g.user_type == const.teacher:
        users_cursor = db.find_many(collection_name="users", query={"teacher_name":g.user_name})
        users = [dict(user) for user in users_cursor]
        
        for user in users:
            del user['_id']
            del user['token']
        
        print(users)
        
        users_cursor.close()
        users_cursor.close()
        return jsonify(users), 200   
    
    users_cursor = db.find_many(collection_name="users", query=None)
    users = [dict(user) for user in users_cursor]
    
    for user in users:
        del user['_id']
        del user['token']
    
    users_cursor.close()
    return jsonify(users), 200


@education_blueprint.route("/adduser", methods=["POST"])
def add_user():
    content = request.get_json()
    if content is None or "user_name" not in content or "password" not in content:
        return jsonify({"error": "Eksik bilgi"}), 400
    print(content)
    
    username = content["user_name"].strip()
    password = content["password"].strip()
    name = content["name"]
    phoneNumber = content["phone_number"]
    level = content["level"]
    
    db = MongoDB(db_name=db_name, url=db_url)
    
    users = db.find_one(collection_name="users",query={"user_name":username})
    print(users)
    if type(users)==dict:
        return jsonify({"error": "kullanıcı_adı  zaten  kayıtlı"}), 400
    
    token = JWT_Token()
    userToken = token.generate_token(user_id=None,name=name,role=const.student,user_name=username,level=level)
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

    usr = User(_id=new_id,basari_puani=basari_puani,kayit_tarihi=createdTime,password=password,phone_number=phoneNumber,user_name=username,user_type=userType,token=userToken,name=name,level=level,activate=activated,teacher_name=teacher_name,count=0,last_seen_data=None).__dict__
    usr_proccess = Process(user_name=username,next_exercise=1,now_exercise=0,day="day1",next_day_date=newDate,okey=False,level=level).__dict__
    db.insert_one(collection_name="users",data=usr)
    db.insert_one(collection_name="process",data=usr_proccess)
    return jsonify({"message":"kullanıcı eklendi","username": username, "password": password,"token":userToken}), 200

@education_blueprint.route("/user/isactivate",methods=["POST"])
def activated():
    if g.user_type != const.admin:
        return jsonify({"error":"lütfen admin hesabı ile giriş yapınız"}),200
    
    content = request.get_json()
    user_name = content["user_name"]
    print(user_name)

    db = MongoDB(db_name=db_name, url=db_url)
    users = db.find_one(collection_name="users",query={"user_name":user_name})

    if type(users)!=dict:
        return jsonify({"error": "kullanıcı_adı  bulunamadı"}), 400
    
    print(users["activate"])
    
    if users["activate"]=="True":
        return jsonify({"message":"kullanıcı zaten aktif"}),200
    
    activate = True
    
    result = db.update_one(collection_name="users",query={"user_name":user_name},data={"activate":activate})
    print(result)
    
    return jsonify({"message":"işlem başarılı"}),200

@education_blueprint.route("/addteacher",methods=["POST"])
def add_teacher():
    if g.user_type != const.admin:
        return jsonify({"error":"lütfen admin hesabı ile giriş yapınız"}),200
    
    content = request.get_json()
    if content is None or "user_name" not in content or "password" not in content:
        return jsonify({"error": "Eksik bilgi"}), 400
    
    username = content["user_name"]
    password = content["password"]
    name = content["name"]
    email = content["email"]
    
    db = MongoDB(db_name=db_name, url=db_url)
    
    users = db.find_one(collection_name="users",query={"user_name":username})
    print(users)
    if type(users)==dict:
        return jsonify({"error": "kullanıcı_adı  zaten  kayıtlı"}), 400
    
    token = JWT_Token()
    userToken = token.generate_token_teacher(user_id=None,name=name,role=const.teacher,user_name=username)
    
    new_id = ObjectId()
    userType = const.teacher
    
    createdTime = datetime.now()
    usr = Teacher(_id=new_id,kayit_tarihi=createdTime,password=password,email=email,user_name=username,user_type=userType,token=userToken,name=name).__dict__
    db.insert_one(collection_name="users",data=usr)
    return jsonify({"message":"öğretmen başarılı bir şekilde eklendi","username": username, "password": password,"token":userToken}), 200


@education_blueprint.route("/deluser", methods=["GET"])
def del_user():
    if g.user_type != const.admin:
        return jsonify({"error":"lütfen admin hesabı ile giriş yapınız"}),200
    
    name = request.headers.get("username").strip()
    print("silinen kulalnıcı ismi:", name)
    
    if name is None or name == "":
        return jsonify({"message": "Kullanıcı adı belirtilmemiş."}), 400
    
    query = {"user_name": name}
    db = MongoDB(db_name=db_name, url=db_url)
    deleted_user = db.delete_one("users", query=query)
    deleted_process = db.delete_one("process", query=query)

    if deleted_user :
        return jsonify({"message": "Kullanıcı başarılı şekilde silindi."}), 200
    else:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

@education_blueprint.route("/alldeluser",methods=["DELETE"])
def all_del_user():
    if g.user_type != const.admin:
        return jsonify({"error":"lütfen admin hesabı ile giriş yapınız"}),200
    
    db = MongoDB(url=db_url,db_name=db_name)

    db.delete_many(collection_name="users",query={})
    
    return jsonify(),200

@education_blueprint.route("/updateuser/<string:old_name>", methods=["POST"])
def update_user(old_name):
    if g.user_type != const.admin:
        return jsonify({"error": "Lütfen admin hesabı ile giriş yapınız"}), 403  # Hata kodu değiştirildi
    
    content = request.get_json()
    if content is None or ("user_name" not in content and "password" not in content):
        return jsonify({"error": "Eksik bilgi"}), 400
    
    #new_username = content.get("user_name")
    new_password = content.get("password")
    name = content.get("name")
    phone_number = content.get("phone_number")
    level = content.get("level")
    
    query = {"user_name": old_name}
    print(old_name)
    print("old_name",old_name)
    print(name)
    
    new_values = {}

    # Mevcut bilgileri güncellemek için kontroller
    """
    if new_username:
        new_values["username"] = new_username
    """
    if new_password:
        new_values["password"] = new_password
    if name:
        new_values["name"] = name
    if phone_number:
        new_values["phone_number"] = phone_number
    if level:
        new_values["level"] = level

    if not new_values:
        return jsonify({"error": "Güncellenecek bilgi bulunamadı"}), 400
    
    print("new,values",new_values)
    db = MongoDB(db_name=db_name, url=db_url)
    updated_user = db.update_one(collection_name="users", query=query, data=new_values)
  
    print("update_user",updated_user)
    if updated_user==1:
        return jsonify({"message": "Kullanıcı başarılı şekilde güncellendi"}), 200
    else:
        return jsonify({"error": "Kullanıcı güncellenirken hata oluştu"}), 400
        

@education_blueprint.route("/user/countuser",methods=["GET"])
def count_user():
    db = MongoDB(url=db_url,db_name=db_name)
    count_document = db.count_documents(collection_name="users",query={})
    
    return jsonify({"kullanici_sayisi":count_document})
    
    
"""
    KULLANICI İŞLEMLERİ TAMAMLANDI
    (UPDATEUSER DENEMESİ YAPILMADI)
"""


@education_blueprint.route("/addeducation",methods=["POST"])
def add_education():
    content = request.get_json()
    
    day = content["day"]
    
    #egzersiizn içinde egzersiz ismi ,hızı ve sayısı olmalıdır
    egzersiz = content["egzersiz"]
    
    db = MongoDB(url=db_url,db_name=db_name)
    db.insert_one("egzersiz",)
    


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

    unique_id = str(uuid.uuid4())

    if video:
        filename = video.filename 
        name = unique_id
        video.save(os.path.join("static", name))  
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
    videos_curser = db.find_many(collection_name="videos", query=None)
    
    videos = [dict(video) for video in videos_curser]
    for video in videos:
        video['_id'] = str(video['_id'])
    videos_curser.close()
    return jsonify(videos), 200

@education_blueprint.route("/video/<string:name>",methods=["GET"])
def get_video(name):
    query = {"video_name":name}
       
    db = MongoDB(url=db_url,db_name=db_name)
    videos = db.find_one(collection_name="videos",query=query)

    if type(videos)!=dict:
        return jsonify({"error":"video bulunamadı"}),400

    return jsonify({"video_url":videos["video_url"]}),200

@education_blueprint.route("/delvideo", methods=["DELETE"])
def del_video():
    name = request.headers.get("name")
    
    if name=="":
        return jsonify({"error": "Video adı belirtilmedi."}), 400
    
    db = MongoDB(url=db_url, db_name=db_name)
    deleted_video = db.delete_one(collection_name="videos", query={"name": name})

    if deleted_video == 1:
        # Dosya sisteminden videoyu sil
        video_path = os.path.join("static", name)
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
    content = request.get_json()
    print(content)
    if "content" not in content or "header" not in content:
        return jsonify({"error":"Hatalı header"}), 400
    
    header = content["header"]
    messages = content["content"]
    user_name = content["user_name"]
    
    
    current_datetime = datetime.now()
    current_date = current_datetime.date()
    current_time_str = current_datetime.strftime("%H:%M:%S")
    
    db = MongoDB(url=db_url, db_name=db_name)   

    data = Messages(header=header,sender=g.user_name, receiver=user_name, content=messages, cender_date=current_date, date=current_time_str).__dict__
    
    db.insert_one(collection_name="messages", data=data)
    
    return jsonify({"messages":"Mesajınız gönderildi"}), 200


@education_blueprint.route("/messages", methods=["GET"])
def message():
    db = MongoDB(url=db_url, db_name=db_name)
    messages_cursor = db.find_many(collection_name="messages", query=None)
    messages = [dict(msg) for msg in messages_cursor]
    
    for msg in messages:
        del msg['_id']
    
    messages_cursor.close()
    
    return jsonify(messages), 200


    

@education_blueprint.route("/delmessage", methods=["DELETE"])
def del_message():
    header = request.headers.get("header")
    print(header)
    if header == "":
        return jsonify({"error": "Hatalı header"}), 400

    db = MongoDB(url=db_url, db_name=db_name)

    res = db.delete_one(collection_name="messages", query={"header": header})

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
    print(g.user_name)
    tasks = [dict(task) for task in task_cursor]
    
    for task in tasks:
        del task['_id']
    
    task_cursor.close()
    
    return jsonify(tasks), 200
    
    
@education_blueprint.route("/addtask",methods=["POST"])
def add_task():
    content = request.get_json()
    print(content)
    if "content" not in content or "date" not in content:
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
    print(task_id)
    db = MongoDB(db_name=db_name, url=db_url) 
    
    result = db.delete_one(collection_name="task", query={"task_id":task_id})    
    return jsonify({"error": "silindi"}),200



    """
    EGZERSİZ İŞELMLERİ
    """
@education_blueprint.route("/getexercisedetails", methods=["POST"])
def get_exercise():
    try:
        # JSON verisini alın
        exercise_data = request.get_json()
        
        db = MongoDB(db_name=db_name, url=db_url) 
        cursor = db.find_many(collection_name="after_exercise", query=exercise_data)
        exercises = [dict(exercise) for exercise in cursor]

        # Her bir egzersiz verisinden '_id' alanını kaldırın
        for ex in exercises:
            ex.pop('_id', None)
        
        # JSON yanıtı döndürün
        return jsonify(exercises), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500



@education_blueprint.route("/getexercises", methods=["GET"])
def get_exercises():
    level = request.args.get('level')
    print("deneme elvei",level)
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
        
    for ex in exercises:
        del ex['_id']
    
    return jsonify(exercises), 200


@education_blueprint.route("/selecttext",methods=["GET"])
def select_text():
    if g.user_type==const.student:
        return jsonify({"error": "Lütfen admin veya öğretmen hesabı ile giriş yapınız"}), 403

    content = request.get_json()
    
    db = MongoDB(db_name=db_name, url=db_url)
    
    cursor_all = db.find_one(collection_name="exercise",query=content)
    
    return jsonify(cursor_all["data"]),200
    


# faydalı bilgiler
from model.model import Knowledge

from pydantic import ValidationError

@education_blueprint.route("/setknowledge", methods=["POST"])
def set_knowledge():
    if g.user_type != const.admin:
        return jsonify({"error": "Lütfen admin hesabı ile giriş yapınız"}), 403
    
    try:
        content = request.get_json()
        content["id"] = str(uuid.uuid4())  # Add a unique ID to the content
        knowledge = Knowledge(**content)
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

    db = MongoDB(url=db_url, db_name=db_name)
    res = db.insert_one(collection_name="knowledge", data=knowledge.dict())

    if res:
        return jsonify({"message": "Başarılı şekilde eklendi"}), 200
    else:
        return jsonify({"error": "Ekleme yapılırken hata oluştu"}), 500


@education_blueprint.route("/setpublish", methods=["POST"])
def set_publish():
    if g.user_type != const.admin:
        return jsonify({"error": "Lütfen admin hesabı ile giriş yapınız"}), 403

    content = request.get_json()
    print(content)

    db = MongoDB(url=db_url,db_name=db_name)
    res = db.update_one(collection_name="knowledge",query=content,data={"publish":True})

    print(res)
    if res==1:
        return jsonify({"message": "Faydalı  Bilgi Yayınlandı"}), 200
    else:
        return jsonify({"error":"faydalı bilgi yayınlanırken hata oluştu"}),400
@education_blueprint.route("/setnotpublish", methods=["POST"])
def set_not_publish():
    if g.user_type != const.admin:
        return jsonify({"error": "Lütfen admin hesabı ile giriş yapınız"}), 403

    content = request.get_json()
    print(content)

    db = MongoDB(url=db_url,db_name=db_name)
    res = db.update_one(collection_name="knowledge",query=content,data={"publish":False})

    print(res)
    

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
    print(id)
    print(id)
    print(request.headers)
    if id == "":
        return jsonify({"error":"internal error"}),500
    db = MongoDB(url=db_url, db_name=db_name)
    res = db.delete_one(collection_name="knowledge",query={"id":id})
    
    if res==1:
        return jsonify({"message":"başarılı bir şekilde silindi"}),200
    else:
        return jsonify({"error":"hata"}),500
    
    
    
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