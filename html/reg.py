#!/usr/bin/python
# -*- coding: utf-8 -*-

import cgi
import hashlib
import subprocess
import datetime
import sys
import ConfigParser
import pgdb
import boto.ses
import xml.sax.saxutils
from auth import passwd_changer
import cgitb
cgitb.enable()

import auth

# user_id = os.environ["REMOTE_USER"]
user_id = auth.get_user_id('admin')

# Config
config = ConfigParser.RawConfigParser()
config.read('/home/ec2-user/html/config/config')

if config.has_option('all', 'admin_email'):
    admin_email = config.get('all', 'admin_email')
if config.has_option('all', 'dns_name'):
    sitename = config.get('all', 'dns_name')
if config.has_option('all', 'http_or_https'):
    http_or_https = config.get('all', 'http_or_https')
else:
    http_or_https = "http"

ses_region_name = "us-west-2"

# definition
base_url = "https://" + sitename + "/reg2.py?"

# DB Connection
connector = pgdb.connect(host="127.0.0.1", database="traffic", user="dbuser", password="dbuser")
cursor = connector.cursor()

# crate table aws.user_reg_table (status text,email text,code text);


def print_err(msg):
    sys.stderr.write(msg + "\n")


def https_or_http(content):
    # process = subprocess.Popen(["ss -lnp | grep 443 | wc -l"], shell=True, stdout=subprocess.PIPE).communicate()[0]
    # if int(process) == 0:
    if http_or_https == "http":
        content = content.replace("https://", "http://")
    return content


def send_email(to_addr, title, content):
    content = https_or_http(content)
    try:
        conn = boto.ses.connect_to_region(ses_region_name)
        # conn = SESConnection(ses_region_name)
        conn.send_email(admin_email, title, content, to_addr)
    except Exception, e:
        print_err("send_mail failed. " + str(e))
        raise
    else:
        print_err("send email : " + to_addr + " / " + title)


def New_user_reg(addr):
    new_password_temp = subprocess.Popen(["mkpasswd -s 0 -l 8"], shell=True, stdout=subprocess.PIPE).communicate()[0]
    new_password = new_password_temp[0:8]

    email = addr
    username = addr

    expires = datetime.datetime.now() + datetime.timedelta(days=365)
    passwd_sha = auth.password_hash(username, new_password)
    sql = "insert into aws.usertable (user_id,passwd,grp,account,expires,last_login,lock,last1pass,last2pass,last3pass,force_pass_ch,view_account,default_account,emailed_account,font_size) "
    sql += " values ('" + username + "','" + passwd_sha + "','user','','"
    sql += expires.strftime("%Y-%m-%d %H:%M:%S") + "','"
    sql += datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "',"
    sql += "0,'" + passwd_sha + "','','',1,'','','',12);"
    cursor.execute(sql)
    connector.commit()
    print_err(sql)

    # ロック解除のため、エラーテーブルから削除
    sql = "delete from aws.errortable where user_id_md5='" + hashlib.md5(username).hexdigest() + "';"
    cursor.execute(sql)
    connector.commit()
    print_err(sql)

    # SES to user
    f = open("template/useremail_newuser2.txt", "r")
    body = f.read()
    body = body.replace("**operation**", "新規ユーザ申請が承認されました。")
    body = body.replace("**emailaddress**", email)
    body = body.replace("**password**", new_password)
    body = body.replace("**sitename**", sitename)

    # SESの処理
    try:
        send_email(email, "Issued new userID and Password for " + sitename, body)
    except Exception, e:
        message = "<p>" + email + "へのメール送信が失敗しました。</p><pre>" + xml.sax.saxutils.escape(str(e)) + "</pre>"
    else:
        print_err("send email for password to new user")
        message = "処理を完了しました.<p>" + addr + "にパスワードの通知が送られます"

    print_html(message)

def Exist_check(addr):
    cursor.execute("select user_id from aws.usertable where user_id = '" + addr +"';")
    summary = cursor.fetchall()
    if len(summary) == 0:
        return False
    else:
        return True

def delete_allcode(addr):
    sql = "delete from aws.user_reg_table where email = '" + addr + "';"
    cursor.execute(sql)
    connector.commit()


def print_html(msg):
    f = open('template/reg_template.htm', 'r')
    html_body = f.read()
    f.close()
    html = html_body.replace("**message**", msg)
    print "Content-type: text/html\n"
    print html


