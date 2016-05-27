#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'akinaga'

import os
import MeCab
import commands
import hashlib
import pickle

t = MeCab.Tagger()
dic = []
s_labels = []
s_features = []

liblinear_location = "/home/ec2-user/Fraud_Detector/tools/liblinear-2.1/"
work_space = "/tmp/"

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


def train(input, dic):
    dat_file = work_space + hashlib.md5(input).hexdigest()
    print dat_file
    f = open(dat_file, "w")
    f.write(input)
    f.close()
    result = commands.getoutput(liblinear_location + "train -s 0 " + dat_file+ " " + dat_file + ".model")

    f = open(dat_file + ".dic", 'w')
    pickle.dump(dic, f)
    f.close()

    return result, dat_file + ".model"


def predict(input, model_file):
    dat_file = work_space + hashlib.md5(input).hexdigest()
    f = open(dat_file, "w")
    f.write(input)
    f.close()
    result = commands.getoutput(liblinear_location + "predict -b 1 " + dat_file + " " + model_file + " " + dat_file + ".result")
    f = open(dat_file + ".result", "r")
    output = f.read()
    f.close()
    return result, output


files = os.listdir('txt2/')
files.sort()
for file in files:
    f = open('txt2/' + file, "r")
    txt = f.readlines()
    line = 0
    feature_set = {}
    for sen in txt:
        line += 1
        if line > 3:
            sen = sen.replace('\r',' ').replace("\t"," ").replace("　"," ").replace(":"," ")
            sen2 = sen.split(" ")
            if len(sen2)>1:
                if len(sen2[1])>0:
                    # print sen2[1]
                    words = t.parseToNode(sen2[1])
                    while words:
                        word = words.surface
                        feature = words.feature
                        features = feature.split(",")
                        words = words.next
                        cano_word = features[6]

                        # 辞書追加作業
                        if cano_word not in dic:
                            dic.append(cano_word)
                        # print file, "\t",  word, "\t", features[6], "\t", dic.index(cano_word)

                        if feature_set.has_key(dic.index(cano_word)):
                            feature_set[dic.index(cano_word)] += 1
                        else:
                            feature_set[dic.index(cano_word)] = 1
    # print feature_set
    # print file,
    if '-' in file:
        # print "-1",
        s_labels.append('-1')
    else:
        # print "+1",
        s_labels.append('+1')
    s_features.append(feature_set)
    # # print "-----------------------------------------------------------"

train_data = svm_format(s_labels, s_features)
test_data = svm_format(s_labels[10:14], s_features[10:14])

result, model = train(train_data, dic)
# print result
result2, output = predict(test_data, model)
print output

