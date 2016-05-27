#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import pgdb
import Cookie
import cgitb
import sys
cgitb.enable()
template_html = "login.html"
msg = ""

#DB Connection
connector = pgdb.connect(host="127.0.0.1",database="traffic",user="dbuser",password="dbuser")
cursor = connector.cursor()

#--------------
au = 0
sc = Cookie.SimpleCookie(os.environ.get('HTTP_COOKIE'))
sys.stderr.write(str(sc))
if 'sid' in sc:
    sid = sc['sid'].value
    sys.stderr.write(str(au) + ":" + sid + "\n")

    sql = "delete from sessiontable where sessionid='" + sid + "';"
    cursor.execute(sql)
    connector.commit()

msg = '<tr><td height="60px" valign=middle align=center width=500px>'
msg += 'ログアウトしました'
msg += '</td></tr>'

f = open(template_html, 'r')
bottom_html_skel = f.read()
f.close()
html = bottom_html_skel.replace("**main**", msg)
html = html.replace("<!--replacement-->",'<meta http-equiv="REFRESH" content="1;URL=dashboard.py">')

print sc.output()
print "Content-type: text/html\n"
print html
