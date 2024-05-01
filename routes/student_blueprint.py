from flask import Blueprint,request,jsonify,g

student_blueprint = Blueprint('student', __name__)
from db.db import MongoDB
from datetime import datetime

from model.model import Messages
import const
from dotenv import dotenv_values


env_values = dotenv_values()
db_url = env_values.get("DATABASE_URL")
db_name = env_values.get("DATABASE_NAME")



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
    
    
    user_name = user["user_name"]
    user_score = user["basari_puan"]
    complated_user = user["tamamlanan_gun"]
    
      
    return jsonify({"user_name":user_name,"user_score":user_score,"complated_user":complated_user}),200


@student_blueprint.route("/egzersiz",methods=["POST"])
def gune_ait_egzersiz():
    content = request.get_json()
    day = content["day"]

    db = MongoDB(url=db_url,db_name=db_name)
    
    days = db.find_one("days",query={"day":day})    
    if type(days)!=dict:
        return jsonify({"error":"gün bulunamadı"}),400
    
    return jsonify({"egzersiz":days["egzersiz"]}),200


@student_blueprint.route("/egzersiz/<string:day>/<string:name>",methods = ["POST"])
def egzersiz(day,name):
    query = {"egzersizismi":name,"day":day}
    
    db = MongoDB(url=db_url,db_name=db_name)

    egzersiz = db.find_one("egzersiz",query=query)
   
    if type(egzersiz)!=dict:
        return jsonify({"error":"egzersiz bulunamadı"}),400
       
    speeds = egzersiz["speed"]
    text = egzersiz["text"]
    complated_time = egzersiz["time"]
    
    
    speed = speeds[day-1]


    return jsonify({"text":text,"speed":speed,"complated_time":complated_time})


@student_blueprint.route("/egzersiz_bitti",methods=["POST"])
def egzersiz_bitti():
    content = request.get_json()
    
"""
//kullanıcı iletişim işlemleri
"""

@student_blueprint.route("/allmessage", methods=["POST"])
def all_message():

    user_name = g.user_name
    db = MongoDB(url=db_url, db_name=db_name)
    messages_cursor = db.find_many(collection_name="messages", query={"user_name": user_name})    
    messages = list(messages_cursor)
    messages_cursor.close()

    if messages:
        return jsonify(messages), 200
    else:
        return jsonify({"message": "Henüz bir mesajınız yok"}), 404
    
@student_blueprint.route("/sendmessage",methods=["POST"])
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
    
    
    
    