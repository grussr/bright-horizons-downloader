import os
from io import BytesIO
from flask import Flask
from flask import send_file
from flask import abort
from pymongo import MongoClient
import pickle

app = Flask(__name__)

@app.route('/')
def source():
    MONGO_URL = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/test_db')
    client = MongoClient(MONGO_URL)
    try:
        db = client.get_default_database().settings
        screenshot = db.find_one({'type':'screenshot'})
        image_file = BytesIO(screenshot['value'])
        return send_file(image_file, attachment_filename='logo.png', mimetype='image/png')
    except Exception as exc:
        print(str(exc))
        
    return 'Hello World!'

@app.route('/list/', defaults={'req_path': ''})
@app.route('/list/<path:req_path>')
def dir_listing(req_path):
    BASE_DIR = '/app/img'

    # Joining the base and the requested path
    abs_path = os.path.join(BASE_DIR, req_path)

    # Return 404 if path doesn't exist
    if not os.path.exists(abs_path):
        return abort(404)

    # Check if path is a file and serve
    if os.path.isfile(abs_path):
        return send_file(abs_path)

    # Show directory contents
    files = os.listdir(abs_path)
    return render_template('files.html', files=files)
    
if __name__ == '__main__':
    app.run()