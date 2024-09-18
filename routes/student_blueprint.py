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
    exercises = db.find_one("days",query={"day":day})
    print("deneme",len(exercises["exercise"])) 
    return len(exercises["exercise"])

@student_blueprint.before_request
def check_user_type():
    print("dneem")


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
    
    now = datetime.now()

    formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")

    db.update_one(collection_name="users",query={"user_name":user_name},data={"last_seen_data":formatted_now})
        
    complated_day = user["tamamlanan_gun"]
    return jsonify({"user_name":user_name,"user_score":user_score,"complated_days":complated_day,"process_order":process_order_exercise,"all_exercise":len_exesice}),200





@student_blueprint.route("/<string:day>", methods=["GET"])
def gune_ait_egzersiz(day):
    level = g.level
    print("level",level)
    user_name = g.user_name
    days = db.find_one(collection_name="days", query={"day": day,"level":int(level)})  
    
    if type(days) != dict:
        return jsonify({"error": "gün bulunamadı"}), 400  
    process = db.find_one(collection_name="process", query={"user_name":user_name}) 
    
    if type(process) != dict:
        return jsonify({"error": "hatalı işlem yaptınız"}), 400  
    
    day_digits = check_last_digits(day)
    process_digits = check_last_digits(process["day"])
    print("day digits",day_digits)
    print("process",process_digits)
    if day_digits[1] == process_digits[1]:
        if day_digits[0]==process_digits[0]:
            return jsonify({"egzersiz": days["exercise"],"order":process["now_exercise"],"next_exercies":process["next_exercise"]}), 200
        elif day_digits[0]<=process_digits[0]:
            return jsonify({"egzersiz": days["exercise"],"order":len_exercise}), 200
            
    elif day_digits[1] > process_digits[1]: 
        print("hata daydigtitn ads")
        return jsonify({"error":"tamamlanması gereken gün : "+process["day"],"egzersiz":days["exercise"],"order":-1})
    
    if day!= process["day"]:
        return jsonify({"egzersiz": days["exercise"],"order":-1}), 200 
    


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
        days_digits = check_last_digits(process["day"])
        if days_digits[1]==2:
            if days_digits[0]>24:
                process = db.find_one(collection_name="users",query={"user_name":user_name})
                count = process["count"] + 1
                if count > 3:
                    return jsonify({"message":"daha fazla kurs hakkınız kalmadı lütfen yetkili kişi ile iletişime geçin"}),400
                if count==1:     
                    now = datetime.now()
                    formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")
                    data = {"count":count,"endDate":formatted_now}
                else:
                    data = {"count":count}
                db.update_one(collection_name="users",query={"user_name":user_name},data=data)
                return jsonify({"message":"kursu başarılı bir şekilde tamamladınız"}),200
            print("deneme")
        else:
            date>=process["next_day_date"]
            newDate = (createdTime + timedelta(days=1)).strftime("%Y-%m-%d")
            day = process["day"]
            day_digits = check_last_digits(day)
            new_day_digits = day_digits[0]+1
            new_day = "day" + str(new_day_digits)
            db.update_one(collection_name="process",query={"user_name": user_name},data={"next_day_date":newDate,"next_exercise":1,"now_exercise":0,"day":new_day,"okey":False})
            return jsonify({"message":"yeni güne geçebilirsiniz"}),200
    else:
        return jsonify("egzersizleri tamamlayın"),200 

@student_blueprint.route("/newcourse",methods=["POST"])
def new_course():
    user_name = g.user_name
    
    process = db.find_one(collection_name="process",query={"user_name":user_name})
    users = db.find_one(collection_name="users",query={"user_name":user_name})
    
    if type(process)!=dict:
        return jsonify({"error":"lütfen daha sonra tekrar deneyein"}),500
    if type(users)!=dict:
        return jsonify({"error":"lütfen daha sonra tekrar deneyein"}),500
    createdTime = datetime.now()
    newDate = (createdTime + timedelta(days=1)).strftime("%Y-%m-%d")
    db.update_one(collection_name="process",query={"user_name":user_name},data={"now_exercise":0,"next_exercise":1,"day":"day1","next_day_date":newDate,"okey":False})
    db.update_one(collection_name="users",query={"user_name":user_name},data={"tamamlanan_gun":0})
    
    return jsonify({"message":"kursa tekrara başlayabilirsiniz","kalan hak":3-users["count"]})


