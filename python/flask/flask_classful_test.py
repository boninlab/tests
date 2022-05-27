#!/usr/bin/python3
from flask_mqtt import Mqtt
from flask_classful import FlaskView, route
from flask import Flask, request, jsonify, render_template_string, make_response
from flask_redis import FlaskRedis
from flask_cors import CORS
import requests
import json


app = Flask(__name__)
CORS(app)
mqtt = Mqtt(app)
g_rd = FlaskRedis(app)


class ApiFlask(FlaskView):

  def index(self):
    return jsonify({"result": "fail"}), 403

  @route('/feeder/<actionType>/<action>', methods=['POST'])
  def action(self, actionType, action):
    try:
      data = request.get_data().decode('utf8').replace("'", '"')
      mqtt.publish("feeder/"+actionType+"/"+action, data)
      return jsonify({"result": "ok"})
    except:
      return jsonify({"result": "Bad Request"}), 400

  @route('/feeder/settings/<setting>', methods=['GET', 'POST'])
  def settings(self, setting):
    if setting == 'switch':
      fpath = "/etc/smart-feeder/switch-conf.json"
      if request.method == 'POST':
        try:
          data = request.get_data().decode('utf8').replace("'", '"')
          data = json.loads(data)
          with open(fpath, 'w') as outfile:
            json.dump(data, outfile, indent="\t")
        except:
          return jsonify({"result": "Bad Request"}), 400
      with open(fpath, "r") as jf:
        try:
          fobj = json.load(jf)
        except:
          return jsonify({"result": "Not Found"}), 404
    return jsonify(fobj)

  def getlog(self):
    url = "http://localhost:3030/getlog"
    resp = requests.get(url, params=dict(request.args), timeout=1)
    try:
      dic = json.loads(resp.text)
    except:
      return jsonify({"result": "Not Found"}), 404
    return jsonify(dic)

  def status(self):
    global g_rd
    fobj = {"devices": {}, "params": {}, "hoppers": {}}
    for k in g_rd.scan_iter(match='status/*'):
      rkey = k.decode(encoding="utf-8")
      spKey = rkey.split('/')
      if spKey[1] in fobj['devices']:
        fobj['devices'][spKey[1]].update(
            {spKey[2]: g_rd.get(rkey).decode(encoding="utf-8")})
      else:
        fobj['devices'].update(
            {spKey[1]: {spKey[2]: g_rd.get(rkey).decode(encoding="utf-8")}})
    for k in g_rd.scan_iter(match='params/*'):
      rkey = k.decode(encoding="utf-8")
      spKey = rkey.split('/')
      if spKey[1] in fobj['params']:
        fobj['params'][spKey[1]].update(
            {spKey[2]: g_rd.get(rkey).decode(encoding="utf-8")})
      else:
        fobj['params'].update(
            {spKey[1]: {spKey[2]: g_rd.get(rkey).decode(encoding="utf-8")}})

    hoppers = [1, 2]
    for i in hoppers:
      url = "http://localhost:3030/hopper_info/%s" % (i)
      resp = requests.get(url, timeout=1)
      try:
        fdic = json.loads(resp.text)
      except:
        return jsonify({"result": "Not Found"}), 404
      fdlist = []
      for fd in fdic['feedList']:
        d = {'id': fd['value'], 'name': fd['label'], 'gram': fd['gram']}
        fdlist.append(d)
      fdic['feedList'] = fdlist
      fdic.update({'selname': fdic['kindl'], 'selid': fdic['kindv']})
      del fdic['kindl']
      del fdic['kindv']
      fobj['hoppers'].update({str(i-1): fdic})

    try:
      response = make_response(jsonify(fobj), 200)
      response.mimetype = "application/json"
    except:
      return jsonify({"result": "Not Found"}), 404
    return response

  def testpage(self):
    with open("msgtast.html") as f:
      content = f.read()
    return render_template_string(content)


if __name__ == '__main__':
  ApiFlask.register(app, route_base='/')
  app.run(host='0.0.0.0', debug=True, port=3100)
