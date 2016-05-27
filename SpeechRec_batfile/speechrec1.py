#!/usr/bin/python
# -*- coding: utf-8 -*-

import glob
import shutil
import time
import os
import boto.sqs
import datetime

wav_source_dir = "Z:\\"
wav_dist_dir = "C:\\SpeechRec\\data\\recog_req\\"

txt_source_dir = "C:\\SpeechRec\\data\\recog_result\\"
eml_dir = "Z:\\"
txt_dist_dir = "Y:\\"

tmp_dir = "C:\\temp\\"

old_filelist_wav = []
old_filelist_txt = []

AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""

conn = boto.sqs.connect_to_region("ap-northeast-1")
# conn = boto.connect_sqs(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
queue = conn.get_queue('voice-solution-sound')

def print_log(st):
    dd = datetime.datetime.today().isoformat(' ')
    print dd + " " + st


if __name__ == '__main__':
    # old_filelist_wav = glob.glob(wav_source_dir + "*.wav")
    old_filelist_txt = glob.glob(txt_source_dir + "*#text.csv")

    while 1:
        # S3バケットからSpeechRecのソースディレクトリへのコピー
        # filelist_wav = glob.glob(wav_source_dir + "*.wav")
        # set_ab_wav = set(filelist_wav) - set(old_filelist_wav)
        # filelist_diff_wav = list(set_ab_wav)
        #
        # for f in filelist_diff_wav:
        #     shutil.copy(f,wav_dist_dir)
        #     print "copy : " + f
        # old_filelist_wav = filelist_wav

        # S3バケットからSpeechRecのソースディレクトリへのコピー(SQS渡し)
        msgs = queue.get_messages()
        for msg in msgs:
            keyname = msg.get_body()
            print_log(keyname)
            queue.delete_message(msg)
            shutil.copy(wav_source_dir + keyname, wav_dist_dir)
            print_log("copy : " + keyname)

        # SoeechRecの出来上がりからのS3へのコピー
        filelist_txt = glob.glob(txt_source_dir + "*#text.csv")
        set_ab_txt = set(filelist_txt) - set(old_filelist_txt)
        filelist_diff_txt = list(set_ab_txt)

        for f in filelist_diff_txt:
            base = os.path.basename(f)
            basename, ext = os.path.splitext(base)
            basename1 = basename.split("#")
            f = open(f, "r")
            f2 = open(tmp_dir + basename1[0] + ".txt", "w")
            readall = f.readlines()
            for r in readall:
                c = r.split(",")
                f2.write(c[3])
            f.close()
            f2.close()

            shutil.copy(tmp_dir + basename1[0] + ".txt", txt_dist_dir + basename1[0] + ".txt")
            print_log("copy : " + basename1[0] + ".txt")
            shutil.copy(eml_dir + basename1[0] + ".eml", txt_dist_dir)
            print_log("copy : " + basename1[0] + ".eml")

        old_filelist_txt = filelist_txt

        print_log("Waiting..." + str(len(old_filelist_wav)) + " / " + str(len(old_filelist_txt)))
        time.sleep(2)