@student_blueprint.route("/<string:day>/<string:name>/exerciseisover", methods=["POST"])
def egzersiz_bitti(day,name):
    user_name = g.user_name 
    content = request.get_json()
    
    
    content["user_name"]=user_name
    content["exercise_name"]=name
    content["execise_day"]=day

    process = db.find_one(collection_name="process", query={"user_name": user_name})
    day_exercise = db.find_one(collection_name="days", query={"day": day})
    
    day_digits = check_last_digits(day)
    process_digits = check_last_digits(process["day"])
    
    if day_digits[1] == process_digits[1]:
        if day_digits[0]>process_digits[0]:
            return jsonify({"error":"tamamlanması gereken gün : "+process["day"]})
    elif day_digits[1] > process_digits[1]: 
        return jsonify({"error":"tamamlanması gereken gün : "+process["day"]})
    
    
    exercises =day_exercise["exercise"]
    len_day_exercise = len(exercises)
    print(exercises)
    now_exercise = process.get("now_exercise") 
    
    # kullancıının kaldığı egzersiz
    # gelen istekteki egzersizin aynı mı kontrolü
    dnd = find_exercise(exercises,name,now_exercise)

    if dnd:
        now_exercise = process.get("next_exercise") 
        new_next_exercise = now_exercise + 1
        db.update_one(collection_name="process", query={"user_name": user_name}, data={"next_exercise": new_next_exercise, "now_exercise": now_exercise})
        if process["okey"]==False:
            if now_exercise>=len_day_exercise:
                found_user = db.find_one(collection_name="users",query={"user_name": user_name}) 
                if not isinstance(found_user, dict):
                    return jsonify({"error": "Hatalı işlem yaptınız"}),400
                complated_day = found_user.get("tamamlanan_gun")
                complated_day+=1
                new_data = {"tamamlanan_gun":complated_day}
                db.insert_one(collection_name="after_exercise",data=content)
                db.update_one(collection_name="process",query={"user_name": user_name},data={"okey":True})
                db.update_one(collection_name="users",query={"user_name": user_name},data=new_data)   
                return jsonify({"message":"tüm egzersizleri başarılı şeklilde tamamladınız"}),200
            db.insert_one(collection_name="after_exercise",data=content)
            return jsonify({"message":"sıradaki egzersize geçebilirsinz"}),200        
        return jsonify({"message": "Tüm egzersizleri başarılı bir şekilde tamamladınız. Gelecek gün: " + process["next_day_date"]}), 200 
    return jsonify({"message":"lütfen kaldığınız egzersizi tamamlayın"}) ,400 
    
    """
    user_name = g.user_name 
    db = MongoDB(url=db_url, db_name=db_name)
    process = db.find_one(collection_name="process", query={"user_name": user_name})
    
    if not isinstance(process, dict):
        return jsonify({"error": "Hatalı işlem yaptınız"}),400

    
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
    """  
"""
//kullanıcı iletişim işlemleri
"""
    
from bson import json_util

@student_blueprint.route("/allmessages", methods=["GET"])
def all_message():
    # Query to find messages with receiver as 'all' or 'user_name'
    query = {
        "$or": [
            {"user_name": "all"},
            {"user_name": g.user_name}
        ]
    }
    
    # Find messages based on the query
    messages_cursor = db.find_many(collection_name="messages", query=query)
    
    # Convert cursor to list
    messages = list(messages_cursor)
    messages_cursor.close()
    
    if messages:
        # Convert ObjectId to string for each message
        for message in messages:
            message['_id'] = str(message['_id'])
        return json_util.dumps(messages), 200
    else:
        return jsonify({"message": "Henüz bir mesajınız yok"}), 404



@student_blueprint.route("/knowledge",methods = ["GET"])
def knowledge():
    db = MongoDB(url=db_url, db_name=db_name)
    res = db.find_one(collection_name="knowledge", query={"publish":True})
        
    return jsonify(res["content"]), 200