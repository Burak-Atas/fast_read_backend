from flask import Blueprint,request,jsonify,g

student_blueprint = Blueprint('student', __name__)
from db.db import MongoDB

import const
from dotenv import dotenv_values


env_values = dotenv_values()
db_url = env_values.get("DATABASE_URL")
db_name = env_values.get("DATABASE_NAME")



@student_blueprint.before_request
def check_user_type():
    if g.user_type != const.student or g.user_type != const.admin:
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
    
    speed = speeds[day-1]

    return jsonify({"text":text,"speed":speed})


@student_blueprint.route("/egzersiz_bitti",methods=["POST"])
def egzersiz_bitti():
    content = request.get_json()
    
    
    


