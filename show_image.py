from flask import Flask
import base64

app = Flask(__name__)

@app.route('/')
def source():
  try:
    with open('state/after_login.png',"rb") as i:
      encoded_string = base64.b64encode(i.read())
      html = '<img src="data:image/png;base64;+encoded_string">'
  except e:
    print(e)
    html = 'Hello World!'
  return html

if __name__ == '__main__':
    app.run()