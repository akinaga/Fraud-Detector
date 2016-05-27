#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'akinaga'

import MeCab
import math
import commands
import hashlib
import pickle
import cgi
import sys
from colour import Color
import cgitb
cgitb.enable()

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

# Final assemble
f = open('fd.html','r')
html = f.read()
f.close()

feature_set = {}
word_summary = []
form = cgi.FieldStorage()
if 'target' in form:
    input_txt = form.getfirst('target')
    # sys.stderr.write(input_txt)
    if len(input_txt)>1:
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
                if dic.index(cano_word)!=0:
                    word_summary.append([word, features[6], dic.index(cano_word)])

    test_data = svm_format(['-1'], [feature_set])
    result, output = predict(test_data, model_file, input_txt)
    sys.stderr.write(str(output))

    sc = output.split("\n")[1]
    score = str(int(float(sc.split(" ")[1])*100.0))
    score_html = '<table width="800pt" border=1 class="t2">'
    score_html += '<tr>'
    score_html += '<td class="tg" width="200px"><div class="graph" style="width: XX%" ><span>YY</span></div></td>'.replace("XX",score).replace("YY","詐欺確率" + score + "%")
    score_html += '</td></tr></table><p>'

    # 文章の重み付け
    word_html = '<table width="800pt" border=1 class="t1"><tr><td>'
    for word in word_summary:
        model_score = model[word[2]]*10000.0
        if model_score > 500:
            model_score2 = 500
        elif model_score < -500:
            model_score2 = -500
        else:
            model_score2 = model_score
        model_color = (1-(model_score2 + 500)/1000)*0.7
        c = Color(hsl=(model_color, 0.7, 0.5))
        # if model_score>100 or model_score<-100:
        word_html += '<font color="' + c.get_web() + '">' + word[0] + "</font>"

    word_html += "</td></tr></table>"

    # 単語毎のスコア表示
    word_html += '<table width="800pt" border=1 class="t1">'
    word_html += "<tr><th>検出語</th><th>正規化語</th><th>インデックス番号</th><th>スコア</th></tr>"
    model_sum = 0
    # bias = -1
    for word in word_summary:
        model_sum += model[word[2]]
        model_score = model[word[2]]*10000.0
        if model_score > 500:
            model_score2 = 500
        elif model_score < -500:
            model_score2 = -500
        else:
            model_score2 = model_score
        model_color = (1-(model_score2 + 500)/1000)*0.7
        c = Color(hsl=(model_color, 0.8, 0.7))
        # if model_score>100 or model_score<-100:
        word_html += "<tr><td>" + word[0] + "</td><td>" + word[1] + "</td><td>" + str(word[2]) + "</td><td bgcolor='" + c.get_web() + "'>" + str(round(model_score,2)) + "</td></tr>"
    word_html += "</table>"

    summary = "<h2>判定結果</h2>" + score_html + word_html # + "<h2>**</h2>".replace("**",str(model_sum))
    html = html.replace("<!--Insert data-->", summary)

if 'model' in form:
    word_html = '<table width="800pt" border=1 class="t1">'
    word_html += "<tr><th>No.</th><th>辞書語</th><th>重み</th></tr>"
    model_dic = {}
    for i in zip(dic,model):
        model_dic[i[0]] = i[1]
    i = 0
    for k, v in sorted(model_dic.items(), key=lambda x:x[1], reverse=True):
        i += 1
        word_html += "<tr><td>" + str(i) + "</td><td>" + k + "</td><td>" + str(v) + "</td></tr>"
    word_html += "</table>"
    html = html.replace("<!--Insert data-->", word_html)

print "Content-type: text/html; charset=UTF-8\n\n"
print html.replace("**original_text**",input_txt)

