from flask import Blueprint,request,jsonify,g,Response

student_blueprint = Blueprint('student', __name__)
from db.db import MongoDB
from datetime import datetime,timedelta

from model.model import Messages
import const
import config


db_url = config.DATABASE_URL
db_name = config.DATABASE_NAME



db = MongoDB(url=db_url, db_name=db_name)


def total_exercises():
    # Counted per call: a module-level count queried the DB at import time
    # and went stale when exercises were added.
    return db.count_documents("exercise",query={})


def _safe_document(content):
    """Drop keys MongoDB could interpret as operators or paths."""
    return {k: v for k, v in content.items()
            if isinstance(k, str) and k and not k.startswith("$") and "." not in k}

def _student_level():
    """Level from the student's token as int, or None if missing/invalid."""
    try:
        return int(g.level)
    except (AttributeError, TypeError, ValueError):
        return None


@student_blueprint.before_request
def check_user_type():
    if request.method == "OPTIONS":
        return None
    if getattr(g, "user_type", None) != const.student:
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
    user_score = user.get("basari_puani")
    process_order = process.get("day")
    process_order_exercise = process.get("now_exercise")
    
    days = db.find_one(collection_name="days",query={"day":process_order})
    if type(days)!=dict:
        return jsonify({"error":"lütfen tekrar giriş yapın"}),400
    len_exesice = len(days.get("exercise") or [])
    
    now = datetime.now()

    formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")

    db.update_one(collection_name="users",query={"user_name":user_name},data={"last_seen_data":formatted_now})
        
    complated_day = user.get("tamamlanan_gun", 0)
    return jsonify({"user_name":user_name,"user_score":user_score,"complated_days":complated_day,"process_order":process_order_exercise,"all_exercise":len_exesice}),200





@student_blueprint.route("/<string:day>", methods=["GET"])
def gune_ait_egzersiz(day):
    level = _student_level()
    if level is None:
        return jsonify({"error":"tekrar giriş yapınız"}),401
    user_name = g.user_name
    days = db.find_one(collection_name="days", query={"day": day,"level":level})  
    
    if type(days) != dict:
        return jsonify({"error": "gün bulunamadı"}), 400  
    process = db.find_one(collection_name="process", query={"user_name":user_name}) 
    
    if type(process) != dict:
        return jsonify({"error": "hatalı işlem yaptınız"}), 400  
    
    day_digits = check_last_digits(day)
    process_digits = check_last_digits(process.get("day", ""))
    if day_digits is None or process_digits is None:
        return jsonify({"error": "gün bulunamadı"}), 400
    if day_digits[1] == process_digits[1]:
        if day_digits[0]==process_digits[0]:
            return jsonify({"egzersiz": days["exercise"],"order":process["now_exercise"],"next_exercies":process["next_exercise"]}), 200
        elif day_digits[0]<=process_digits[0]:
            return jsonify({"egzersiz": days["exercise"],"order":total_exercises()}), 200
            
    elif day_digits[1] > process_digits[1]: 
        return jsonify({"error":"tamamlanması gereken gün : "+process["day"],"egzersiz":days["exercise"],"order":-1})
    
    return jsonify({"egzersiz": days["exercise"],"order":-1}), 200 
    


def check_last_digits(day):
    if not isinstance(day, str) or not day:
        return None
    try:
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
    if type(control) != dict:
        return jsonify({"error": "hatalı işlem yaptınız"}), 400
    level = _student_level()
    if level is None:
        return jsonify({"error":"tekrar giriş yapınız"}),401

    day_digits = check_last_digits(day)
    process_digits = check_last_digits(control.get("day", ""))
    if day_digits is None or process_digits is None:
        return jsonify({"error": "gün bulunamadı"}), 400
    
    if day_digits[1] == process_digits[1]:
        if day_digits[0]>process_digits[0]:
            return jsonify({"error":"tamamlanması gereken gün : "+control["day"]})
        else:
            
            now_exerscise=db.find_one(collection_name="exercise",query={"name":name,"level":level})
            if type(now_exerscise)!=dict:
                return jsonify({"error":"egzersiz bulunamadı"}),400
            data = now_exerscise.get("data")
            return jsonify(data),200
    elif day_digits[1] > process_digits[1]: 
        return jsonify({"error":"tamamlanması gereken gün : "+control["day"]})
    
    
    exercise = control.get("now_exercise") or 0
    if exercise>=total_exercises():
        now_exerscise=db.find_one(collection_name="exercise",query={"name":name,"level":level})
        if type(now_exerscise)!=dict:
            return jsonify({"error":"egzersiz bulunamadı"}),400
        data = now_exerscise["data"]
        return jsonify(data),200
        
    now_exerscise=db.find_one(collection_name="days",query={"day":day})
    if type(now_exerscise)!=dict:
        return jsonify({"error":"egzersiz bulunamadı"}),400
    
    if day==control["day"]:
        dnd = find_exercise(now_exerscise["exercise"],name,exercise)
        if not dnd :
            return jsonify({"error":"lütfen önceki egzersizleri tamamlayın"}),400    
        
    exercise_data =db.find_one(collection_name="exercise",query={"name":name,"level":level})
    if type(exercise_data)!=dict:
        return jsonify({"error":"egzersiz bulunamadı"}),400
    data = exercise_data.get("data")

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
    if process.get("okey"):
        days_digits = check_last_digits(process.get("day", ""))
        if days_digits is None:
            return jsonify({"error":"lütfen daha sonra tekrar deneyein"}),500
        if days_digits[1]==2 and days_digits[0]>24:
            found_user = db.find_one(collection_name="users",query={"user_name":user_name})
            if type(found_user)!=dict:
                return jsonify({"error":"lütfen daha sonra tekrar deneyein"}),500
            count = found_user.get("count", 0) + 1
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
        else:
            # NOTE: the original code had a bare `date >= next_day_date`
            # expression here, so the one-day wait was never enforced.
            # Left unenforced to keep current behavior; see review notes.
            newDate = (createdTime + timedelta(days=1)).strftime("%Y-%m-%d")
            new_day_digits = days_digits[0]+1
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
    
    return jsonify({"message":"kursa tekrara başlayabilirsiniz","kalan hak":3-users.get("count", 0)})


