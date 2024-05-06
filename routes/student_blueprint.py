from flask import Blueprint,request,jsonify,g

student_blueprint = Blueprint('student', __name__)
from db.db import MongoDB
from datetime import datetime,timedelta

from model.model import Messages
import const
from dotenv import dotenv_values


env_values = dotenv_values()
db_url = env_values.get("DATABASE_URL")
db_name = env_values.get("DATABASE_NAME")
len_exesice = env_values.get("EXERSİCE")


@student_blueprint.before_request
def check_user_type():
    if g.user_type not in {const.student, const.teacher}:
        return jsonify({"error": "yetkisiz erişim"}), 403


@student_blueprint.route('/dashboard',methods=["GET"])
def hello():   
    user_name = g.user_name 
    
    db = MongoDB(url=db_url,db_name=db_name)
    user= db.find_one(collection_name="users",query={"user_name":user_name})
    if type(user)!=dict:
        return jsonify({"error":"lütfen tekrar giriş yapın"}),400
    
    
    
    process= db.find_one(collection_name="process",query={"user_name":user_name})
    
    
    
    if type(process)!=dict:
        return jsonify({"error":"lütfen tekrar giriş yapın"}),400
        
    
    user_name = user["user_name"]
    user_score = user["basari_puani"]
    process_order = process["day"]
    process_order_exercise = process["now_exercise"]
    
    days = db.find_one(collection_name="days",query={"day":process_order})
    
    len_exesice = len(days["exercise"])
    if type(days)!=dict:
        return jsonify({"error":"lütfen tekrar giriş yapın"}),400
        
        
    complated_day = user["tamamlanan_gun"]
    return jsonify({"user_name":user_name,"user_score":user_score,"complated_days":complated_day,"process_order":process_order_exercise,"all_exercise":len_exesice}),200





@student_blueprint.route("/<string:day>", methods=["GET"])
def gune_ait_egzersiz(day):
    level = g.level
    user_name = g.user_name
    db = MongoDB(url=db_url, db_name=db_name)
    days = db.find_one(collection_name="days", query={"day": day,"level":level})  
    if type(days) != dict:
        return jsonify({"error": "gün bulunamadı"}), 400  
    process = db.find_one(collection_name="process", query={"user_name":user_name}) 
    if type(process) != dict:
        return jsonify({"error": "hatalı işlem yaptınız"}), 400  
    if day!= process["day"]:
        return jsonify({"egzersiz": days["exercise"],"order":-1}), 200 
    
    return jsonify({"egzersiz": days["exercise"],"order":process["now_exercise"],"next_exercies":process["next_exercise"]}), 200




@student_blueprint.route("/<string:day>/<string:name>",methods = ["GET"])
def egzersiz(day,name):
    db = MongoDB(url=db_url,db_name=db_name)
    query = {"user_name":g.user_name}

    control  = db.find_one("process",query=query)    
    
    if day[-1] > control["day"][-1]:
        return jsonify({"error":"tamamlanması gereken gün : "+control["day"]})
    
    exercise = control["now_exercise"]
    print(day,exercise)
    now_exerscise=db.find_one(collection_name="exercise",query={"order":exercise})
    if type(now_exerscise)!=dict:
        return jsonify({"error":"egzersiz bulunamadı"}),400
    
    if day==control["day"]:
        if name != now_exerscise["name"]:
            return jsonify({"error":"tamamlanması gereken egzersiz :"+now_exerscise["name"]}),400    
    
    speeds = now_exerscise["speed"]
    #text = now_exerscise["text"]
    #complated_time = now_exerscise["time"]
    speed = speeds[int(day[-1])-1]
    #return jsonify({"text":text,"speed":speed,"complated_time":complated_time})
    return jsonify({"speed":speed}),200




@student_blueprint.route("/exerciseisover", methods=["POST"])
def egzersiz_bitti():
    user_name = g.user_name 
    db = MongoDB(url=db_url, db_name=db_name)
    process = db.find_one(collection_name="process", query={"user_name": user_name})
    
    if not isinstance(process, dict):
        return jsonify({"error": "Hatalı işlem yaptınız"}),400
    
    now_exercise = process.get("next_exercise") 
    
    if process["okey"]==False:
        print(now_exercise)
        print("eln"+len_exesice)
        if now_exercise>=int(len_exesice):
            found_user = db.find_one(collection_name="users",query={"user_name": user_name}) 
            if not isinstance(found_user, dict):
                return jsonify({"error": "Hatalı işlem yaptınız"}),400
            complated_day = found_user.get("tamamlanan_gun")
            complated_day+=1
            
            new_data = {"tamamlanan_gun":complated_day}
            db.update_one(collection_name="users",query={"user_name": user_name},data=new_data)
            db.update_one(collection_name="process",query={"user_name": user_name},data={"okey":True})
            
            return jsonify({"message":"tüm egzersizleri başarılı şeklilde tamamladınız"}),200
    
        new_next_exercise = now_exercise + 1
        print(new_next_exercise)
        db.update_one(collection_name="process", query={"user_name": user_name}, data={"next_exercise": new_next_exercise, "now_exercise": now_exercise})
        return jsonify({"message":"sıradaki egzersize geçebilirsinz"}),200
    
    createdTime = datetime.now()
    date = createdTime.strftime("%Y-%m-%d")
    
    if date==process["next_day_date"]:
        if now_exercise>=int(len_exesice):
            newDate = (createdTime + timedelta(days=1)).strftime("%Y-%m-%d")
            db.update_one(collection_name="process",query={"user_name": user_name},data={"next_day_date":newDate,"next_exercise":1,"now_exercise":0,"day":"day2","okey":False})
            return jsonify({"message":"yeni güne geçebilirsiniz"}),200
            
    
    return jsonify({"message": "Tüm egzersizleri başarılı bir şekilde tamamladınız. Gelecek gün: " + process["next_day_date"]}), 200
    
    
        
"""
//kullanıcı iletişim işlemleri
"""
    
from bson import json_util

@student_blueprint.route("/allmessages", methods=["GET"])
def all_message():
    db = MongoDB(url=db_url, db_name=db_name)
    messages_cursor = db.find_many(collection_name="messages", query={})    
    messages = list(messages_cursor)
    messages_cursor.close()
    if messages:
        # Convert ObjectId to string for each message
        for message in messages:
            message['_id'] = str(message['_id'])
        return json_util.dumps(messages), 200
    else:
        return jsonify({"message": "Henüz bir mesajınız yok"}), 404


    