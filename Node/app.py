import os
from flask import Flask, redirect, url_for, request, render_template
import requests, json
from pymongo import MongoClient

#IS_LEADER=os.environ['IS_LEADER']
IS_LEADER = True
SERVER_ID = os.environ['SERVER_ID']
############# FRONT END STUFF########################
app = Flask(__name__)

client = MongoClient(host='test_mongodb',
                     port=27017,
                     username='root',
                     password='pass',
                     authSource="admin")
db = client["test_db"]


@app.route('/')
def home():

    _items = db.homedb.find()
    items = [item for item in _items]

    url = requests.get(
        "https://eonet.gsfc.nasa.gov/api/v3/events?limit=20&days=20")
    text = url.text
    data = json.loads(text)
    d2 = data['events']
    events = []

    for i in range(len(d2)):
        events.append(d2[i]['title'])

    return render_template('home.html', items=items, ev=events)


@app.route('/new', methods=['POST'])
def new():
    #print(type(request.form))
    item_doc = {
        'name': request.form['name'],
    }
    if IS_LEADER == "true":
        """nothing"""
        #redirect("http://web2:5000/new",code=307)
        requests.post("http://Node2:5000/new", item_doc)
        requests.post("http://Node3:5000/new", item_doc)

    db.homedb.insert_one(item_doc)
    return redirect(url_for('home'))


@app.route('/return_ack', methods=['GET'])
def ack():
    return "ACK"


if __name__ == "__main__":
    #print(os.environ)

    app.run(host='0.0.0.0', debug=True)
