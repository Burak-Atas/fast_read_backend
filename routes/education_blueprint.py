from flask import Blueprint, request, jsonify, g
from db.db import MongoDB
from dotenv import dotenv_values
import const

env_values = dotenv_values()
db_url = env_values.get("DATABASE_URL")
db_name = env_values.get("DATABASE_NAME")

education_blueprint = Blueprint('education_blueprint', __name__)

@education_blueprint.before_request
def check_user_type():
    if g.user_type != const.teacher:
        return jsonify({"error": "yetkisiz erişim"}), 403


@education_blueprint.route("/", methods=["POST"])
def teach():
    content = request.get_json()
    if content is None or "username" not in content or "password" not in content:
        return jsonify({"error": "Eksik bilgi"}), 400
    
    name = content["username"]
    password = content["password"]
    
    # Veritabanı işlemleri - Eğitim verme işlemi
    
    return jsonify({"username": name, "password": password}), 200


@education_blueprint.route("/adduser", methods=["POST"])
def add_user():
    content = request.get_json()
    if content is None or "username" not in content or "password" not in content:
        return jsonify({"error": "Eksik bilgi"}), 400
    
    name = content["username"]
    password = content["password"]
    
    # Veritabanı işlemleri - Kullanıcı ekleme işlemi
    
    return jsonify({"username": name, "password": password}), 200


@education_blueprint.route("/deluser/<string:name>", methods=["DELETE"])
def del_user(name):
    query = {"username": name}
    db = MongoDB(db_name=db_name, url=db_url)
    deleted_user = db.delete_one("users", query=query)

    if deleted_user:
        return jsonify({"message": "Kullanıcı başarılı şekilde silindi"}), 200
    else:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404


@education_blueprint.route("/updateuser/<string:old_name>", methods=["PUT"])
def update_user(old_name):
    content = request.get_json()
    if content is None or ("new_username" not in content and "new_password" not in content):
        return jsonify({"error": "Eksik bilgi"}), 400
    
    new_username = content.get("new_username")
    new_password = content.get("new_password")
    
    query = {"username": old_name}
    new_values = {}
    if new_username:
        new_values["$set"] = {"username": new_username}
    if new_password:
        new_values["$set"].update({"password": new_password})  # Update instead of overwrite
    
    db = MongoDB(db_name=db_name, url=db_url)
    updated_user = db.update_one("users", query=query, new_values=new_values)

    if updated_user:
        return jsonify({"message": "Kullanıcı başarılı şekilde güncellendi"}), 200
    else:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404




@education_blueprint.route("/addeducation",methods=["POST"])
def add_education():
    content = request.get_json()
    
    day = content["day"]
    
    #egzersiizn içinde egzersiz ismi ,hızı ve sayısı olmalıdır
    egzersiz = content["egzersiz"]
    
    db = MongoDB(url=db_url,db_name=db_name)
    db.insert_one("egzersiz",)
    
    