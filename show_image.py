import os
from flask import Flask
from flask import send_file
from pymongo import MongoClient
import pickle

app = Flask(__name__)

@app.route('/')
def source():
    MONGO_URL = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/test_db')
    client = MongoClient(MONGO_URL)
    try:
        db = client.get_default_database()
        image_file = pickle.loads(db.findOne({'type':'screenshot'}))
        send_file(image_file, attachment_filename='logo.png', mimetype='image/png')
    except Exception as exc:
        print(str(e))
        
    return 'Hello World!'

if __name__ == '__main__':
    app.run()