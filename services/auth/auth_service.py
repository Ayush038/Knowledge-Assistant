from bson import ObjectId
from flask_jwt_extended import create_access_token
from auth.utils import hash_password, verify_password
from users.model import create_user
from db import db
import re

users_collection = db["users"]

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_ROLES = {"user", "admin"}


def validate_registration(data):
    if not data or not all(k in data for k in ("username", "email", "password", "role")):
        return False, "Missing required fields"

    if not EMAIL_REGEX.match(data["email"]):
        return False, "Invalid email format"

    username = data["username"].strip()
    if not (3 <= len(username) <= 30):
        return False, "Invalid username"

    if data["role"] not in ALLOWED_ROLES:
        return False, "Invalid role"

    password = data["password"]
    if len(password) < 7:
        return False, "Password must be at least 7 characters long"

    if len(password.encode("utf-8")) > 72:
        return False, "Password too long (max 72 bytes)"

    if users_collection.find_one({"email": data["email"]}):
        return False, "Email already registered"

    return True, None


def register_user(data):
    hashed_password = hash_password(data["password"])

    user = create_user(
        username=data["username"],
        email=data["email"],
        password=hashed_password,
        role=data["role"]
    )

    users_collection.insert_one(user)
    return True


def validate_login(data):
    if not data or not all(k in data for k in ("email", "password")):
        return False, "Missing required fields"

    if not EMAIL_REGEX.match(data["email"]):
        return False, "Invalid email format"

    if not data["password"] or not data["password"].strip():
        return False, "Password cannot be empty"

    return True, None


def login_user(data):
    user = users_collection.find_one({"email": data["email"]})

    if not user or not verify_password(data["password"], user["password"]):
        return None

    token = create_access_token(
        identity=str(user["_id"]),
        additional_claims={"role": user["role"]}
    )

    return {
        "access_token": token,
        "user": {
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    }
