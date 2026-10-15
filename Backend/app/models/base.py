import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)
