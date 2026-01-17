from flask import Blueprint, request, jsonify
from extensions import limiter
from services.auth.auth_service import (
    validate_registration,
    register_user,
    validate_login,
    login_user
)


auth_bp = Blueprint("auth", __name__)





@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    data = request.json

    valid, error = validate_registration(data)
    if not valid:
        return jsonify({"success": False, "msg": error}), 400

    register_user(data)

    return jsonify({"success": True, "msg": "User registered successfully"}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data = request.json

    valid, error = validate_login(data)
    if not valid:
        return jsonify({"success": False, "msg": error}), 400

    result = login_user(data)

    if not result:
        return jsonify({"success": False, "msg": "Invalid email or password"}), 401

    return jsonify({"success": True, **result}), 200