def reg_request(addr):
    # Search email address on /etc/httpd/.htdigest
    username = addr #実際のユーザ名
    email = addr #emailアドレス
    # 現在の実装では同じだが、残置

    found = Exist_check(username)

    # New user
    if not found:
        status = "New User"
        acceptcode = hashlib.md5(status + email + status).hexdigest()
        sql = "insert into aws.user_reg_table values ('" + status + "','" + email + "','" + acceptcode + "');"
        cursor.execute(sql)
        connector.commit()
        print_err("Reg db acceptcode for new user")

        status = "Reject"
        rejectcode = hashlib.md5(status + email + status).hexdigest()
        sql = "insert into aws.user_reg_table values ('" + status + "','" + email + "','" + rejectcode + "');"
        cursor.execute(sql)
        connector.commit()
        # print_err("Reg db rejectcode for new user")

        # SES to admin
        f = open("template/adminemail.txt", "r")
        body = f.read()
        f.close()
        body = body.replace("**accepturl**", base_url + "regcode=" + acceptcode)
        body = body.replace("**rejecturl**", base_url + "regcode=" + rejectcode)
        body = body.replace("**operation**", "新規ユーザの申し込み")
        body = body.replace("**emailaddress**", addr)
        body = body.replace("**sitename**", sitename)

        try:
            send_email(admin_email, "New user coming", body)
        except Exception, e:
            print_html("<p>" + admin_email + "へのメール送信が失敗しました。</p><pre>" + xml.sax.saxutils.escape(str(e)) + "</pre>")
            exit()

        print_err("send email to admin for new user")

        # SES to user
        f = open("template/useremail_newuser1.txt", "r")
        body = f.read()
        f.close()

        body = body.replace("**rejecturl**", base_url + "regcode=" + rejectcode)
        body = body.replace("**operation**", "新規ユーザの申し込みがありました。")
        body = body.replace("**emailaddress**", addr)
        body = body.replace("**sitename**", sitename)

        try:
            send_email(email, "Welcome to " + sitename, body)
        except Exception, e:
            print_html("<p>" + email + "へのメール送信が失敗しました。</p><pre>" + xml.sax.saxutils.escape(str(e)) + "</pre>")
            exit()

        print_err("send email to user for new user")

        print_html("ユーザ登録を受理しました。<p>Adminが承認するとEmailでパスワードが届きます。<p>Emailでの通知をお待ちください。")

    # Password change
    else:
        sql = "update aws.usertable set force_pass_ch=1 where user_id='" + email + "';"
        cursor.execute(sql)
        connector.commit()

        # temporary password issuing
        new_password_temp = subprocess.Popen(["mkpasswd -s 0 -l 8"], shell=True, stdout=subprocess.PIPE).communicate()[0]
        new_password = new_password_temp[0:8]
        passwd_changer(addr, new_password)

        # SES to admin
        f = open("template/adminemail.txt", "r")
        body = f.read()
        body = body.replace("**operation**", "パスワード変更")
        body = body.replace("**emailaddress**", email)
        body = body.replace("**accepturl**", "N/A")
        body = body.replace("**sitename**", sitename)
        body = body.replace("**rejecturl**", "N/A")
        # body = body.replace("**rejecturl**", base_url + "regcode=" + rejectcode)
        f.close()

        # SES
        try:
            send_email(admin_email, "Password change initiated for " + addr, body)
        except Exception, e:
            print_html("<p>" + admin_email + "へのメール送信が失敗しました。</p><pre>" + xml.sax.saxutils.escape(str(e)) + "</pre>")
            exit()

        # SES to user
        f = open("template/useremail_passwordchange.txt", "r")
        body = f.read()
        f.close()
        body = body.replace("**accepturl**", "https://" + sitename + "/dashboard.py")
        # body = body.replace("**accepturl**", base_url + "regcode=" + acceptcode)
        # body = body.replace("**rejecturl**", base_url + "regcode=" + rejectcode)
        body = body.replace("**sitename**", sitename)
        body = body.replace("**operation**", "パスワード変更の申し込みがありました。")
        body = body.replace("**emailaddress**", email)
        body = body.replace("**temppass**", new_password)

        # SESの処理
        try:
            send_email(addr, "Password change", body)
        except Exception, e:
            print_html("<p>" + addr + "へのメール送信が失敗しました。</p><pre>" + xml.sax.saxutils.escape(str(e)) + "</pre>")
            exit()

        print_html("パスワード変更を受理しました。<p>Emailでの通知をお待ちください。")


if __name__ == '__main__':

    # crate table aws.user_reg_table (status text,email text,code text);
    # Extract form values
    form = cgi.FieldStorage()
    regcode = ""
    passwd = ""
    addr = ""
    # Accept code and Reject code
    if 'regcode' in form:
        regcode = auth.filter(str(form.getfirst('regcode')))
    # Passsword
    if 'passwd' in form:
        passwd = auth.filter(str(form.getfirst('passwd')))
    # Email address
    if 'addr' in form:
        addr_temp = str(form.getfirst('addr'))
        if email_validator(addr_temp) == 1:
            addr = addr_temp

    # print_err(regcode + " / " + passwd + " / " + addr)

    #
    if regcode == "" and addr != "":
        delete_allcode(addr)
        reg_request(addr)
        exit()
    elif regcode != "":
        # code checker
        sql = "select status,email from aws.user_reg_table where md5(code) = '" + hashlib.md5(regcode).hexdigest() + "';"
        cursor.execute(sql)
        summary = cursor.fetchall()
        if len(summary) == 0:
            print_html("このオペレーションは既に承認されているか、無効にされました。<p>詳細が不明な場合はAdminまでご連絡ください。")
            exit()
        else:
            for data in summary:
                email = str(data[1])
                if str(data[0]) == "New User":
                    New_user_reg(email)
                    delete_allcode(email)
                    exit()

                elif str(data[0]) == "Reject":
                    delete_allcode(email)
                    print_html("処理を中断しました. " + email)
                    exit()
                else:
                    print_html("状態が不正です。<p>詳細が不明な場合はAdminまでご連絡ください。")
                    exit()
    else:
        template_html = "reg.htm"
        f = open(template_html, 'r')
        html = f.read()
        f.close()

        # Final assemble
        print "Content-type: text/html\n"
        print html
