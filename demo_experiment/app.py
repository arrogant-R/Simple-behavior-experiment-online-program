from flask import Flask, render_template, request, redirect,jsonify
import time
import pandas as pd
import json
import os
from pycocotools import mask
import numpy as np
from PIL import Image
import random
import user_agents
import re
from datetime import datetime

sleep_seconds = 5
app = Flask(__name__, static_folder='.', static_url_path='')

samples = json.load(open("samples_reindex.json", 'r'))
xy = pd.read_csv("xy.csv", index_col=0)
react_t = pd.read_csv("t.csv", index_col=0)
info = pd.read_csv("info.csv",index_col=0)
sent = pd.read_csv("sent.csv", index_col=0)
num_image = 8
click_audio_files = os.listdir('./audio/click')
right_audio_files = os.listdir("./audio/right")

@app.route('/')
def index():
    return render_template("index.html", num_image = num_image)


def detect_device(user_agent):
    if not user_agent:
        return 'unknown'
    mobile_patterns = ["Android", "iPhone", "iPad", "Windows Phone", "Symbian", "BlackBerry", "Mobile", "webOS", "Opera Mini", "Opera Mobi"]
    
    
    desktop_patterns = ["Windows NT", "Macintosh", "Linux"]

    for pattern in mobile_patterns:
        if re.search(pattern, user_agent, re.IGNORECASE):
            return "phone"

    for pattern in desktop_patterns:
        if re.search(pattern, user_agent, re.IGNORECASE):
            return "computor"

    # 如果无法识别，返回未知
    return "unknown"



@app.route("/information/", methods=['GET', 'POST'])
def information():

    id = len(info)
    
    user_agent_string = request.headers.get('User-Agent')
    if user_agent_string:
        device = detect_device(user_agent_string)

    if user_agent_string:
            user_agent = user_agents.parse(user_agent_string)
            browser = user_agent.browser
            #version = user_agent.version
            print(f"Browser: {browser}")
    client_ip = request.remote_addr
    print(client_ip)
    time = datetime.now()


    if request.method == 'POST':
        name = request.form.get('name')
        sex = request.form.get('sex')
        age = request.form.get('age')
        print('从服务器接收到的数据：', name, sex, age)

        info.loc[id,'name'] = name
        info.loc[id, 'age'] = age
        info.loc[id, 'sex'] = sex
        info.loc[id,'browser'] = browser
        info.loc[id,'ip'] = client_ip
        info.loc[id,'device'] = device
        info.loc[id,'time'] = time
        info.to_csv("info.csv")
        return redirect(f'/focus/{id}_0')
    return render_template("information.html")


@app.route('/focus/<id_n>')
def focus(id_n):
    id, n = id_n.split("_")
    id, n = int(id), int(n)
    n += 1
    if num_image < n:
        return redirect('/done/')
    return render_template("focus.html", id=id, n=n)


@app.route("/sentence/<id_n>")
def sentence(id_n):
    id, n = id_n.split("_")
    id, n = int(id), int(n)
    sentence = samples[str(n)]['sentences'][0]['translation']
    return render_template("sentence.html", sentence=sentence, id=id, n=n)


@app.route("/image/<id_n>")
def image(id_n):
    id, n = id_n.split("_")
    id, n = int(id), int(n)
    image_dir = "train2014"
    image_name = samples[str(n)]['file_name']
    I = f'/{image_dir}/{image_name}'
    return render_template("image.html", image=I, id=id, n=n)


@app.route("/done/")
def done():
    return render_template("thanks.html")


@app.route("/handle_click/<id_n>", methods=["POST"])
def write(id_n):
    id, n = id_n.split("_")
    id, n = int(id), int(n)
    data = request.json
    right = True
    x = data['x']
    y = data['y']
    t = data['T']
    # 这里可以处理坐标数据，例如保存到数据库等
    #right= is_click_right(float(x),float(y),samples[str(n)])

    print(f"Received click at ({x} {type(x)}, {y} {type(y)}) , {t} ")

    pos = str(n)
    xy.loc[id, pos] = f'{x}_{y}'
    react_t.loc[id, pos] = t

    xy.to_csv("xy.csv")
    react_t.to_csv("t.csv")

    ref = samples[str(n)]
    if (t > 10000) or (ref['ann_id'][0] == -1
                       and x != -1) or (ref['ann_id'][0] != -1 and x == -1):
        right = False
    elif (ref['ann_id'][0] == -1 and x == -1):
        right = True
    else:
        right = is_click_right(x, y, ref)
    print(f"correct? {right}")

    return jsonify({"right": right})



def is_click_right(x, y, ref):
    """
    xy: 点击的相对坐标
    ref: json文件中的.values()
    """
    image_dir = "train2014"
    file_name = ref['file_name']
    i = Image.open(os.path.join(image_dir, file_name))
    w = i.width
    h = i.height

    ann = ref['annotation']
    if type(ann['segmentation'][0]) == list: # polygon
        rle = mask.frPyObjects(ann['segmentation'], h, w)
    else:
        rle = ann['segmentation']

    m = mask.decode(rle)
    m = np.sum(m, axis=2)

    x = x*w
    y = y*h

    if m[int(y), int(x)] == 0:
        return False

    return True


@app.route("/handle_sent/<id_n>", methods=["POST"])
def handle_sent(id_n):
    id, n = id_n.split("_")
    id, n = int(id), int(n)
    data = request.json
    t = data['T']
    # 这里可以处理坐标数据，例如保存到数据库等
    print(f"Received click at {t}")
    pos = str(n)
    sent.loc[id, pos] = t
    sent.to_csv("sent.csv")
    return 'Calculated!'


@app.route("/grouth_true/<id_n_r>")
def grouth_true(id_n_r):
    id, n, right = id_n_r.split("_")
    id, n, right = int(id), int(n), int(right)

    ref = samples[str(n)]
    no_target = True
    image_dir = "train2014"
    image_name = samples[str(n)]['file_name']

    if not ref['no_target']:
        image_dir = 'GT'
        no_target = False
    I = f'/{image_dir}/{image_name}'
    if right:
        audio_name = random.choice(right_audio_files)
        audio_dir = '/audio/right/'
        audio = audio_dir + audio_name
    else:
        audio = '/audio/wrong.mp3'
    return render_template("grouth_true.html",
                           image=I,
                           no_target=no_target,
                           id=id,
                           n=n,
                           audio=audio,right= right)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002)
