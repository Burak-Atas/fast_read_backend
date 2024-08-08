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
    print(g.user_type)
    if g.user_type != const.teacher and g.user_type != const.admin:
        return jsonify({"error": "yetkisiz erişim"}), 403


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
@education_blueprint.route("/firstdelluser",methods=["GET"])
def first_dell_user():
    if g.user_type != const.admin:
        return jsonify(),400

    db = MongoDB(url=db_url, db_name=db_name)
    users_cursor = db.find_many(collection_name="users", query=None)
    users = [dict(user) for user in users_cursor]

    
    for user in users:
        if user["kayit_tarihi"]>datetime.now():
            user_name =  user["user_type"]
            db.delete_one(collection_name="users",query={"user_name":user_name})
    
    users_cursor.close()
    return jsonify(users), 200
    
    

@education_blueprint.route("/user", methods=["GET"])
def user():
    db = MongoDB(url=db_url, db_name=db_name)
    if g.user_type == const.teacher:
        users_cursor = db.find_many(collection_name="users", query={"added":g.user_name})
        users = [dict(user) for user in users_cursor]
        
        for user in users:
            del user['_id']
            del user['token']
            del user["user_type"]
        
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
    
    username = content["user_name"]
    password = content["password"]
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

    usr = User(_id=new_id,basari_puani=basari_puani,kayit_tarihi=createdTime,password=password,phone_number=phoneNumber,user_name=username,user_type=userType,token=userToken,name=name,level=level,activate=activated,teacher_name=teacher_name,count=0).__dict__
    usr_proccess = Process(user_name=username,next_exercise=1,now_exercise=0,day="day1",next_day_date=newDate,okey=False).__dict__
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
    phoneNumber = content["phone_number"]
    
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
    usr = Teacher(_id=new_id,kayit_tarihi=createdTime,password=password,phone_number=phoneNumber,user_name=username,user_type=userType,token=userToken,name=name).__dict__
    db.insert_one(collection_name="users",data=usr)
    return jsonify({"message":"öğretmen başarılı bir şekilde eklendi","username": username, "password": password,"token":userToken}), 200


@education_blueprint.route("/deluser", methods=["DELETE"])
def del_user():
    print("Headers:", request.headers)  # Tüm başlıkları yazdır

    if g.user_type != const.admin:
        return jsonify({"error":"lütfen admin hesabı ile giriş yapınız"}),200
    
    name = request.headers.get("username")
    print("name:", name)
    
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


@education_blueprint.route("/updateuser/<string:old_name>", methods=["PUT"])
def update_user(old_name):
    if g.user_type != const.admin:
        return jsonify({"error":"lütfen admin hesabı ile giriş yapınız"}),200
    
    content = request.get_json()
    if content is None or ("new_username" not in content and "new_password" not in content):
        return jsonify({"error": "Eksik bilgi"}), 400
    
    new_username = content.get("new_username")
    new_password = content.get("new_password")
    
    query = {"username": old_name}
    new_values = {}
    if new_username:
        new_values["$set"] = {"username": new_username}
    if new_password:
        new_values["$set"].update({"password": new_password})  # Update instead of overwrite
    
    db = MongoDB(db_name=db_name, url=db_url)
    updated_user = db.update_one("users", query=query, new_values=new_values)

    if updated_user:
        return jsonify({"message": "Kullanıcı başarılı şekilde güncellendi"}), 200
    else:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404


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
        url =  SERVER_IP+"/static/"+name
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
    
    current_datetime = datetime.now()
    current_date = current_datetime.date()
    current_time_str = current_datetime.strftime("%H:%M:%S")
    
    db = MongoDB(url=db_url, db_name=db_name)   

    data = Messages(header=header,sender=g.user_name, receiver=const.admin, content=messages, cender_date=current_date, date=current_time_str).__dict__
    
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
