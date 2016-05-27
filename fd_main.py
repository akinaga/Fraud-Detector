#!/usr/bin/python
# -*- coding: utf-8 -*-
import MeCab
import commands
import hashlib
import pickle
import time
from boto.s3.connection import S3Connection
import boto.ses
from hashlib import md5
from boto3.session import Session
import datetime
import urllib
import json
import os
import datetime
from boto.sqs.message import Message

__author__ = 'akinaga'
session = Session(region_name='ap-northeast-1')

t = MeCab.Tagger()
s_labels = []
s_features = []
input_txt = ""

liblinear_location = "/home/ec2-user/Fraud_Detector/tools/liblinear-2.1/"
work_space = "/tmp/"
# model_file = work_space + "8332dd5c05de2650bca8ae10ea1e8448.model"
# dic_file = work_space + "8332dd5c05de2650bca8ae10ea1e8448.dic"
model_file = work_space + "ae5ae9a3a642dc49a2e937d2cc07884f.model"
dic_file = work_space + "ae5ae9a3a642dc49a2e937d2cc07884f.dic"


f = open(dic_file,'r')
dic = pickle.load(f)
f.close()

model = []
f = open(model_file,'r')
m = f.readlines()
i = 0
for mm in m:
    i += 1
    if i == 5:
        bias = float(mm.split(" ")[1])
    if i >= 7:
        model.append(float(mm))
f.close()
# sys.stderr.write(str(model))
log_file = open("fd_main.log", "a")


def print_log(st):
    dd = datetime.datetime.today().isoformat(' ')
    print dd + " " + st
    log_file.write(dd + " " + st + "\n")

def svm_format(labels, features):
    output = ""
    if len(labels)!=len(features):
        return "Error"
    i = 0
    for dat in zip(labels,features):
        output += str(dat[0])
        feature = dat[1]
        fkeys = feature.keys()
        fkeys = sorted(fkeys, key=int)
        for k in fkeys:
            if k != 0:
                output += " " + str(k) + ":" + str(feature[k])
        i += 1
        if len(labels) > i:
            output += "\n"
    return output


def predict(input, model_file, original_txt):
    dat_file = work_space + hashlib.md5(input).hexdigest()
    f = open(dat_file + ".original","w")
    f.write(original_txt)
    f.close()
    f = open(dat_file, "w")
    f.write(input)
    f.close()
    result = commands.getoutput(liblinear_location + "predict -b 1 " + dat_file + " " + model_file + " " + dat_file + ".result")
    f = open(dat_file + ".result", "r")
    output = f.read()
    f.close()
    return result, output


def get_queue(qname):
    queue = session.resource('sqs').get_queue_by_name(QueueName=qname)
    messages = queue.receive_messages(
        MaxNumberOfMessages=1
    )
    entries = []
    body = ""
    for message in messages:
        entries.append({
            "Id": message.message_id,
            "ReceiptHandle": message.receipt_handle
        })
        body = json.loads(message.body)
        print_log(str(body))

    if len(entries) != 0:
        response = queue.delete_messages(
            Entries=entries
        )

    if len(body) > 0:
        bucket = body['Records'][0]['s3']['bucket']['name']
        key = urllib.unquote_plus(body['Records'][0]['s3']['object']['key']).decode('utf8')
        print_log(bucket + "/" + key)
        return key
    else:
        return ""

def put_queue(msg, qname):
    response = session.resource('sqs').get_queue_by_name(QueueName=qname).send_message(MessageBody=msg)
    print_log(qname + "->" + msg)
    return response

def send_email(to_addr, title, content):
    admin_email = "fraud.detector.docomo@gmail.com"
    ses_region_name = "us-west-2"
    try:
        conn = boto.ses.connect_to_region(ses_region_name)
        # conn = SESConnection(ses_region_name)
        print_log("SES: " + admin_email + " / " + title +" / " + content + " / " + to_addr)
        conn.send_email(admin_email, title, content, to_addr, format="html")
    except Exception, e:
        print_log("send_mail failed. " + str(e))
        raise
    else:
        print_log("send email : " + to_addr + " / " + title)


# Final assemble
f = open('mail.html', 'r')
html = f.read()
f.close()

feature_set = {}
word_summary = []

conn = S3Connection(host='s3-ap-northeast-1.amazonaws.com')
b = conn.get_bucket('voice-solution-text')
from boto.s3.key import Key

