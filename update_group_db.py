import os
from app import app
from models import db

with app.app_context():
    print("Creating new tables for Study Group feature...")
    db.create_all()
    print("Done!")
