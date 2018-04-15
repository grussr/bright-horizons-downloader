from flask import Flask
import base64

app = Flask(__name__)

@app.route('/')
def source():
  with open('state/after_login.png',"rb") as i:
    encoded_string = base64.b64encode(i.read())
  html = '<img  src="data:image/jpeg;base64;+encoded_string">'
  return html