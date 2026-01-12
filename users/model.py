from datetime import datetime

def create_user(username, email, password, role):
    return {
        "username": username,
        "email": email,
        "password": password,
        "role": role,
        "is_active": True,
        "created_at": datetime.utcnow()
    }