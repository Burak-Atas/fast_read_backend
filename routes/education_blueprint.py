from flask import Blueprint, request, jsonify, g
from db.db import MongoDB
from dotenv import dotenv_values
import const
from db.db import MongoDB
from jwtgenerate import JWT_Token
from model.model import Story,Egzersiz,Process,User,Video,Messages
from datetime import datetime, timedelta
from bson import ObjectId
import os


env_values = dotenv_values()
db_url = env_values.get("DATABASE_URL")
db_name = env_values.get("DATABASE_NAME")


userId = 0


education_blueprint = Blueprint('education_blueprint', __name__)

@education_blueprint.before_request
def check_user_type():
    if g.user_type != const.teacher:
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

@education_blueprint.route("/user", methods=["GET"])
def user():
    db = MongoDB(url=db_url, db_name=db_name)
    users_cursor = db.find_many(collection_name="users", query=None)
    users = [dict(user) for user in users_cursor]
    
    # Remove _id field from each dictionary
    for user in users:
        del user['_id']
        del user['token']
        del user["user_type"]
    
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

    usr = User(_id=new_id,basari_puani=basari_puani,kayit_tarihi=createdTime,password=password,phone_number=phoneNumber,user_name=username,user_type=userType,token=userToken,name=name,level=level).__dict__
    usr_proccess = Process(user_name=username,next_exercise=1,now_exercise=0,day="day1",next_day_date=newDate,okey=False).__dict__
    db.insert_one(collection_name="users",data=usr)
    db.insert_one(collection_name="process",data=usr_proccess)
    return jsonify({"message":"kullanıcı eklendi","username": username, "password": password,"token":userToken}), 200


@education_blueprint.route("/deluser/<string:name>", methods=["DELETE"])
def del_user(name):
    print(name)
    query = {"user_name": name}
    db = MongoDB(db_name=db_name, url=db_url)
    deleted_user = db.delete_one("users", query=query)

    if deleted_user:
        return jsonify({"message": "Kullanıcı başarılı şekilde silindi"}), 200
    else:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404


@education_blueprint.route("/alldeluser",methods=["DELETE"])
def all_del_user():
    db = MongoDB(url=db_url,db_name=db_name)

    db.delete_many(collection_name="users",query={})
    
    return jsonify(),200


@education_blueprint.route("/updateuser/<string:old_name>", methods=["PUT"])
def update_user(old_name):
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
@education_blueprint.route("/addvideo",methods=["POST"])
def upload_video():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        filename = file.filename
        file.save(os.path.join(education_blueprint.config['UPLOAD_FOLDER'], filename))
        
        
        return jsonify({"message":"başarılı bir şekilde dosya yüklendi"}),200   
    
@education_blueprint.route("/videos",methods=["GET"])
def videos():
    db = MongoDB(url=db_url, db_name=db_name)
    videos_curser = db.find_many(collection_name="videos", query=None)
    
    # Convert Cursor object to a list of dictionaries
    videos = [dict(video) for user in videos_curser]
    
    # Convert ObjectId to string in each dictionary
    for video in videos:
        video['_id'] = str(video['_id'])
    
    # Close the cursor
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

@education_blueprint.route("/video/delvideo", methods=["DELETE"])
def del_video():
    content = request.get_json()
    if "video_name" not in content:
        return jsonify({"error": "Video adı belirtilmedi."}), 400
    
    video_name = content["video_name"]
    db = MongoDB(url=db_url, db_name=db_name)
    
    deleted_video = db.delete_one(collection_name="videos", query={"video_name": video_name})
    db.close()
    
    if deleted_video.deleted_count == 1:
        return jsonify({"message": "Video başarıyla silindi."}), 200
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
    if "messages" not in content:
        return jsonify({"error":"hatalı işlem yaptınız"}),400
    
    messages = content["messages"]
    db = MongoDB(url=db_url,db_name=db_name)   
    current_datetime = datetime.now()
    current_date = current_datetime.date()
    current_time = current_datetime.time()
    
    data = Messages(sender=g.user_name,receiver=const.admin,read=False,messages = messages,cender_date=current_date,sender_time=current_time).__dict__
    db.insert_one(collection_name="messages",data=data)
    
    return jsonify({"messages":"mesajınız gönderildi"}),200
    
    
@education_blueprint.route("/delmessage",methods=["POST"])
def del_message():
    user_name = g.user_name
    content = request.get_json()
    
    message_id =content["message_id"]
    


"""
    KULLANICI BAZLI  İŞLMELER
"""  



