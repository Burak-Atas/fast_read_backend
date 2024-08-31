from flask import Flask, jsonify, request,g,abort
from flask_cors import CORS
from routes.student_blueprint import student_blueprint
from routes.education_blueprint import education_blueprint
import const
app = Flask(__name__)

from db.db import MongoDB
from dotenv import dotenv_values
from model import model
from smtpserver import EmailVerification,EmailVerificationCode
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
    print("logind")

    db = MongoDB(db_name=db_name,url=db_url)
    user = db.find_one("users",query=query)
    
    if type(user)!=dict:
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400
    
    if user["password"]!=password:
        return jsonify({"error":"Kullanıcı adı yada şifre hatalı"}),400
    
    if user["user_type"]==const.student:
        if user["activate"]==False:
            return jsonify({"message":"lütfen üyeliğinizin aktifliğini bekleyin"}),200
        return jsonify({"message":"giriş başarılı","token":user["token"],"name":user["name"]}),200
    
    token = JWT_Token().generate_token_teacher(user_id=None,role=user["user_type"],name=user["name"],user_name=user["user_name"])
    print("yeni toen",token)
    print(user["user_type"])
    if token =="":
        return jsonify({"error":"lütfen daha sonra tekrar deneyiniz"}),400

    res = db.update_one(collection_name="users",query={"user_name":user["user_name"]},data={"token":token})
    if res == 1:
        return jsonify({"message":"giriş başarılı","token":token,"name":user["name"]}),200
    else:
        return jsonify({"error":"lütfen daha sonra tekrar deneyiniz"}),400
    
@app.before_request
def auth_middleware():
    if request.path != "/login" and request.path != "/contact" and request.path != "/sendcode" and request.path != "/teacher/updatepassword":
        print("ubrada")
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
            return jsonify({"error":"yetkisiz erişim"})



@app.route('/contact',methods=["POST"])
def index():
    content = request.get_json()["formData"]
    EmailVerification("batas219@gmail.com",konu=content["subject"],kimden=content["email"])
    return jsonify({"message":"mesajınız gönderildi"}),200

@app.route('/sendcode',methods=["POST"])
def send_code():
    content = request.get_json()
    email = content["email"].strip()
    db = MongoDB(url=db_url,db_name=db_name)

    users = db.find_one(collection_name="users",query={"email":email})    
    
    if type(users)!=dict:
        return jsonify({"message":"lütfen mailiniz kontrol ediniz"}),400
    
    code = EmailVerificationCode(email_receiver=email,subject="şifre güncelleme kodu",sender_name="GELISTRİO").send_code()
    print(code)

    user = db.find_one("update_password",{"email":email})
    if user== None:
        inserted = db.insert_one("update_password",{"code":code,"email":email,"try":3})
        if inserted:
            return jsonify({"message":"mesajınız gönderildi"}),200
        else:
            return jsonify({"error":"sunucu hatası"}),500
    else:
        inserted = db.update_one("update_password",{"email":email},{"code":code,"email":email})
        if inserted==1:
            return jsonify({"message":"doğrulama kodunuz gönderildi lütfen mailinizi kontrol edin"}),200
        else:
            return jsonify({"error":"sunucu hatası"}),500




@app.route("/teacher/updatepassword",methods=["POST"])
def update_password():
    content = request.get_json()["formData"]
    print(content)
    
    email = content["email"].strip()
    
    if content["password"]!=content["rpassword"]:
        return jsonify({"error":"şifreler eşleşmiyor"}),400
    
    db = MongoDB(url=db_url,db_name=db_name)
    find_user = db.find_one(collection_name="update_password",query={"email":email})

    if find_user:
        found_code = find_user["code"]
        if content["code"]==found_code:
            updated = db.update_one(collection_name="users",query={"email":email},data={"password":content["password"]})
            if updated==1:
                deleted = db.delete_one(collection_name="update_password",query={"email":email})
                if deleted == 1:    
                    return jsonify({"message":"şifreniz başarılı bir şekilde güncellendi"}),200
                return jsonify({"message":"daha sonra tekrar deneyiniz"}),200
            else:
                return jsonify({"error":"şifreniz  güncellenirken hata oluştu"}),400
        else:
            updated = db.update_one(collection_name="updata_password",query={"email":email},data={"try":find_user["try"]-1})
            if update_password==1:
                return jsonify({"message":"hatalı kod girdiniz","try":find_user["try"]-1})
            else:
                return jsonify({"error":"şifreniz  güncellenirken hata oluştu"}),400
    else:
        return jsonify({"error":"lütfen tekrar kod alınız "}),400       
                
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