while 1:

    keyname = get_queue("voice-solution-wav")
    keyname2 = get_queue("voice-solution-text")

    try:

        # MP3変換
        if ".mp3" in keyname:
            command = "/usr/local/bin/s3cmd -f get s3://voice-solution/" + keyname + " /dev/shm/"
            status, output = commands.getstatusoutput(command)
            print_log(command)

            command = "sox /dev/shm/" + keyname + " /dev/shm/" + keyname.replace(".mp3", ".wav") + " channels 1 rate 8k"
            status, output = commands.getstatusoutput(command)
            print_log(command)

            command = "/usr/local/bin/s3cmd -f put /dev/shm/" + keyname.replace(".mp3", ".wav") + " s3://voice-solution/"
            status, output = commands.getstatusoutput(command)
            print_log(command)

            command = "rm -f /dev/shm/" + keyname.replace(".mp3", ".wav") + " /dev/shm/" + keyname
            status, output = commands.getstatusoutput(command)
            print_log(command)


        elif ".wav" in keyname:
            response = put_queue(keyname, "voice-solution-sound")

        elif ".txt" in keyname2:
            print_log("Start Email: " + keyname2)
            k = Key(b)
            k2 = Key(b)
            k.key = keyname2
            k2.key = keyname2.replace(".txt", ".eml")
            input_txt = k.get_contents_as_string()
            if k2.exists():
                email_addr = k2.get_contents_as_string().split(";")
                print_log(input_txt)
                print_log(str(email_addr))

                command = "/usr/local/bin/s3cmd -f get s3://voice-solution/" + keyname2.replace(".txt", ".wav") + " /dev/shm/"
                status, output = commands.getstatusoutput(command)
                print_log(command)

                command = "sox /dev/shm/" + keyname2.replace(".txt", ".wav") + " -n stat 2>&1 1>/dev/null | grep Length | tr -cd '0123456789.\n'"
                status, output = commands.getstatusoutput(command)
                wav_length = int(float(output) + 5.0)
                print_log(str(wav_length))

                timestring = keyname2.replace(".txt", "").split("_")
                starttime = datetime.datetime.strptime(timestring[1], "%Y%m%d%H%M%S")
                endtime = starttime + datetime.timedelta(seconds=wav_length)
                duration = datetime.timedelta(seconds=wav_length)

                if len(input_txt) > 1:
                    words = t.parseToNode(input_txt)
                    while words:
                        word = words.surface
                        feature = words.feature
                        features = feature.split(",")
                        words = words.next
                        cano_word = features[6]
                        # 辞書内検索作業（辞書にない場合は無視）
                        if cano_word in dic:
                            if feature_set.has_key(dic.index(cano_word)):
                                feature_set[dic.index(cano_word)] += 1
                            else:
                                feature_set[dic.index(cano_word)] = 1
                            if dic.index(cano_word) != 0:
                                word_summary.append([word, features[6], dic.index(cano_word), model[dic.index(cano_word)]])

                test_data = svm_format(['-1'], [feature_set])
                result, output = predict(test_data, model_file, input_txt)
                print_log(str(output).replace("\n", ""))

                sc = output.split("\n")[1]
                score = int(float(sc.split(" ")[1])*100.0)
                if score > 90:
                    output_text = "ほぼ詐欺である"
                elif (score <= 90) and (score > 52):
                    output_text = "詐欺の可能性がある"
                elif (score >= 20) and (score < 48):
                    output_text = "ほぼ詐欺ではない"
                elif score < 20:
                    output_text = "詐欺ではない"
                else:
                    output_text = "判定不能（情報量不足）"

                score_html = '<table width="600px" border=1 class="t2">'
                score_html += '<tr>'
                score_html += '<td class="tg" width="600px"><div class="graph" style="width: XX%" ><span>YY</span></div></td>'\
                    .replace("XX", str(score)).replace("YY", "詐欺確率:YY%".replace("YY", str(score)))
                score_html += '</td></tr></table><p>'

                # 文章の重み付け
                word_html = '<table border=1 class="t1" width="600px"><tr><td>'
                word_score = {}
                for word in word_summary:
                    if word[2] in word_score.keys():
                        word_score[word[2]] += word[3]
                    else:
                        word_score[word[2]] = word[3]
                    # print_log(str(word) + "/" + str(word_score[word[2]]))
                i = 0

                r = []
                for k, v in sorted(word_score.items(), key=lambda x:x[1], reverse=True):
                    r.append(str(dic[k]) + "(" + str(round(v, 2)) + ")")
                    i += 1
                    if i > 9:
                        break
                word_html += ",".join(r[0:4]) + "<br>"
                word_html += ",".join(r[5:9])
                word_html += "</td></tr></table>"

                # 内容の表示（デバッグ用）
                word_html = '<table border=1 class="t1" width="600px"><tr><td>' + input_txt.replace("\n", "<br>") + "</td></tr></table>"


                # 最終仕上げ
                html_r = html.replace("**score**",score_html).replace("**word**", word_html)
                html_r = html_r.replace("**starttime**", starttime.strftime("%c"))
                html_r = html_r.replace("**endtime**", endtime.strftime("%c"))
                html_r = html_r.replace("**duration**", str(wav_length) + "秒")
                html_r = html_r.replace("**msg**",output_text)

                # ファイル名確定
                filename = md5(html_r).hexdigest()
                html_r = html_r.replace("**resultfile**", filename + ".htm")

                # ログファイルへの格納
                f = open('html/result/' + filename + ".htm", 'w')
                f.write(html_r)
                f.close()

                # S3へのファイル格納
                # conn2 = S3Connection(host='')
                # b2 = conn2.get_bucket('voice-solution.cshhage.jp', validate=False)
                # k3 = Key(b2)
                # k3.key = filename + ".htm"
                # k3.set_contents_from_string(html_r)
                command = '/usr/local/bin/s3cmd -f put ' + 'html/result/' + filename + ".htm " + "s3://voice-solution.cshhage.jp/result/"
                print_log(command)
                print_log(str(os.system(command)))

                # メール送信
                for addr in email_addr:
                    if len(addr)>5:
                        send_email(addr, "FD report", html_r)
            else:
                print_log("Ignored...(reason : cannot find email address file)")
        else:
            print_log("waiting...")
            time.sleep(3)
    except:
        print_log("Error...")
        # time.sleep()
