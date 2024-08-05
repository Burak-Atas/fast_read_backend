from flask import Flask, jsonify, request,g
from flask_cors import CORS
from routes.student_blueprint import student_blueprint
from routes.education_blueprint import education_blueprint
import const
app = Flask(__name__)

from db.db import MongoDB
from dotenv import dotenv_values
from model import model
from smtpserver import EmailVerification
from model.model import User,Egzersiz,Story

from jwtgenerate import JWT_Token

env_values = dotenv_values()
db_url = env_values.get("DATABASE_URL")
db_name = env_values.get("DATABASE_NAME")

token_handler= JWT_Token()

app.register_blueprint(student_blueprint, url_prefix='/student')
app.register_blueprint(education_blueprint, url_prefix='/teacher')


CORS(app)


@app.route('/login',methods=["POST"])
def login():
    content = request.get_json()
    if content is None:
        return jsonify({"error":"eksik bilgi doldurunuz"})
    
    if "username" not in content or "password" not in content:
        return jsonify({"error": "kullanıcı adı yada şifre eksik"})
    
    user_name = content["username"]
    password = content["password"]    
    query = {
        "user_name":user_name
    }

    db = MongoDB(db_name=db_name,url=db_url)
    user = db.find_one("users",query=query)
    
    if type(user)!=dict:
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400
    
    if user["password"]!=password:
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400
    
    if user["activate"]==False:
        return jsonify({"message":"lütfen üyeliğinizin aktifliğini bekleyin"}),200
        
    return jsonify({"message":"giriş başarılı","token":user["token"],"name":user["name"]}),200
    
    
@app.before_request
def auth_middleware():
    if request.path != "/login" and request.path != "/contact":
        token = request.headers.get("token")
        
        if token != None:
            decode_token= token_handler.decode_token(token=token)[0]   
            if type(decode_token)!=dict:
                return jsonify({"error":"tekrar giriş yapınız",}),400
                    
            g.user_type = decode_token["role"]
            g.token = token
            g.user_name = decode_token["user_name"]
            if g.user_type == const.student :
                g.level = decode_token["level"]
        else:
            g.user_type = const.admin
            g.user_name = "elvansurel"
            
          #  return jsonify({"error":"yetkisiz erişim"})



@app.route('/contact',methods=["POST"])
def index():
    content = request.get_json()["formData"]
    EmailVerification("batas219@gmail.com",konu=content["subject"],kimden=content["email"])
    return jsonify({"message":"mesajınız gönderildi"}),200



if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
