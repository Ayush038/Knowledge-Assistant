from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from auth.utils import hash_password, verify_password
from flask_jwt_extended import create_access_token
from users.model import create_user
import os


auth_bp=Blueprint("auth",__name__)
client=MongoClient(os.getenv("MONGO_URI"))
db=client['KnowledgeAssistant']
users_collection=db['users']


@auth_bp.route('/register', methods=['POST'])
def register():
    data=request.json

    if not data or not all(k in data for k in ("username", "email", "password", "role")):
        return jsonify({
            "success":False,
            "msg": "Missing required fields"
        }), 400
    
    if len(data["password"].encode("utf-8")) > 72:
        return jsonify({
            "success": False,
            "msg": "Password too long (max 72 bytes)"
        }), 400
    
    if users_collection.find_one({"email":data['email']}):
        return jsonify({
            "success":False,
            "msg": "Email already registered"
        }), 400

    hashed_password=hash_password(data['password'])
    user=create_user(
        username=data['username'],
        email=data['email'],
        password=hashed_password,
        role=data['role']
    )

    users_collection.insert_one(user)

    return jsonify({
        "success":True,
        "msg": "User registered successfully"
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data=request.json

    if not data or not all(k in data for k in ("email", "password")):
        return jsonify({
            "success":False,
            "msg": "Missing required fields"
        }), 400
    

    user=users_collection.find_one({"email":data['email']})


    if not user:
        return jsonify({
            "success":False,
            "msg": "Invalid email or password"
        }), 401
    if not verify_password(data['password'], user['password']):
        return jsonify({
            "success":False,
            "msg": "Invalid email or password"
        }), 401
    
    token=create_access_token(
        identity=str(user['_id']),
        additional_claims={"role":user['role']}
    )

    return jsonify({
        "success":True,
        "access_token":token,
        "user":{
            "username":user["username"],
            "email":user["email"],
            "role":user["role"]
        }
    }), 200