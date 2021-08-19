from collections import OrderedDict
from time import sleep

import datetime
from pyfcm import FCMNotification
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import inko
import os
import json
import random
import requests
from bs4 import BeautifulSoup

myInko = inko.Inko()

# Firebase database 인증을 위해 ... json 파일을 heroku에 업로드할 수 없기 때문
cred_json = OrderedDict()
cred_json["type"] = os.environ["type"]
cred_json["project_id"] = os.environ["project_id"]
cred_json["private_key_id"] = os.environ["private_key_id"]
cred_json["private_key"] = os.environ["private_key"].replace('\\n', '\n')
cred_json["client_email"] = os.environ["client_email"]
cred_json["client_id"] = os.environ["client_id"]
cred_json["auth_uri"] = os.environ["auth_uri"]
cred_json["token_uri"] = os.environ["token_uri"]
cred_json["auth_provider_x509_cert_url"] = os.environ["auth_provider_x509_cert_url"]
cred_json["client_x509_cert_url"] = os.environ["client_x509_cert_url"]
JSON = json.dumps(cred_json)
JSON = json.loads(JSON)

# 링크, 키값 등
APIKEY = os.environ["APIKEY"]
SITE_URL = "https://www.mjc.ac.kr/bbs/data/list.do?pageIndex=1&SC_KEY=&SC_KEYWORD=&bbs_mst_idx=BM0000000026&menu_idx=66&data_idx=&memberAuth=Y"

#
cred = credentials.Certificate(JSON)
firebase_admin.initialize_app(cred, {
    'databaseURL': os.environ["databaseURL"]
})

# 파이어베이스 콘솔에서 얻어 온 API키를 넣어 줌
push_service = FCMNotification(api_key=APIKEY)

def importSubscribedKeyword():
    keywords = []
    dir = db.reference().child("keywords")
    snapshot = dir.get()
    for key, value in snapshot.items():
        # 키워드 조회하는 김에 구독자 수가 1이하 인거 삭제
        if int(value) < 1:
            db.reference().child("keywords").child(key).delete()
            print("[", key, "]", "가 삭제되었습니다: ", value)

        else:
            keywords.append(key)

    return keywords


def importPreviousPost():
    dir = db.reference().child("lastPostNum")
    snapshot = dir.get()
    for key, value in snapshot.items():
        print("VALUE :", value)
        return value


def sendMessage(title, keyword, url):
    data_message = {
        "url": url,
        "title": title
    }

    # 한글은 키워드로 설정할 수 없다. 한영변환.
    keyword = myInko.ko2en(keyword)
    # 구독한 사용자에게만 알림 전송
    print("keyword : ", keyword)
    print("data_message : ", data_message)
    push_service.notify_topic_subscribers(topic_name=keyword, data_message=data_message)


def activateBot():
    baseUrl = "https://www.mjc.ac.kr/bbs/data/list.do?pageIndex=1&bbs_mst_idx=BM0000000026&menu_idx=66&memberAuth=Y&data_idx="
    datas = {"bbs_mst_idx": "BM0000000026", "menu_idx": "66", "memberAuth": "Y", "pageIndex": "1"}

    now = datetime.datetime.now()
    print("Date: " + now.isoformat())

    try:
        response = requests.get("https://www.mjc.ac.kr/bbs/data/list.do", data=datas)
    except requests.exceptions.Timeout:
        exit()
    except requests.exceptions.TooManyRedirects:
        exit()

    startindex = 0

    soup = BeautifulSoup(response.content, "html.parser")

    check = soup.select("tr > td:nth-of-type(1) > [alt]")
    for string in check:
        startindex += 1

    strings = soup.find_all(attrs={'class': 'cell_type01'})

    subject = []
    didx = []
    keywords = importSubscribedKeyword()

    for string in strings:
        title = string.text.strip()
        subject.append(title)

    href = soup.select("tr > td > a")

    for a in href:
        didx.append(a['href'].split(',\'')[1].replace("'", ""))

    newPostNumber = ""
    for i in range(startindex, startindex + 10):
        newPostNumber = newPostNumber + ", " + didx[i]
        if not didx[i] in previousPostNumber:  # 최근 10개 게시물중 이 번호가 아닌게 있으면 = 새로운 게시물이면
            print("title: [" + subject[i] + "]")
            print("contain keyword:", end=" ")

            for keyword in keywords:
                if keyword in subject[i]:
                    print(keyword, end=", ")
                    sendMessage(subject[i], keyword, baseUrl + didx[i])
            print()

    return newPostNumber


def takeSomeRest():
    rand_value = random.randint(1, 10)
    sleep(rand_value)


now = datetime.datetime.today().weekday()
time = datetime.datetime.now().strftime('%H')

print("-----------------------------------------------")
previousPostNumber = importPreviousPost()
newPostNumber = activateBot()
if previousPostNumber != newPostNumber:
    dir = db.reference().child("lastPostNum")
    dir.update({"lastPostNum": newPostNumber})
    print("\n" + "newPost: " + newPostNumber)
print("-----------------------------------------------")
