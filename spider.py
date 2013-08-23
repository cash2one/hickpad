#!/usr/bin/python
#coding=utf-8
import urllib
import urllib2
import cookielib

import re

import time

import sqlite3

import socket
import os
import urlparse
    
conn = sqlite3.connect(r'D:\\Web\\data\\info.db3')
cur =  conn.cursor()



url = "http://news.sz.soufun.com/gdxw.html"
save_file = r'D:\\web\\data\\tmp.htm'

try: 
    """从网络获得文件内容"""
    CookieHandle = cookielib.CookieJar()
    UrlOpener=urllib2.build_opener(urllib2.HTTPCookieProcessor(CookieHandle))
    UrlOpener.addheaders = [('User-agent', 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)')]
    urllib2.install_opener(UrlOpener)
    Req = urllib2.Request(url)
    Resp = urllib2.urlopen(Req)
    content = Resp.read()
    FileHandle = file(save_file, 'w')
    FileHandle.write(content)
    FileHandle.close()
    content = content.decode('gb2312')
except urllib2.URLError, e: 
    print 'file open error:' + str(e)


    
url_part = urlparse.urlparse(url)



### 分析内容
##FileHandle = file(save_file, 'r')
##content = FileHandle.read().decode('gb2312')



Reg = re.compile(r'''<div class="textlisttitless">\s+<div class="fonttime">(?P<PubTime>\d{4}-\d{2}-\d{2}　\d{2}：\d{2})</div>\s+<div class="textlist"><a href="(?P<Link>[^"]*)" target="_blank" class="link_01">(?P<Title>[^<]*)</a></div>'''.decode('utf8'))
for i in Reg.finditer(content):
    pub_time = i.groupdict()['PubTime']
    pub_time = pub_time.replace('　'.decode('utf8'), ' ')
    pub_time = pub_time.replace('：'.decode('utf8'), ':')
    pub_time = pub_time + ':00'
    
    link = i.groupdict()['Link']
    link = 'http://' + url_part[1] + link
    
    title = i.groupdict()['Title']
    
    basename = os.path.basename(link)
    sofun_id = basename[0:-4]
    unique_id  = 'soufun_' + str(sofun_id)
    
    type = 'house'  # 数据类型， house 为房产
    source = 'soufun'     # soufun
    
    ### 查询数据库中是否已经存在该记录
    cur.execute("select * from news where unique_id = '" + unique_id + "'")
    row = cur.fetchone()
    if row:
        print unique_id + " has been added"
        continue
    
    ### 插入数据库
    insertStr = "insert into news(title, link, unique_id, pub_time, type, source) values ('%s', '%s', '%s', '%s', '%s', '%s');" % (title, link, unique_id, pub_time, type, source)
    #print insertStr
    cur.executescript(insertStr)
    
    #print i.groupdict()['Title'].encode('gb2312')

    

exit


timeout = 3
socket.setdefaulttimeout(timeout)

