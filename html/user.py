#!/usr/bin/python
# -*- coding: utf-8 -*-

import cgi
import os
import sys
import hashlib
import cgitb
cgitb.enable()

import auth
# user_id = os.environ["REMOTE_USER"]
module_name = "init/user2.py"
user_id = auth.get_user_id(module_name)

template_html = "base.html"
title = "User Configuration"
# current_user = os.environ["REMOTE_USER"]
# --------------
additional_js = ""

# --------------
# Form value
form = cgi.FieldStorage()
sys.stderr.write(str(form.keys()) + "\n")
if 'mode' in form:
    mode = str(form.getfirst('mode'))
    sys.stderr.write(str(mode) + "\n")
    if mode == 'reg':
        group_con = auth.read_group_list()
        lock_con = auth.read_user_lock_list()
        force_pass_ch_con = auth.read_force_pass_ch_list()

        for user in group_con.keys():
            grp = ""
            if 'grp_' + hashlib.md5(user).hexdigest() in form:
                grp = str(form.getfirst(hashlib.md5(user).hexdigest()))
            if grp != "":
                sys.stderr.write(str({user: grp}) + "\n")
                group_con.update({user: grp})

            lock_tmp = 0
            if 'lock_' + hashlib.md5(user).hexdigest() in form:
                lock_tmp = auth.filter(str(form.getfirst('lock_' + hashlib.md5(user).hexdigest())))
            lock_con.update({user: lock_tmp})
            sys.stderr.write(str({user: lock_tmp}) + "\n")

            fpc_tmp = 0
            if 'fpc_' + hashlib.md5(user).hexdigest() in form:
                fpc_tmp = auth.filter(str(form.getfirst('fpc_' + hashlib.md5(user).hexdigest())))
            force_pass_ch_con.update({user: fpc_tmp})
            sys.stderr.write(str({user: fpc_tmp}) + "\n")

        auth.reg_user_list(group_con)
        auth.update_user_lock_list(lock_con)
        auth.update_force_pass_ch_list(force_pass_ch_con)

        additional_js = "function msg_disp(){window.alert('変更しました');}"

if 'deleteuser' in form:
    delete_user_md5 = auth.filter(str(form.getfirst('deleteuser')))
    user_con = auth.read_group_list()
    for user in user_con.keys():
        if delete_user_md5 == hashlib.md5(user).hexdigest():
            delete_user = user
    if delete_user in user_con:
        auth.delete_user_from_usertable(delete_user)
    additional_js = "function msg_disp(){window.alert('変更しました');}"


# HTML making
user_con = auth.read_group_list()
lock_con = auth.read_user_lock_list()
force_pass_ch_con = auth.read_force_pass_ch_list()
loginlist = auth.read_loginlist()
errorlist = auth.read_errorlist()

html = '<form action="***SCRIPT***" name="myform" method="POST" target="_self">'
html += '<h2>ユーザ・所属グループ変更(User configuration)</h2>' \
        '<table class="t1">'
html += "<tr>" \
        "<th>Users</th>" \
        "<th>Group</th>" \
        "<th>Lock</th>" \
        "<th nowrap>強制<br>PW変</th>" \
        "<th>ユーザ設定</th>" \
        "<th>Delete</th>" \
        "</tr>\n" \

for user in sorted(user_con.keys()):
    html += "<tr>\n"
    html += "<td style='width: 300pt; text-align: left'>" + user + '</td>\n<td><select name="' \
            + hashlib.md5(user).hexdigest() \
            + '" style="width:100px;font-size:18">'

    for grp in group_con.keys():
        if user_con[user] == grp:
            html += '<option value="' + str(grp) + '" selected>' + str(grp) + '</option>\n'
        else:
            html += '<option value="' + str(grp) + '">' + str(grp) + '</option>\n'
    html += "</select></td>\n"

    # Lock
    html += '<td><input type="checkbox" name="lock_' + hashlib.md5(user).hexdigest() + '" value="1"'
    if lock_con[user] == 1:
        html += ' checked="checked"'
    html += '></td>\n'

    # パスワード変更
    html += '<td><input type="checkbox" name="fpc_' + hashlib.md5(user).hexdigest() + '" value="1"'
    if force_pass_ch_con[user] == 1:
        html += ' checked="checked"'
    html += '></td>\n'

    # User Config
    html += '<td width=100px>'
    html += '<a href="/init/userconfig.py?viewuser=' + hashlib.md5(user).hexdigest() + '" >View</a>'
    html += '</td>\n'

    # Delete
    html += '<td><a href="/init/user2.py?deleteuser=' + hashlib.md5(user).hexdigest() \
            + '" onClick="return del_disp();" style="color: red"><img src="dis.gif"></a></td>\n'

    html += "</tr>\n"

html += "</table>\n"

html += '<input type="hidden" name="mode" value="reg">'
html += "<p><input type='submit' value='Save' onClick='return reg_disp();' style='WIDTH: 200px; HEIGHT: 40px'>" \
        "<input type='reset' value='Reset' style='WIDTH: 100px; HEIGHT: 40px'></form>"

html += "</td></tr>"
html += "<tr><td><hr></td></tr><tr>"
html += '<td valign=middle align=center width=1000px>'
html += '<form action="../reg2.py" name="myform" method="POST" target="_self" onSubmit="return FormCheck(this);">'
html += '新規登録するユーザ、もしくはパスワード変更するユーザのEmailアドレスを入力してください。<p>'
html += '<input type="text" name="addr" size="50" style="background-color: lightgray"> ' \
        '<input type="submit" value="Request" style="WIDTH: 100px; HEIGHT: 20px; background-color: lightpink">'
html += '</form>'
html += "</td></tr>"

html += "<tr><td><hr></td></tr>"

html += '<tr><td valign=middle align=center width=1000px>'

html += '<h2>現在ログインしているユーザ</h2>'
if len(loginlist) == 0:
    html += "<h4>ログインユーザはありません(No User)</h4>"
else:
    html += '<table class="t1">'
    html += "<tr><th>UserID</th><th>SessionID</th><th>Exp.</th></tr><tr>"
    for data in loginlist:
        html += "<tr>"
        for dat in data:
            html += "<td>" + str(dat) + "</td>"
        html += "</tr>"
    html +="</table>"
html += "</td></tr>"

html += "<tr><td><hr></td></tr><tr>"

html += '<td valign=middle align=center width=1000px>'
html += '<h2>ログイン失敗ユーザ</h2>'
if len(errorlist) == 0:
    html += "<h4>ログイン失敗ユーザは居ません(No User)</h4>"

else:
    html += '<table class="t1">'
    html += "<tr><th>UserID(Hash)</th><th>Registered UserID</th><th>Failed attempt</th></tr><tr>"
    for data in errorlist:
        html += "<tr>"
        for dat in data:
            html += "<td>" + str(dat) + "</td>"
        html += "</tr>"
    html += "</table>"

html += "</td></tr>"

# Show target
f = open(template_html, 'r')
bottom_html_skel = f.read()
f.close()
html = bottom_html_skel\
    .replace("**title**", title)\
    .replace("**MAIN**", html)\
    .replace("//**additional**", additional_js)\
    .replace("***SCRIPT***", os.path.basename(__file__))

# Final assemble
print "Content-type: text/html\n"
print html
