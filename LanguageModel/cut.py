#!/usr/bin/python
# -*- coding: utf-8 -*-

filenum = 1

f = open('languagemodel.txt', 'r')
f2 = open(str(filenum)+".txt", "w")
data = f.readlines()
i = 0
for dat in data:
    i += 1
    if i > 20000:
        f2.close()
        filenum += 1
        f2 = open(str(filenum)+".txt", "w")
        i = 0
    f2.write(dat)

f2.close()
