from flask import Flask, jsonify, request,g
from flask_cors import CORS
from routes.student_blueprint import student_blueprint
from routes.education_blueprint import education_blueprint
import const
app = Flask(__name__)

from db.db import MongoDB
from dotenv import dotenv_values


env_values = dotenv_values()
db_url = env_values.get("DATABASE_URL")
db_name = env_values.get("DATABASE_NAME")



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
        "username":user_name
    }

    db = MongoDB(db_name=db_name,url=db_url)
    user = db.find_one("users",query=query)
    
    
    if type(user)!=dict:
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400
    
    if user["password"]!=password:
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400
    
    return jsonify({"message":"giriş başarılı","token":user["token"]}),200
    
    
@app.before_request
def auth_middleware():
    if request.path !="/login":
        token =request.headers.get("token")
        if token is None:
            return jsonify({
                        "user_type": const.visited,
                    }), 200
        if token :
            #token çözme işlmeleri
            #g nesnesinie kaydetme işlemleri
            g.user_type = const.visited
            


@app.route('/',methods=["POST"])
def index():
    return {"message":"iris_academi.com"}

if __name__ == '__main__':
    app.run(debug=True)
