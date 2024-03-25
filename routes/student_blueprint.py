from flask import Blueprint,request,jsonify

student_blueprint = Blueprint('student', __name__)
from db.db import MongoDB



from dotenv import dotenv_values


env_values = dotenv_values()
db_url = env_values.get("DATABASE_URL")
db_name = env_values.get("DATABASE_NAME")


@student_blueprint.route('/')
def hello():
    
    return 'Merhaba, Blueprint!'


@student_blueprint.route("/egzersiz",methods=["POST"])
def gune_ait_egzersiz():
    content = request.get_json()
    day = content["day"]

    db = MongoDB(url=db_url,db_name=db_name)
    
    days = db.find_one("days",query={"day":day})    
    if type(days)!=dict:
        return jsonify({"error":"gün bulunamadı"}),400
    
    return jsonify({"egzersiz":days["egzersiz"]}),200


#egzersiz dönderme işlemleri yapılacak
@student_blueprint.route("/egzersiz/<string:name>",methods = ["POST"])
def egzersiz(name):
    query = {"egzersizismi":name}
    
    db = MongoDB(url=db_url,db_name=db_name)

    egzersiz = db.find_one("egzersiz",query=query)
   
    if type(egzersiz)!=dict:
        return jsonify({"error":"egzersiz bulunamadı"}),400
    
    

    return f"Egzersiz ID'si: {egzersiz}"


@student_blueprint.route("/egzersiz_bitti",methods=["POST"])
def egzersiz_bitti():
    content = request.get_json()
    
    
    


