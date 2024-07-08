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



db = MongoDB(url=db_url, db_name=db_name)
len_exercise = db.count_documents("exercise",query={})
print(len_exercise)

@student_blueprint.before_request
def check_user_type():
    if g.user_type not in {const.student, const.teacher}:
        return jsonify({"error": "yetkisiz erişim"}), 403


@student_blueprint.route('/dashboard',methods=["GET"])
def hello():   
    user_name = g.user_name 
    
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
    days = db.find_one(collection_name="days", query={"day": day})  
    
    if type(days) != dict:
        return jsonify({"error": "gün bulunamadı"}), 400  
    process = db.find_one(collection_name="process", query={"user_name":user_name}) 
    
    if type(process) != dict:
        return jsonify({"error": "hatalı işlem yaptınız"}), 400  
    
    print(day)
    print(process["day"])
  
    if int(day[-1])<int(process["day"][-1]):
        return jsonify({"egzersiz": days["exercise"],"order":1,"order":len_exercise}), 200
    
    
    if day!= process["day"]:
        return jsonify({"egzersiz": days["exercise"],"order":-1}), 200 
    
    return jsonify({"egzersiz": days["exercise"],"order":process["now_exercise"],"next_exercies":process["next_exercise"]}), 200




@student_blueprint.route("/<string:day>/<string:name>",methods = ["GET"])
def egzersiz(day,name):
    query = {"user_name":g.user_name}

    control  = db.find_one("process",query=query)    
    
    if int(day[-1])<int(control["day"][-1]):
        now_exerscise=db.find_one(collection_name="exercise",query={"name":name})
        data = now_exerscise["data"]
        return jsonify(data),200
    
    if day[-1] > control["day"][-1]:
        return jsonify({"error":"tamamlanması gereken gün : "+control["day"]})
    if day[-1] < control["day"][-1]:
        exercise =len_exercise
    exercise = control["now_exercise"]
    if exercise>=len_exercise:
        now_exerscise=db.find_one(collection_name="exercise",query={"name":name})
        if type(now_exerscise)!=dict:
            return jsonify({"error":"egzersiz bulunamadı"}),400
        data = now_exerscise["data"]
        return jsonify(data),200
        
    now_exerscise=db.find_one(collection_name="exercise",query={"order":exercise})
    if type(now_exerscise)!=dict:
        return jsonify({"error":"egzersiz bulunamadı"}),400
    
    if day==control["day"]:
        if name != now_exerscise["name"]:
            return jsonify({"error":"tamamlanması gereken egzersiz :"+now_exerscise["name"]}),400    
    
    data = now_exerscise["data"]
    #text = now_exerscise["text"]
    #complated_time = now_exerscise["time"]
    #return jsonify({"text":text,"speed":speed,"complated_time":complated_time})
    #datas = {"speed":data[exercise-1]["speed"][exercise-1],"text":data[exercise-1]["text"][exercise-1]}
    return jsonify(data),200


@student_blueprint.route("/newday",methods=["POST"])
def new_day():
    user_name = g.user_name
    process = db.find_one(collection_name="process",query={"user_name":user_name})
    
    if type(process)!=dict:
        return jsonify({"error":"lütfen daha sonra tekrar deneyein"}),500
    
    createdTime = datetime.now()
    date = createdTime.strftime("%Y-%m-%d")
    if process["okey"]:
        if date>=process["next_day_date"]:
            newDate = (createdTime + timedelta(days=1)).strftime("%Y-%m-%d")
            db.update_one(collection_name="process",query={"user_name": user_name},data={"next_day_date":newDate,"next_exercise":1,"now_exercise":0,"day":"day2","okey":False})
            return jsonify({"message":"yeni güne geçebilirsiniz"}),200
    else:
        order = process["now_exercise"]
        exercise = db.find_one(collection_name="exercise",query={"order":order})
        if type(exercise)!=dict:
            return jsonify({"error":"lütfen daha sonra tekrar deneyein"}),500
        return jsonify("egzersizleri tamamlayın",exercise["name"]),200   
        

@student_blueprint.route("/<string:name>/exerciseisover", methods=["POST"])
def egzersiz_bitti(name):
    user_name = g.user_name 
    db = MongoDB(url=db_url, db_name=db_name)
    process = db.find_one(collection_name="process", query={"user_name": user_name})
    exercise = db.find_one(collection_name="exercise",query={"name":name})
    print(exercise)
    
    if not isinstance(process, dict):
        return jsonify({"error": "Hatalı işlem yaptınız"}),400
    
    nw = process.get("now_exercise")
    print(nw,exercise.get("order"))
    if nw == exercise.get("order"):
        print("burada")
        now_exercise = process.get("next_exercise") 
        new_next_exercise = now_exercise + 1
        db.update_one(collection_name="process", query={"user_name": user_name}, data={"next_exercise": new_next_exercise, "now_exercise": now_exercise})
    
        if process["okey"]==False:
            if now_exercise>=len_exercise:
                found_user = db.find_one(collection_name="users",query={"user_name": user_name}) 
                print("kullancıı bulundu")
                if not isinstance(found_user, dict):
                    return jsonify({"error": "Hatalı işlem yaptınız"}),400
                complated_day = found_user.get("tamamlanan_gun")
                complated_day+=1
                new_data = {"tamamlanan_gun":complated_day}
                db.update_one(collection_name="process",query={"user_name": user_name},data={"okey":True})
                db.update_one(collection_name="users",query={"user_name": user_name},data=new_data)
                                
                return jsonify({"message":"tüm egzersizleri başarılı şeklilde tamamladınız"}),200
        
            return jsonify({"message":"sıradaki egzersize geçebilirsinz"}),200        
        return jsonify({"message": "Tüm egzersizleri başarılı bir şekilde tamamladınız. Gelecek gün: " + process["next_day_date"]}), 200 
    return jsonify("egzersizi daha önce tamamladınız"),200
        
"""
//kullanıcı iletişim işlemleri
"""
    
from bson import json_util

@student_blueprint.route("/allmessages", methods=["GET"])
def all_message():
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


    