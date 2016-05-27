#!/usr/bin/python
# -*- coding: utf-8 -*-

import pgdb
import hashlib
import sys
import Cookie
import os
import string
import datetime
import ConfigParser

# --- Input checker ---
def filter(input_text):
    output_text = input_text.replace('"', "").translate(string.maketrans("a", "a"), " *?/><;:,!#$%&'()=~^|\\{}[]`+")
    return output_text


def password_hash(user_id, password):
    return hashlib.sha256(user_id + password).hexdigest()


# ----------------------------
def login_check(sid):   # セッションIDを利用したログインの確認
    connector = pgdb.connect(host="127.0.0.1",database="traffic",user="dbuser",password="dbuser")
    cursor = connector.cursor()
    sql = "select user_id from aws.sessiontable where md5(sessionid) = '" + hashlib.md5(sid).hexdigest() +"' and expires > current_timestamp;"
    # sys.stderr.write(str(sql) + "\n")
    cursor.execute(sql)
    summary = cursor.fetchall()
    if len(summary) == 0:
        auth_result = "NG"
        user_id = ""
    else:
        auth_result = "OK"
        for data in summary:
            user_id = data[0]
    cursor.execute("delete from aws.sessiontable where expires < current_timestamp;")
    connector.commit()
    return auth_result, user_id


def get_user_id(group):
    # Config
    config = ConfigParser.RawConfigParser()
    config.read('./config')

    if config.has_option('all', 'http_or_https'):
        http_or_https = config.get('all', 'http_or_https')
    else:
        http_or_https = "http"

    au = 0
    sc = Cookie.SimpleCookie(os.environ.get('HTTP_COOKIE'))
    # sys.stderr.write(str(sc))
    user_id = ""
    if 'sid' in sc:
        sid = sc['sid'].value
        au = 404
        status, user_id = login_check(sid)
        if status == "OK":
            au = 200
        else:
            au = 504
    if au != 200:
        # Form value
        sys.stderr.write(os.environ['REQUEST_URI'])
        url = os.environ['REQUEST_URI']
        expires = datetime.datetime.now() + datetime.timedelta(minutes=10)
        sc['prev_url'] = url
        sc['prev_url']['expires'] = expires.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
        sc['prev_url']['httponly'] = True
        if http_or_https != "http":
            sc['prev_url']['secure'] = True

        sc['cookie_enable'] = "1"

        print sc.output()
        print "Content-type: text/html\n"
        print '<html><head><meta http-equiv="REFRESH" content="0;URL=/login.py?cookie=1"></head>'
        print '<body><center><h1>User Authorization Required... </h1></body></center></html>'
        exit()
    sys.stderr.write(str(au) + ":" + sid + "\n")
    return user_id


# ---------------- パスワード変更
def passwd_changer(user_id, passwd):

    connector = pgdb.connect(host="127.0.0.1", database="traffic", user="dbuser", password="dbuser")
    cursor = connector.cursor()

    expires = datetime.datetime.now() + datetime.timedelta(days=120)
    sql = "update aws.usertable set (passwd,expires,lock)=('" + password_hash(user_id, passwd) + "',"
    sql += "'" + expires.strftime("%Y-%m-%d %H:%M:%S") + "',0)"
    sql += " where user_id = '" + user_id + "';"
    cursor.execute(sql)
    connector.commit()

    sql = "delete from aws.sessiontable where user_id='" + user_id + "';"
    cursor.execute(sql)
    connector.commit()

    user_id_md5 = hashlib.md5(user_id).hexdigest()
    sql = "delete from aws.errortable where user_id_md5='" + user_id_md5 + "';"
    cursor.execute(sql)
    connector.commit()

# ------------------------------

def error_handling():
    print "Content-type: text/html\n"
    print '<html><head><meta http-equiv="REFRESH" content="0;URL=/dashboard.py"></head>'
    print '<body><center><h1>Recovering from critical error... </h1></body></center></html>'
