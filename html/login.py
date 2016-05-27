#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import datetime
import hashlib
import cgi
import pgdb
import Cookie
import sys
import ConfigParser
import cgitb
cgitb.enable()

import auth

template_html = "login.html"
msg = ""

def print_html(msg):
    # Show target
    f = open(template_html, 'r')
    bottom_html_skel = f.read()
    html = bottom_html_skel.replace("**main**", msg)
    f.close()
    print "Content-type: text/html\n"
    print html

def print_message(msg):
    html = '<tr><td height="60px" valign=middle align=center width=500px>'
    html += msg
    html += '</td></tr>'
    print_html(html)

#DB Connection
connector = pgdb.connect(host="127.0.0.1",database="traffic",user="dbuser",password="dbuser")
cursor = connector.cursor()

# Config
config = ConfigParser.RawConfigParser()
config.read('config')

if config.has_option('all', 'http_or_https'):
    http_or_https = config.get('all', 'http_or_https')
else:
    http_or_https = "http"

#--------------
# Form value
form = cgi.FieldStorage()
if 'userid' in form:
    if 'passwd' in form:
        user_id = auth.filter(str(form.getfirst('userid')))
        passwd = str(form.getfirst('passwd'))
        user_id_md5 = hashlib.md5(user_id).hexdigest()
        passwd_sha = auth.password_hash(user_id, passwd)

        cursor.execute("select user_id_md5 from errortable where user_id_md5 = '" + user_id_md5 +"';")
        summary = cursor.fetchall()
        error_retry = len(summary) + 1

        if error_retry > 5:
            msg = '<p style="color: red;font-weight: bold;">5回以上パスワードの入力に失敗しましたのでロックしました</p>'
            sys.stderr.write("Login Error :" + user_id + " / " + str(error_retry) + " more attempts.")
            sql = "update usertable set lock=1 where md5(user_id)='" + user_id_md5 + "';"
            cursor.execute(sql)
            connector.commit()

        else:
            user = auth.authentication(user_id, passwd)

            if user is None:
                sys.stderr.write("Login Error :" + user_id + " / " + str(error_retry) + " attempts.")
                msg = '<p style="color: red;font-weight: bold;">ユーザIDかパスワードが間違っています(*回目)</p>'.replace("*", str(error_retry))
                sql = "insert into errortable values ('" + user_id_md5 + "','" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "');"
                cursor.execute(sql)
                connector.commit()

            else:
                user_id = user[0]
                lock = user[1]

                if lock == 1:
                    msg = '<p style="color: red;font-weight: bold;">アカウントがロックされています</p>'
                    sys.stderr.write("Login Error :" + user_id + " / " + str(error_retry) + " attempts. Account has been locked.")

                else:
                    sc = Cookie.SimpleCookie(os.environ.get('HTTP_COOKIE',''))
                    sessionid = hashlib.sha256(user_id + passwd + os.urandom(100)).hexdigest()
                    expires = datetime.datetime.now() + datetime.timedelta(days=1)
                    sc['sid'] = sessionid
                    sc['sid']['expires'] = expires.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
                    sc['sid']['httponly'] = True
                    if http_or_https != "http":
                        sc['sid']['secure'] = True
                    sql = "insert into sessiontable values ('" + user_id + "','" + sessionid + "','" + expires.strftime("%Y-%m-%d %H:%M:%S") + "');"
                    cursor.execute(sql)
                    connector.commit()

                    # 最終ログイン日を更新
                    sql = "update usertable set last_login='" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "' where passwd ='" + passwd_sha + "';"
                    cursor.execute(sql)
                    connector.commit()

                    # 正常ログインのため、エラーテーブルから削除
                    sql = "delete from errortable where user_id_md5='" + user_id_md5 + "';"
                    cursor.execute(sql)
                    connector.commit()

                    # パスワード有効期限切れ確認
                    sql = "update usertable set force_pass_ch = (case when force_pass_ch=1 then 1 when expires<current_timestamp then 1 else 0 end) " \
                          "where md5(user_id)='" + user_id_md5 + "';"
                    cursor.execute(sql)
                    connector.commit()

                    # パスワード強制変更か、確認
                    cursor.execute("select force_pass_ch from usertable where md5(user_id) = '" + user_id_md5 +"';")
                    summary = cursor.fetchall()
                    for data in summary:
                        force_pass_ch = data[0]
                    if force_pass_ch == 1:
                        jump_url = "passch2.py"
                    else:
                        jump_url = "dashboard.py"
                        if 'prev_url' in sc:
                            if 'passch2.py' not in sc['prev_url'].value:
                                jump_url = sc['prev_url'].value
                            expires = datetime.datetime.now() - datetime.timedelta(days=100)
                            sc['prev_url']['expires'] = expires.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
                            sc['prev_url']['httponly'] = True
                            if http_or_https != "http":
                                sc['prev_url']['secure'] = True

                    # HTML
                    msg = '<tr><td height="60px" valign=middle align=center width=500px>'
                    msg += 'ログインしました'
                    msg += '</td></tr>'

                    f = open(template_html, 'r')
                    bottom_html_skel = f.read()
                    f.close()
                    html = bottom_html_skel.replace("**main**", msg)
                    html = html.replace("<!--replacement-->",'<meta http-equiv="REFRESH" content="0;URL=' + jump_url + '">')

                    sc['cookie_enable'] = "1"

                    print sc.output()
                    print "Content-type: text/html\n"
                    print html
                    exit()

sc = Cookie.SimpleCookie(os.environ.get('HTTP_COOKIE',''))
if 'cookie' in form:
    if 'cookie_enable' in sc:
        if sc['cookie_enable'].value == "1":
            msg += ""
        else:
            msg += '<p style="color: red;font-weight: bold;">クッキーが改竄されています。管理者に連絡してください。</p>'
    else:
        msg += '<p style="color: red;font-weight: bold;">クッキーが有効になっていません。設定を確認してください。<br>クッキーが有効でないとセッション情報が維持できないため、利用できません。</p>'

html = ""
html += '<form action="login.py" name="myform" method="POST" target="_self" onSubmit="return FormCheck(this);">'
html += '<tr><td height="50px" valign=middle align=center colspan="3">' + msg + '</td></tr>'
html += '<tr><td height="100px" valign=middle align=center colspan="3">'
html += "<p>ログインしてください<br>Please login using userID and Password.</p>" \
        "<p>パスワードを忘れた方は<a href='lostpass.htm'>こちら</a></p></td></tr>"
html += '<tr><td height="30px" align="right"> ユーザID </td>' \
        '<td><input type="input" name="userid" size="40" style="background-color: whitesmoke" autocomplete="off"></td></tr>'
html += '<tr><td height="30px" align="right"> パスワード </td><td>' \
        '<input type="password" name="passwd" size="40" style="background-color: whitesmoke" autocomplete="off"></td></tr>'
html += '<tr><td height="50px" colspan="2" align="center">' \
        '<input type="submit" value="Login" style="WIDTH: 100px; HEIGHT: 30px; background-color: lightpink"></td></tr>'

sc['cookie_enable'] = "1"
print sc.output()
print_html(html)