@student_blueprint.route("/<string:day>/<string:name>/exerciseisover", methods=["POST"])
def egzersiz_bitti(day,name):
    user_name = g.user_name 
    content = request.get_json(silent=True)
    if not isinstance(content, dict):
        return jsonify({"error": "Hatalı işlem yaptınız"}),400
    level = _student_level()
    if level is None:
        return jsonify({"error":"tekrar giriş yapınız"}),401

    content = _safe_document(content)
    content.pop("_id", None)
    content["user_name"]=user_name
    content["exercise_name"]=name
    content["execise_day"]=day

    process = db.find_one(collection_name="process", query={"user_name": user_name})
    day_exercise = db.find_one(collection_name="days", query={"day": day,"level":level})
    if type(process)!=dict or type(day_exercise)!=dict:
        return jsonify({"error": "Hatalı işlem yaptınız"}),400
    
    day_digits = check_last_digits(day)
    process_digits = check_last_digits(process.get("day", ""))
    if day_digits is None or process_digits is None:
        return jsonify({"error": "Hatalı işlem yaptınız"}),400
    
    if day_digits[1] == process_digits[1]:
        if day_digits[0]>process_digits[0]:
            return jsonify({"error":"tamamlanması gereken gün : "+process["day"]})
    elif day_digits[1] > process_digits[1]: 
        return jsonify({"error":"tamamlanması gereken gün : "+process["day"]})
    
    
    exercises =day_exercise["exercise"]
    len_day_exercise = len(exercises)
    now_exercise = process.get("now_exercise") 
    
    # kullancıının kaldığı egzersiz
    # gelen istekteki egzersizin aynı mı kontrolü
    dnd = find_exercise(exercises,name,now_exercise)

    if dnd:
        now_exercise = process.get("next_exercise") or 1
        new_next_exercise = now_exercise + 1
        db.update_one(collection_name="process", query={"user_name": user_name}, data={"next_exercise": new_next_exercise, "now_exercise": now_exercise})
        if not process.get("okey"):
            if now_exercise>=len_day_exercise:
                found_user = db.find_one(collection_name="users",query={"user_name": user_name}) 
                if not isinstance(found_user, dict):
                    return jsonify({"error": "Hatalı işlem yaptınız"}),400
                complated_day = (found_user.get("tamamlanan_gun") or 0) + 1
                new_data = {"tamamlanan_gun":complated_day}
                db.insert_one(collection_name="after_exercise",data=content)
                db.update_one(collection_name="process",query={"user_name": user_name},data={"okey":True})
                db.update_one(collection_name="users",query={"user_name": user_name},data=new_data)   
                return jsonify({"message":"tüm egzersizleri başarılı şeklilde tamamladınız"}),200
            db.insert_one(collection_name="after_exercise",data=content)
            return jsonify({"message":"sıradaki egzersize geçebilirsinz"}),200        
        return jsonify({"message": "Tüm egzersizleri başarılı bir şekilde tamamladınız. Gelecek gün: " + str(process.get("next_day_date", ""))}), 200 
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
    # Messages are stored with a "receiver" field (model.Messages); the
    # legacy "user_name" field is still matched for older documents.
    recipients = ["all", g.user_name]
    query = {
        "$or": [
            {"receiver": {"$in": recipients}},
            {"user_name": {"$in": recipients}}
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
        # Explicit JSON type: a bare string response is served as text/html,
        # letting message content run as script if the URL is opened directly.
        return Response(json_util.dumps(messages), status=200, mimetype="application/json")
    else:
        return jsonify({"message": "Henüz bir mesajınız yok"}), 404



@student_blueprint.route("/knowledge",methods = ["GET"])
def knowledge():
    db = MongoDB(url=db_url, db_name=db_name)
    res = db.find_one(collection_name="knowledge", query={"publish":True})
    if type(res) != dict:
        return jsonify({"error": "faydalı bilgi bulunamadı"}), 404
        
    return jsonify(res.get("content")), 200