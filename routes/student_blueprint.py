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



def len_exercises(day):
    exercises = db.count_documents("process",query={"day":day})
    len_exercise = len(exercises["exercise"])
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
    
  
    if int(day[-1])<int(process["day"][-1]):
        return jsonify({"egzersiz": days["exercise"],"order":1,"order":len_exercise}), 200
    
    
    if day!= process["day"]:
        return jsonify({"egzersiz": days["exercise"],"order":-1}), 200 
    
    return jsonify({"egzersiz": days["exercise"],"order":process["now_exercise"],"next_exercies":process["next_exercise"]}), 200


def check_last_digits(day):
    try:
        print("day",day)
        last_two_digits = int(day[-2:])
        return last_two_digits,2
    except ValueError:
        try:
            last_one_digit = int(day[-1])
            return last_one_digit,1
        except ValueError:
            return None


@student_blueprint.route("/<string:day>/<string:name>",methods = ["GET"])
def egzersiz(day,name):
    query = {"user_name":g.user_name}

    control  = db.find_one("process",query=query)    
  
    day_digits = check_last_digits(day)
    process_digits = check_last_digits(control["day"])
    print("day digits",day_digits)
    print("process_digits",process_digits)
    
    if day_digits[1] == process_digits[1]:
        if day_digits[0]>process_digits[0]:
            print("burada")
            return jsonify({"error":"tamamlanması gereken gün : "+control["day"]})
        else:
            now_exerscise=db.find_one(collection_name="exercise",query={"name":name})
            data = now_exerscise["data"]
            return jsonify(data),200
    elif day_digits[1] > process_digits[1]: 
        return jsonify({"error":"tamamlanması gereken gün : "+control["day"]})
    
    
    if day[-1] < control["day"][-1]:
        exercise =len_exercises(day=day)
    exercise = control["now_exercise"]
    if exercise>=len_exercise:
        now_exerscise=db.find_one(collection_name="exercise",query={"name":name})
        if type(now_exerscise)!=dict:
            return jsonify({"error":"egzersiz bulunamadı"}),400
        data = now_exerscise["data"]
        return jsonify(data),200
        
    now_exerscise=db.find_one(collection_name="days",query={"day":day})
    print("reis",now_exerscise)
    if type(now_exerscise)!=dict:
        return jsonify({"error":"egzersiz bulunamadı"}),400
    
    if day==control["day"]:
        dnd = find_exercise(now_exerscise["exercise"],name,exercise)
        print("dnd",dnd)
        if not dnd :
            return jsonify({"error":"lütfen önceki egzersizleri tamamlayın"}),400    
        
    exercise_data =db.find_one(collection_name="exercise",query={"name":name})
    
    data = exercise_data["data"]

    return jsonify(data),200

def find_exercise(exercise_list, exercise_name, exercise_order):
    for i, exercise in enumerate(exercise_list):
        if exercise == exercise_name:
            if i == int(exercise_order):
                return True
            else:
                return False
    return False




@student_blueprint.route("/newday",methods=["POST"])
def new_day():
    user_name = g.user_name
    process = db.find_one(collection_name="process",query={"user_name":user_name})
    
    if type(process)!=dict:
        return jsonify({"error":"lütfen daha sonra tekrar deneyein"}),500
    
    createdTime = datetime.now()
    date = createdTime.strftime("%Y-%m-%d")
    if process["okey"]:
        print("deneme",int(process["day"][-2:]))
        if int(process["day"][-2:])>24:
            process = db.find_one(collection_name="users",query={"user_name":user_name})
            count = process["count"] + 1
            if count > 3:
                return jsonify({"message":"daha fazla kurs hakkınız kalmadı lütfen yetkili kişi ile iletişime geçin"}),400
            db.update_one(collection_name="users",query={"user_name":user_name},data={"count":count})
            return jsonify({"message":"kursu başarılı bir şekilde tamamladınız"}),200
        if date>=process["next_day_date"]:
            newDate = (createdTime + timedelta(days=1)).strftime("%Y-%m-%d")
            db.update_one(collection_name="process",query={"user_name": user_name},data={"next_day_date":newDate,"next_exercise":1,"now_exercise":0,"day":"day2","okey":False})
            return jsonify({"message":"yeni güne geçebilirsiniz"}),200
    else:
        return jsonify("egzersizleri tamamlayın"),200   
        

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


    