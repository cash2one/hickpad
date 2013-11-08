#!/usr/bin/env python
#coding=utf8

import wx
import wx.lib.agw.aui as aui
import wx.stc
import sys
import os
import time
import re
import datetime
import ctypes

import sqlite3

import win32con # 系统热键
import win32api
import win32gui

# 网络相关操作
import urllib
import urllib2
import cookielib
import socket   # 用于控制超时等
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
import wx.lib.masked          as masked

import os
import traceback # dolog 需要

# 语音 tts
import pyttsx
# 剪切板
import win32clipboard 
# 抓取分析网页
from bs4 import BeautifulSoup

import threading

############################################## 全局操作和变量
# 获得可执行文件所在路径(注意 os.path.getcwd 获得的是命令行启动的当前路径)
exe_dir = os.path.dirname(sys.argv[0])
# tts 引擎同时只能有一个操作
tts_running = False
tts_engine = pyttsx.init()

###------------------ 全局函数： 记录 log
"""
记录 log 的调试函数: 默认去当前文件夹
    注意中文可能某些输入的时候是 unicode 的话，有这样的差别:
    dolog("I am Hick")
    dolog("中文")
    dolog(u"我只中文hick".encode("UTF-8"))
"""
def dolog(text, name = ''):
    if len(name) < 1:
        name = 'log.txt'
    log_file = os.path.join(os.path.dirname(sys.argv[0]), name)

    trace = traceback.extract_stack()
    last_file = trace[0][0]
    last_line = trace[0][1]

    # 参数字符处理
    if isinstance(text, unicode):
        text = text.encode("UTF-8")

    all_str = time.strftime("%Y-%m-%d %H:%M:%S\t") + last_file + "\t" + str(last_line) + "\t" + text + "\n"
    print all_str
    file(log_file, 'a').write(all_str)
### 检查 log 文件大小
def checklog(name = ''):
    if len(name) < 1:
        name = 'log.txt'
    log_file = os.path.join(os.path.dirname(sys.argv[0]), name)  
    print log_file
    if os.path.isfile(log_file):
        return os.path.getsize(log_file)

###------------------ 全局函数： tts 说话
def tts_say(text):
    # 如果当前有使用语音引擎，则记录 log 并返回 false
    global tts_running
    if tts_running:
        dolog("语音引擎使用中，暂时不能使用")
        return

    # 文本必须是 unicode ， 所以这里需要转码: 也只接受 utf 8 的
    if not isinstance(text, unicode):
        text = text.decode("UTF-8")

    tts_running = True
    tts_engine.say(text)
    # tts_engine.runAndWait()
    tts_running = False

    dolog(time.strftime("%Y-%m-%d %H:%M:%S\t") + u"语音引擎执行完以下内容: " + text)

if wx.Platform == '__WXMSW__':
    face1 = 'Fixedsys'
    face2 = 'Times New Roman'
    face3 = 'Fixedsys'
    pb = 9
else:
    face1 = 'Helvetica'
    face2 = 'Times'
    face3 = 'Courier'
    pb = 12
    

tts_say("咚咚咚咚，小爷来了")
dolog("hickpad启动了") ### 要用中文以免文件不是 utf8

log_size = checklog()
# 5M 提醒清理
if log_size > 5000000 :
    tts_say("日志文件有点大了，清理一下吧")

#=======================================================================
class PageEditor(wx.Panel):
    """
    文本编辑器(后续还需要类似 Excel tab 等)
    """
    def __init__(self, parent):
        """初始化文本编辑器"""
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

        self.Textarea = wx.stc.StyledTextCtrl(self, wx.ID_ANY, pos=(0, 26))
        self.Textarea.SetWrapMode(True)
        self.Textarea.SetMarginType(0, wx.stc.STC_MARGIN_NUMBER)   # 设置第一列显示行号(可以随便定义，还可以设置第三列也显示行号)
        self.Textarea.SetMarginType(1, wx.stc.STC_MARGIN_SYMBOL)   # 设置第二列显示符号(symbol)
        self.Textarea.SetMarginWidth(0, 22)    # 经实际测试，第一个参数 0 时第二个参数 width 为右侧行号部分宽度，实际上默认还有一部分是显示书签等位置的
        self.Textarea.SetMarginWidth(1, 0)    # 经实际测试，第一个参数 1 时第二个参数 width 为显示书签等位置的宽度
        self.Textarea.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER, "size:%d,face:%s" % (pb-2, face1))
        self.Textarea.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, "size:%d,face:%s" % (pb, face3))

        textareaFont = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, u'Fixedsys')  # 设置字体
        self.Textarea.SetFont(textareaFont)
        
        sizer = wx.BoxSizer()
        sizer.Add(self.Textarea, 1, wx.EXPAND)
        self.SetSizer(sizer)


class PageNote(PageEditor):
    """
    便签管理器目前只是编辑器的另外一种形式
    """
    # 网络保存的状态(如果网络读取成功了，则设置为 True)
    _net_save = True
    # 本地文件路径
    _local_file= r'c:\Hickpad.hic'
    
    def __init__(self, parent):
        PageEditor.__init__(self, parent)
        # 获得便签内容
        self.Textarea.SetText(self.getNote())
        # 每分钟自动保存内容到本地文件
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onSaveNote, self.timer)
        self.timer.Start(6000)
        
    def onSaveNote(self, event):
        self.saveNote()
        
    def saveNote(self):
        self.Textarea.SaveFile(self._local_file)
        
    def getNote(self):
        """
        获得便签内容(尝试从网络读取)
        """
        
        if not os.path.isfile(self._local_file):
            f = file(self._local_file, 'w')
            f.write("\n")
            f.close()
            
        f = file(self._local_file, 'r')  
        content =  f.read()  
        content = content.decode('gbk')
            
        ############################### 暂时直接返回本地文件内容
        return content


        socket.setdefaulttimeout(10)    # 获取内容 10s 超时
        self._net_save = True
        try: 
            # 从网络获得文件内容
            cj = cookielib.CookieJar()
            url_login ='http://www.hickwu.com/file.php'
            body = (('filename','hickpad'), ('get', '1'))
            opener=urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            opener.addheaders = [('User-agent',
                'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)')]
            urllib2.install_opener(opener)
            req=urllib2.Request(url_login,urllib.urlencode(body))
            u=urllib2.urlopen(req)
        except urllib2.URLError, e: 
            # 标记不进行网络保存
            self._net_save = False
            #print 'file open error:', e 
            dlg = wx.MessageDialog(self, "The network file operating is disabled for: \n" + str(e),  
                                'Save err notice', wx.YES | wx.ICON_WARNING)
        
            result = dlg.ShowModal()
        
        # 如果没有捕获异常, 则获得具体内容
        if self._net_save:
            content = u.read()[11:]
            content = content.decode('utf8')
            #content = content.encode('gbk')
            #print content
        else:
            # 从文件获得内容
            f = file(self._local_file, 'r')  
            content =  f.read()  
            content = content.decode('gbk')
        
        return content

class ThreadTTSCheck(threading.Thread):
    """检查语音提醒的线程"""
    def __init__(self):
        super(ThreadTTSCheck, self).__init__()
        # dolog("thread init %s " % threading.currentThread().getName())
        self.start()
        
    ### 线程执行逻辑
    def run(self):
        dolog("开始检查语音任务 ThreadTTSCheck %s" % threading.currentThread().getName())

        ### 改版成走 url 取
        # url = "http://www.hick.com/notes"
        url = "http://www.webrube.com/notes"
        # 打开 url 出错的可能性比较大
        try:
            res = urllib2.urlopen(url)
        except urllib2.URLError, e: 
            dolog("err when open url:  %s, err: %s" % (url, e))
        except:
            dolog("unknow error: %s" % (e,))


        
        soup = BeautifulSoup(res.read())
        notes_dom = soup.select("div.note")
        if len(notes_dom):
            for item in notes_dom:
                title = item.select("div.title")[0].string
                content = item.select("div.content")[0].string
                note_time = item.select("div.note_time")[0].string
                method = item.select("div.method")[0].string
                note_id = item.select("div.id")[0].string

                say_text = note_time + "," + title +  "," + content
                tts_say(say_text)
                # 删除提醒
                res = urllib2.urlopen("%s/del/%s" % (url, note_id))

        dolog("任务检查后执行任务数: %s" % (len(notes_dom,)))


        # wx.CallAfter(self.postTime, u" %s 线程结束" % tname)


class PageAlarm(wx.Panel):
    
    # 正在提醒的 id 列表
    _aid_alarming = []

    def __init__(self, parent):
        """
        提醒管理器主界面
        """
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        
        # 水平 boxsizer
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        # 列表字段
        self.list = AutoWidthListCtrl(self)
        self.list.InsertColumn(0, u'ID', width=40)
        self.list.InsertColumn(1, u'标题', width=230)
        self.list.InsertColumn(2, u'时间', wx.LIST_FORMAT_RIGHT, 110)
        self.list.InsertColumn(3, u'频率', wx.LIST_FORMAT_RIGHT, 90)
        
        # 初始化列表数据
        self.setListCtrl()
        
        # 列表事件
        self.list.Bind(wx.EVT_LEFT_DCLICK, self.onDoubleClick)
        self.list.Bind(wx.EVT_KEY_UP, self.onKeyUp)

        hbox.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(hbox)
        
        # 启动定时器
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onCheckAlarm, self.timer)
        self.timer.Start(5000)    # 每 5s 检查一次

        ### 语音提醒检查器
        # 注意太短了会导致任务没执行完，下次任务又开始
        self.timerTask = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTTSTask, self.timerTask)
        self.timerTask.Start(1000 * 60 * 1) # 单位为毫秒，定期检查， 检查时间不能短于最长的提醒时间，要不然一直提醒容易无法退出
        # self.timerTask.Start(1000 * 3 * 1) # 单位为毫秒，定期检查， 检查时间不能短于最长的提醒时间，要不然一直提醒容易无法退出


    
    def setListCtrl(self):
        """
        从数据库获得任务数据
        """
        db_file = os.path.join(exe_dir, 'data.db3')
        db_file_flag = os.path.isfile(db_file)
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        if not db_file_flag:
            #  提醒表
            c.execute('''CREATE TABLE [alarm] (
                      [aid] INTEGER PRIMARY KEY, 
                      [title] VARCHAR(255),
                      [content] TEXT, 
                      [plan_time] VARCHAR(16), 
                      [add_time] VARCHAR(16),
                      [state] INT DEFAULT 0);''')     ### state 默认为 0 ， 正常查询，只获得 < 1 的查询选项。

            # 任务表: 移植抓取系统表结构先
            c.execute('''CREATE TABLE [tasks] (
                      [id] INTEGER PRIMARY KEY, 
                      [name] VARCHAR(255),
                      [desciption] TEXT, 
                      [last_time] VARCHAR(16), 
                      [next_time] VARCHAR(16),
                      [item_time] VARCHAR(16),
                      [created_at] VARCHAR(16),
                      [updated_at] VARCHAR(16),
                      [msg] VARCHAR(255),
                      [rev1] VARCHAR(255),
                      [rev2] VARCHAR(255),
                      [title] VARCHAR(255),
                      [url] VARCHAR(255),
                      [type] VARCHAR(255),
                      [day_count] INT DEFAULT 0);''')

        items = []
        i = 1
        c.execute('select aid, title, plan_time, add_time from alarm where state < 1 limit 100')
        for row in c:
            row_item = (str(row[0]), row[1], row[2], row[3])
            items.append(row_item)
            i += 1
        conn.close()
        
        # 列表数据
        self.list.DeleteAllItems()  # 删除所有项以后重新获得
        for i in items:
            index = self.list.InsertStringItem(sys.maxint, str(i[0]))
            self.list.SetStringItem(index, 1, i[1])
            self.list.SetStringItem(index, 2, i[2])
            
        
        return True
    
    def onCheckAlarm(self, event):
        """
        提醒检查
        """
        
        db_file = os.path.join(exe_dir, 'data.db3')
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        items = []
        i = 1
        check_sql = "select aid, title, content, plan_time from alarm where state < 1 and plan_time <= '%s'" % (time.strftime('%Y-%m-%d %H:%M'), )
        c.execute(check_sql)
#        print time.strftime('%Y-%m-%d %H:%M')
        to_alarm = []
        for row in c:
            aid = row[0]
            # 不在正提醒的列表里才提醒并加到列表中
            if not aid in self._aid_alarming:
                self._aid_alarming.append(aid)
                to_alarm.append(aid)
#                print "to alarm %s " % aid
        conn.close()
                
        # 循环显示
        for aid in to_alarm:
#            print "alarming %s " % aid
            Alarm = AlarmView(self, aid)
            Alarm.Show()    # 注意这里如果是 ShowModal 的话，会不必要的阻塞程序


    def onTTSTask(self, event):
        """
        任务检查
        """

        dolog("开始检查语音任务 onTTSTask")
        ThreadTTSCheck()
        return
        ### 以下代码暂时保留
#         db_file = os.path.join(exe_dir, 'data.db3')
#         conn = sqlite3.connect(db_file)
#         c = conn.cursor()
#         items = []
#         i = 1
#         check_sql = "select id,name,url,rev1,title from tasks where type < 2 and next_time <= '%s'" % (time.strftime('%Y-%m-%d %H:%M'), )
#         c.execute(check_sql)
# #        print time.strftime('%Y-%m-%d %H:%M')
#         to_alarm = []
#         for row in c:
#             ### google 网站收录数需要特别处理下
#             url = row[2]
#             selector = row[3]
#             title = row[4]

#             # print time.strftime('%Y-%m-%d %H:%M')
#             # print row

#             dolog(str(row))
            
#             send_headers = {
#               'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1',
#               "Accept": "image/gif, image/jpeg, application/xaml+xml,  */*",
#             }
#             proto, rest = urllib.splittype(url)  
#             host, rest = urllib.splithost(rest) 
#             send_headers['Host'] = host
#             req = urllib2.Request(url, headers=send_headers) 
#             response = urllib2.urlopen(req)
#             content = response.read()
#             reg = re.compile(r'''> +''')
#             content = reg.subn('>', content)[0]
#             soup = BeautifulSoup(content)
#             try_list = (selector, 'div.artic_text')
#             for selector in try_list:
#                 selected_item = soup.select(selector)
#                 if len(selected_item) > 0:
#                     break

#             txt = time.strftime('%Y-%m-%d %H:%M') + u"没找到"
#             if len(selected_item) > 0:
#                 get_str =  selected_item[0].string
#                 get_list = get_str.split(" ")

#                 if len(get_list) > 1 :
#                     # txt = u"博客域名收录网页数量：" + get_list[1]
#                     txt = time.strftime('%Y-%m-%d %H:%M ') + title + "," + get_list[1]
#                     dolog(txt.encode("UTF-8")) 


#             self.engine.say(txt)
#             self.engine.runAndWait()
#             # print "find sth"
#             # print selected_item                

#         conn.close()
        
    def onDoubleClick(self, event):
        # curr_item 为行索引，从 0 开始的
        curr_item = self.list.GetFocusedItem()  # 获得聚焦的行索引
        curr_item = self.list.GetFirstSelected() # 获得被选择的第一行的索引(可能被选择多行)
        # CurrItem 实际上是单元个 cell, 第二个参数为列数
        # 如果当前没有选择任何行，则输出专门提示信息
        if curr_item < 0:
            # 添加提醒
            self.AlarmItem = AlarmEdit(self)
        else:
            # 获得该行第二列的单元格
            self.AlarmItem = AlarmEdit(self, self.list.GetItem(curr_item).GetText())
            #Cell2 = self.list.GetItem(curr_item, 1)
            #Cell3 = self.list.GetItem(curr_item, 2)
            #print u"当前行 %d, 第二列 %s, 第三列 %s" % (curr_item, Cell2.GetText(), Cell3.GetText())
            
        self.AlarmItem.ShowModal()
        
    def onKeyUp(self, event):
        """
        处理键盘操作： 目前包括 delete 删除
        """
        keycode = event.GetKeyCode()
        curr_item = self.list.GetFirstSelected()
        # 如果是 delete 键(keycode 为 127)
        if keycode == 127:
            aid = self.list.GetItem(curr_item).GetText()
            # 从数据库删除记录
            db_file = os.path.join(exe_dir, 'data.db3')
            conn = sqlite3.connect(db_file)
            c = conn.cursor()
            delete_str = "delete from alarm  where aid = %d;" % int(aid)
            c.executescript(delete_str)
            conn.close()
            
        # 更新显示列表
        self.setListCtrl()
        
class AlarmView(wx.Dialog):
    """
    查看提醒项
    注意需要指定 parent 为 PageAlarm 的实例，也就是该实例必须为 PageAlarm 的子窗口，有相关依赖
    """
    _aid = None
    
    # 记录父窗口(并非必要，但是先这样记使程序结构清晰)
    ParentListCtrl = None
    
    def __init__(self, parent, aid=None):
        
        wx.Dialog.__init__(self, parent, -1, u'提醒项', size=(500,350))
        
        self._aid = aid
        self.ParentListCtrl = parent
        
        # 从数据库获得提醒信息
        db_file = os.path.join(exe_dir, 'data.db3')
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute('select aid, title, content, plan_time, add_time from alarm where aid = %s' % int(aid))
        for row in c:
            title = row[1]
            content = row[2]
            plan_time = row[3]
            alarm_date = plan_time[0:10]
            alarm_time = plan_time[11:16]
        
        # 获得即将到期的俩提醒
        check_sql = "select aid, title, content, plan_time from alarm where state < 1 and plan_time > '%s' order by plan_time limit 2 " % (time.strftime('%Y-%m-%d %H:%M'), )
        c.execute(check_sql)
        to_alarm = []
        
        for row in c:
            aid = row[0]
            to_alarm.append(u"%s\t%s" % (row[3], row[1]))
        conn.close()
        # 没有提醒时的文字
        if not len(to_alarm):
            to_alarm.append(u"没有即将到期的提醒")
        
        panel = wx.Panel(self) 
        
        ### 首先创建各个显示控件
        # 行: 标题
        LabelTitle = wx.StaticText(panel, -1, u"提醒名称: ")
        InputTitle = wx.TextCtrl(panel, -1, title, size=(400, 20))
        # 行: 内容
        LabelContent = wx.StaticText(panel, -1, u"提醒内容: ")
        InputContent = wx.TextCtrl(panel, -1, content, size=(400, 200), style=wx.TE_MULTILINE)
        # 行: 时间
        LabelDatetime = wx.StaticText(panel, -1, u"提醒时间: ")
        NowDT = wx.DateTimeFromDMY(int(alarm_date[8:10]), int(alarm_date[5:7]) - 1, int(alarm_date[0:4]))
        InputDate = wx.DatePickerCtrl(panel, dt=NowDT, size=(90,-1), style = wx.DP_DROPDOWN|wx.DP_SHOWCENTURY)
        #InputDate.SetValue(datetime.datetime(2009, 2, 3))
        InputTimeSpin = wx.SpinButton(panel, -1, wx.DefaultPosition, (-1,21), wx.SP_VERTICAL)
        InputTime = masked.TimeCtrl(
                        panel, -1, name="24 hour control", fmt24hr=True,
                        spinButton = InputTimeSpin,
                        display_seconds = False,
                        value='%s:00' % alarm_time
                        )
        
        # 按钮
        ButtonSave = wx.Button(panel, -1, u'修改') 
        ButtonCancel = wx.Button(panel, -1, u"取消") 
        LabelInfo = wx.StaticText(panel, -1, u"可以直接修改提醒时间来延迟到该时间再次提醒。")
        
        # 提示信息
        LabelAlarmList = wx.StaticText(panel, -1, u"即将到期的提醒：\n")
        ToAlarmList = []
        for item in to_alarm:
            # 注意 StaticText 会自动根据文本宽度显示， 但是 \t 只会当作一个字符宽，所以不规定宽度就会有部分文本无法显示
            CurrStaticText = wx.StaticText(panel, -1, u"%s" % item, size=(300, -1))
            ToAlarmList.append(CurrStaticText)

        
        # 对象寄存 
        self.InputTitle = InputTitle
        self.InputContent = InputContent
        self.InputDate = InputDate
        self.InputTime = InputTime
        
        ### 事件绑定
        self.Bind(wx.EVT_BUTTON, self.onSave, ButtonSave)
        self.Bind(wx.EVT_BUTTON, self.onCloseDlg, ButtonCancel)
        

        ### 布局的基本结构: 一个垂直 boxsizer组织全局, 
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        # 注意 sizer 命名规范更方便和位置对应起来(subSizer 表示一级 size 的子 sizer)
        subSizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        # 行: 标题
        subSizer.Add(LabelTitle, 0,  wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        subSizer.Add(InputTitle, 1,  wx.ALIGN_CENTER_VERTICAL)
        # 行: 内容
        subSizer.Add(LabelContent, 0,  wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        subSizer.Add(InputContent, 1)
        # 行: 日期和时间(再套一个水平 sizer)
        subSizer.Add(LabelDatetime, 0,  wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        subDatetimeSizer = wx.BoxSizer(wx.HORIZONTAL)
        subDatetimeSizer.Add(InputDate, 0)
        subDatetimeSizer.Add(InputTime, 0)
        subDatetimeSizer.Add(InputTimeSpin, 0)
        subSizer.Add(subDatetimeSizer, 0)
        
        mainSizer.Add(subSizer, 0, wx.EXPAND|wx.ALL, 10)
        
        # 按钮放在水平sizer
        subBtnSizer = wx.BoxSizer(wx.HORIZONTAL)
        subBtnSizer.Add(LabelInfo, 0, wx.TOP, 3)
        subBtnSizer.Add((20,20), 1) # 按钮之间增加间隙
        subBtnSizer.Add(ButtonSave, 0)
        subBtnSizer.Add((20,20), 1) # 按钮之间增加间隙
        subBtnSizer.Add(ButtonCancel, 0)
        
        mainSizer.Add(subBtnSizer, 1, wx.ALIGN_CENTER|wx.ALL, 10)
        
        # 即将到期的提醒(一个水平 sizer 里套一个垂直 sizer)
        subListSizer = wx.BoxSizer(wx.HORIZONTAL)
        subListVerticalSizer = wx.BoxSizer(wx.VERTICAL)
        subListVerticalSizer.Add(LabelAlarmList, 0)
        for item_alarm in ToAlarmList:
            subListVerticalSizer.Add(item_alarm, 0, wx.BOTTOM, 3)
        
        subListSizer.Add(subListVerticalSizer, 0)
        mainSizer.Add(subListSizer, 1, wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        

        panel.SetSizer(mainSizer) 

        mainSizer.Fit(self)                                      
        mainSizer.SetSizeHints(self) 

    def onCloseDlg(self, event):
        # 插入数据库
        db_file = os.path.join(exe_dir, 'data.db3')
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        update_str = "update alarm set state = 2 where aid = %d;" % (int(self._aid), )
        
        c.executescript(update_str)
        conn.close()
        
        self.ParentListCtrl.setListCtrl()
        
        self.Close()
        
    def onSave(self, event):
        """
        保存项
        """
        title = self.InputTitle.GetValue()
        content = self.InputContent.GetValue()
        plan_date = self.InputDate.GetValue().Format('%Y-%m-%d')
        plan_time = self.InputTime.GetValue()
        
        # 插入数据库
        db_file = os.path.join(exe_dir, 'data.db3')
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        # 根据 _aid 决定编辑还是插入
        if self._aid == None:
            insertStr = "insert into alarm(title, content, plan_time) values ('%s', '%s', '%s %s');" % (title, content, plan_date, plan_time)
            c.executescript(insertStr)
        else:
            update_str = "update alarm set title = '%s', content = '%s', plan_time = '%s %s' where aid = %d;" % (title, content, plan_date, plan_time, int(self._aid))
            #print update_str
            c.executescript(update_str)
        conn.close()
        
        # 如果当前 aid 属于正在提醒的 aid ，则从列表中删除
        if self._aid in self.ParentListCtrl._aid_alarming:
            self.ParentListCtrl._aid_alarming.remove(self._aid)
        
        # 重新渲染
        self.ParentListCtrl.setListCtrl()
        
        self.Close()
        

class AlarmEdit(wx.Dialog):
    """
    添加和编辑提醒项(aid 为 None 表示添加)
    注意需要指定 parent 为 PageAlarm 的实例，也就是该实例必须为 PageAlarm 的子窗口,有相关依赖
    """
    _aid = None     # 如果是编辑。该值保存提醒 id, 否则为 None
    
    # 记录父窗口(并非必要，但是先这样记使程序结构清晰)
    ParentListCtrl = None
    
    def __init__(self, parent, aid=None):
        ### 先确定数据值(添加和编辑不一样)
        if aid == None:
            title = u''
            content = u''
            ### 默认时间和日期目前没有用
            alarm_date = time.strftime('%Y-%m-%d')
            alarm_time = time.strftime('%H:%M')
            
            dialog_title = u'新建提醒'
            submit_title = u'新建'
        else:
            # 从数据库获得记录信息
            db_file = os.path.join(exe_dir, 'data.db3')
            db_file_flag = os.path.isfile(db_file)
            conn = sqlite3.connect(db_file)
            c = conn.cursor()
            c.execute('select aid, title, content, plan_time, add_time from alarm where aid = %s' % int(aid))
            for row in c:
                title = row[1]
                content = row[2]
                plan_time = row[3]
                alarm_date = plan_time[0:10]
                alarm_time = plan_time[11:16]
            conn.close()
            
            dialog_title = u'编辑提醒'
            submit_title = u'保存'
            

        wx.Dialog.__init__(self, parent, -1, dialog_title, size=(700,300))
        
        panel = wx.Panel(self)
        self._aid = aid
        self.ParentListCtrl = parent
                
        ### 首先创建各个显示控件
        # 行: 标题
        LabelTitle = wx.StaticText(panel, -1, u"提醒名称: ")
        InputTitle = wx.TextCtrl(panel, -1, title, size=(400, 20))
        # 行: 内容
        LabelContent = wx.StaticText(panel, -1, u"提醒内容: ")
        InputContent = wx.TextCtrl(panel, -1, content, size=(400, 200), style=wx.TE_MULTILINE)
        # 行: 时间
        LabelDatetime = wx.StaticText(panel, -1, u"提醒时间: ")
        NowDT = wx.DateTimeFromDMY(int(alarm_date[8:10]), int(alarm_date[5:7]) - 1, int(alarm_date[0:4]))
        InputDate = wx.DatePickerCtrl(panel, dt=NowDT, size=(90,-1), style = wx.DP_DROPDOWN|wx.DP_SHOWCENTURY)
        #InputDate.SetValue(datetime.datetime(2009, 2, 3))
        InputTimeSpin = wx.SpinButton(panel, -1, wx.DefaultPosition, (-1,21), wx.SP_VERTICAL)
        InputTime = masked.TimeCtrl(
                        panel, -1, name="24 hour control", fmt24hr=True,
                        spinButton = InputTimeSpin,
                        display_seconds = False,
                        value='%s:00' % alarm_time
                        )
        #InputTime.SetValue(wx.DateTime_Now())
        
        # 按钮
        ButtonSave = wx.Button(panel, -1, submit_title) 
        ButtonCancel = wx.Button(panel, -1, u"取消") 
        
        # 对象寄存 
        self.InputTitle = InputTitle
        self.InputContent = InputContent
        self.InputDate = InputDate
        self.InputTime = InputTime
        
        ### 事件绑定
        self.Bind(wx.EVT_DATE_CHANGED, self.onDateChanged, InputDate)   # 日期变化
        self.Bind(masked.EVT_TIMEUPDATE, self.onTimeChanged, InputTime)   # 时间变化
        self.Bind(wx.EVT_BUTTON, self.onSave, ButtonSave)
        self.Bind(wx.EVT_BUTTON, self.onCloseDlg, ButtonCancel)
        

        ### 布局的基本结构: 一个垂直 boxsizer组织全局, 
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        # 注意 sizer 命名规范更方便和位置对应起来(subSizer 表示一级 size 的子 sizer)
        subSizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        # 行: 标题
        subSizer.Add(LabelTitle, 0,  wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        subSizer.Add(InputTitle, 1,  wx.ALIGN_CENTER_VERTICAL)
        # 行: 内容
        subSizer.Add(LabelContent, 0,  wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        subSizer.Add(InputContent, 1)
        # 行: 日期和时间(再套一个水平 sizer)
        subSizer.Add(LabelDatetime, 0,  wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        subDatetimeSizer = wx.BoxSizer(wx.HORIZONTAL)
        subDatetimeSizer.Add(InputDate, 0)
        subDatetimeSizer.Add(InputTime, 0)
        subDatetimeSizer.Add(InputTimeSpin, 0)
        subSizer.Add(subDatetimeSizer, 0)
        
        mainSizer.Add(subSizer, 0, wx.EXPAND|wx.ALL, 10)
        
        # 按钮放在水平sizer
        subBtnSizer = wx.BoxSizer(wx.HORIZONTAL)
        subBtnSizer.Add(ButtonSave, 0)
        subBtnSizer.Add((20,20), 1) # 按钮之间增加间隙
        subBtnSizer.Add(ButtonCancel, 0)
        mainSizer.Add(subBtnSizer, 1, wx.ALIGN_CENTER|wx.BOTTOM, 10)

        panel.SetSizer(mainSizer) 

        mainSizer.Fit(self)                                      
        mainSizer.SetSizeHints(self) 
        self.Center()

    def onCloseDlg(self, event):
        self.Close()
        
    def onSave(self, event):
        """
        保存项
        """
        title = self.InputTitle.GetValue()
        content = self.InputContent.GetValue()
        plan_date = self.InputDate.GetValue().Format('%Y-%m-%d')
        plan_time = self.InputTime.GetValue()
        
        # 插入数据库
        db_file = os.path.join(exe_dir, 'data.db3')
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        # 根据 _aid 决定编辑还是插入
        if self._aid == None:
            insertStr = "insert into alarm(title, content, plan_time) values ('%s', '%s', '%s %s');" % (title, content, plan_date, plan_time)
            c.executescript(insertStr)
        else:
            update_str = "update alarm set title = '%s', content = '%s', plan_time = '%s %s' where aid = %d;" % (title, content, plan_date, plan_time, int(self._aid))
            #print update_str
            c.executescript(update_str)
        conn.close()
        
        # 如果当前 aid 属于正在提醒的 aid ，则从列表中删除
        if self._aid in self.ParentListCtrl._aid_alarming:
            self.ParentListCtrl._aid_alarming.remove(self._aid)
        
        # 重新渲染
        self.ParentListCtrl.setListCtrl()
        
        self.Close()
        
    def onDateChanged(self, event):
        #print "OnDateChanged: %s\n" % event.GetDate()
        return True
        
    def onTimeChanged(self, event):
        timectrl = self.FindWindowById(event.GetId())
        ib_str = [ "  (out of bounds)", "" ]
        #print '%s time = %s%s\n' % ( timectrl.GetName(), timectrl.GetValue(), ib_str[ timectrl.IsInBounds() ] )
        return True 
            
class SystrayIco(wx.TaskBarIcon):
    """
    系统托盘
    """
    _id_exit = wx.NewId()
    
    def __init__(self, frame):
        """
        主 frame 传递进来，方便控制主 frame
        """
        wx.TaskBarIcon.__init__(self)
        self.frame = frame
        # 创建系统托盘图标并绑定事件
        self.SetIcon(wx.Icon(name='ico/Hickpad.ico', type=wx.BITMAP_TYPE_ICO), self.frame.GetTitle())
        
        # 暂时还不知道怎么只响应双击，不响应单击
        #self.Bind(wx.EVT_TASKBAR_LEFT_UP, self.frame.onSwitchDisplay)
        
        #self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.frame.onSwitchDisplay)
        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.onDclick)
        

    # 重载系统托盘弹出菜单
    def CreatePopupMenu(self):
        menu = wx.Menu()
        self.Bind(wx.EVT_MENU, self.frame.onSwitchDisplay, menu.Append(wx.ID_ANY, u'显示/隐藏主窗口'))
        menu.Append(self._id_exit, u'退出')
        self.Bind(wx.EVT_MENU, self.frame.onExit, id=self._id_exit)
        return menu
    
    def onDclick(self, event):
        AlarmAdd = AlarmEdit(self.frame.notebook.PageAlarm)
        AlarmAdd.Show()
        AlarmAdd.Center()

#=======================================================================
class AutoWidthListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
    """
    自动列宽的 ListCtrl
    """
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT)
        ListCtrlAutoWidthMixin.__init__(self)

#=======================================================================
class AUIManager(aui.AuiManager):
    """
    AUI 管理器类
    """

    def __init__(self, managed_window):
        """Constructor"""
        aui.AuiManager.__init__(self)
        self.SetManagedWindow(managed_window)

#=======================================================================
class AUINotebook(aui.AuiNotebook):
    """
    AUI 多 tab 页管理类
    """
    
    # 编辑器打开个数
    tabCount = 0
    # 提醒管理器打开状态(打开以后被置为 page_idx)
    _alarm_page_idx = None
    # 便签管理器 page_idx
    _note_page_idx = None
    # 便签管理器和提醒管理器对象
    PageNote = None
    PageAlarm = None

    def __init__(self, parent):
        """Constructor"""
        aui.AuiNotebook.__init__(self, parent=parent)
        # AuiNotebook 的默认风格(注意区分 style 和 art )
        self.default_style = aui.AUI_NB_DEFAULT_STYLE | aui.AUI_NB_TAB_EXTERNAL_MOVE | wx.NO_BORDER 
        self.SetWindowStyleFlag(self.default_style)
        
        # 设置 art (tab 样式)
        art = aui.ChromeTabArt()
        self.SetArtProvider(art)
        
        #print self.GetDefaultBorder()
        
        
        # 初始化打开提醒管理器
        self.createAlarmPage()
        
        # 初始化打开便签管理器
        self.createNotePage()

        # Noteobook 中添加页(page)
        pages = [PageEditor]
        for page in pages:
            self.tabCount += 1
            label = u"页签 #%i" % self.tabCount
            tab = page(self)
            self.AddPage(tab, label, False)

    def createAlarmPage(self):
        """
        创建提醒管理器
        """
        if self._alarm_page_idx == None:
            page_bmp = wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16, 16))
            self._alarm_page_idx = self.GetPageCount()   # 注意看了下源代实现发现 page_idx 就是 GetPageCount 而来的
            self.PageAlarm = PageAlarm(self) 
            self.AddPage(self.PageAlarm, u'提醒管理器', False, page_bmp)
            self.SetPageTextColour(self._alarm_page_idx, wx.BLUE)
        else:
            print "PageAlarm already opened"
            
    def createNotePage(self):
        """
        创建便签管理器
        """
        if self._note_page_idx == None:
            page_bmp = wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16, 16))
            self._note_page_idx = self.GetPageCount()   # 注意看了下源代实现发现 page_idx 就是 GetPageCount 而来的
            self.PageNote = PageNote(self)
            self.AddPage(self.PageNote, u'便签管理器', False, page_bmp)
            self.SetPageTextColour(self._note_page_idx, wx.BLUE)
        else:
            print "PageNote already opened"

#=======================================================================
class HickFrame(wx.Frame):
    """
    主 frame
    """
    
    # 退出
    _id_menu_exit = wx.NewId()
    # 置顶菜单 id
    _id_menu_tool_top = wx.NewId()
    # 阅读剪切板文本
    _id_menu_read_clip = wx.NewId()
    # 隐藏主菜单的 id
    _id_menu_hide_menubar = wx.NewId()
    # 隐藏主 frame
    _id_menu_hide_frame = wx.NewId()
    
    def __init__(self):
        """主 Frame : 创建 AUI 管理器以及 Notebook 、菜单等"""
        title = "Hickey"
        wx.Frame.__init__(self, None, wx.ID_ANY, title=title, size=(600, 400), 
                          style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.CAPTION|wx.STAY_ON_TOP)
        
        # 这里是应用程序任务栏 ico
        self.SetIcon(wx.Icon('ico/Hickpad.ico', wx.BITMAP_TYPE_ICO))

        # AUI 管理器
        self.aui_mgr = AUIManager(self)
        
        # AUI notebook 组件
        self.notebook = AUINotebook(self)
        
        # 把 notebook 添加到 AUI 管理器(关联)
        self.aui_mgr.AddPane(self.notebook, aui.AuiPaneInfo().Name("notebook_content").CenterPane().PaneBorder(False))
        self.aui_mgr.Update() # 创建以后一般需要更新下界面
        
        # 绑定关闭 page 事件()
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.closePage, self.notebook) 

        # 创建菜单
        self.createMenu()
        
        # 快捷键定义
        acceltbl = wx.AcceleratorTable( [ #Using an accelerator table
                (wx.ACCEL_CTRL, ord('M'), self._id_menu_hide_menubar),
                (wx.ACCEL_CTRL, ord('Q'), self._id_menu_exit),
            ])  
        self.SetAcceleratorTable(acceltbl)
        

        
        # 系统托盘图标
        self.taskBarIcon = SystrayIco(self)
        
        # 退出事件重新绑定
        self.Bind(wx.EVT_CLOSE, self.onClose) # 截获关闭按钮等的关闭事件：只做隐藏操作
        self.Bind(wx.EVT_ICONIZE, self.onIconfiy) # 在任务栏点时隐藏主窗口
        
        # 注册表自动启动本程序
        self.initSystem()
        
#        #=========================================================== 调试
#        Alarm = AlarmView(self.notebook.PageAlarm, 3)
#        Alarm.Show()    # 注意这里如果是 ShowModal 的话，会不必要的阻塞程序
        
        self.Center()

       
        
    def initSystem(self):
        """
        系统环境的初始化相关操作
        """
        # 注册表操作
        program_file = os.path.join(exe_dir, 'release.pyw')
        key = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER,
                                  'Software\\Microsoft\\Windows\\CurrentVersion\\Run', 
                                  0, win32con.KEY_ALL_ACCESS)
        ##### 暂时不注册，靠在启动里手工添加
        # win32api.RegSetValueEx(key, 'HickeyStartup', 0, win32con.REG_SZ, program_file) # 注意这里还区分类型，必须是数字 1 不能是字符 '1'
        
        # 热键注册: hide/show main frame (depend__on win32con)
        # 主程序显示隐藏控制
        self.RegisterHotKey(self._id_menu_hide_frame, win32con.MOD_CONTROL|win32con.MOD_ALT, ord('H'))
        self.Bind(wx.EVT_HOTKEY, self.onSwitchDisplay, id=self._id_menu_hide_frame)
        # 阅读剪切板文本
        self.RegisterHotKey(self._id_menu_read_clip, win32con.MOD_CONTROL|win32con.MOD_ALT, ord('D'))
        self.Bind(wx.EVT_HOTKEY, self.onReadClipBorad, id=self._id_menu_read_clip)
        # 置顶窗口 topmost
        self.RegisterHotKey(self._id_menu_tool_top, win32con.MOD_CONTROL|win32con.MOD_ALT, ord('T'))
        self.Bind(wx.EVT_HOTKEY, self.onSetTopMost, id=self._id_menu_tool_top)
        #self.RegisterHotKey(self.Id_Hotkey_Top, win32con.MOD_CONTROL|win32con.MOD_ALT, ord('T'))
        #self.Bind(wx.EVT_HOTKEY, self.OnSetTopMost, id=self.Id_Hotkey_Top)
        #wx.EVT_COMMAND
                
    def closePage(self, event):
        """
        创建主菜单
        """
        # 这里获得的是 AUINotebook 对象, event 是(print 出来可查看) auibook.AuiNotebookEvent
        ctrl = event.GetEventObject()
        # 这里的 self 是 HickFrame
        # event.GetSelection 可以获得当前选择的 page_idx, 注意这个与 GetCurrentPage 类似，只是返回 page 对象
        page = ctrl.GetPage(event.GetSelection())
        #print page.Textarea.GetTextUTF8()
        # 注意由于 PageNote 继承自 PageEditor, PageNote 的实例也是 PageEditor 的实例 所以需要先把 PageNote 的判断放在前面
        if isinstance(page, PageNote):
            #print 'PageNote closed'
            #self.notebook._note_page_idx = None
            dlg = wx.MessageDialog(self, u"不许关不许关，或者你告诉我怎么隐藏关闭按钮",
                                   u"提示",
                                   wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            event.Veto() # 不能关闭 PageNot
        elif isinstance(page, PageAlarm):
            #print 'PageAlarm closed'
            #self.notebook._alarm_page_idx = None
            dlg = wx.MessageDialog(self, u"不许关不许关，或者你告诉我怎么隐藏关闭按钮",
                                   u"提示",
                                   wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            event.Veto() # 不能关闭 PageAlarm
        elif isinstance(page, PageEditor):
            print 'PageEditor closed'
        else:
            print 'unkown Page closed'
            
        # 忽略关闭操作(忽略事件)
        #event.Veto() _note_page_idx
            

    #----------------------------------------------------------------------
    def createMenu(self):
        """
        创建主菜单
        """
        def doBind(item, handler):
            """ 菜单事件的统一绑定封装 """
            self.Bind(wx.EVT_MENU, handler, item)

        # 主菜单
        menubar = wx.MenuBar()

        # 子菜单: 文件
        fileMenu = wx.Menu()
        doBind(fileMenu.Append(wx.ID_ANY, u"新建编辑器\tCtrl+N", u"新建标签"),self.onNew)
        #doBind(fileMenu.Append(self._id_menu_hide_menubar, u"隐藏主菜单", u"隐藏主菜单"),self.onToggleMenuBar)
        doBind(fileMenu.Append(self._id_menu_hide_frame, u"隐藏主窗口", u"隐藏主窗口"),self.onSwitchDisplay)
        doBind(fileMenu.Append(self._id_menu_exit, u"退出程序\tCtrl+Q", u"退出程序"),self.onExit)

        # 关联主、子菜单
        menubar.Append(fileMenu, u"文件(&F)")
        
        # 工具菜单
        toolMenu = wx.Menu()
        clipboard_reader = toolMenu.Append(self._id_menu_read_clip, u"阅读剪切板文本(&D)\tCtrl+Alt+D")
        self.Bind(wx.EVT_MENU, self.onReadClipBorad, clipboard_reader)
        topmost = toolMenu.Append(self._id_menu_tool_top, u'活动窗口置顶(&T)\tCtrl+Alt+T')
        self.Bind(wx.EVT_MENU, self.onSetTopMost, topmost)
        
        menubar.Append(toolMenu, u"工具(&T)") 
        
        # 帮助菜单
        helpMenu = wx.Menu()
        doBind(helpMenu.Append(wx.ID_ANY, u"关于(&A)", u"关于"), self.onAbout)
        
        menubar.Append(helpMenu, u"帮助(&H)")
        
        self.MenuBarReal = menubar
        
        # 设置主 frame 的菜单栏
        self.SetMenuBar(menubar)
                
    def onClose(self, event):
        """关闭按钮等操作"""
        self.onHide(self)
    def onHide(self, event):
        """隐藏"""
        self.Hide()
    def onIconfiy(self, event):
        """任务栏操作"""
        self.onHide(self)
        event.Skip()

    def onReadClipBorad(self, event):

        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        txt = data.decode("gb2312")

        tts_say(txt)

        """
        清除系统 DNS cache
        """
        # 清系统 dns
        # dll = ctypes.windll.LoadLibrary('dnsapi.dll')
        # dll.DnsFlushResolverCache()  
        # # 浏览器 dns cache 设置
        # key = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER,
        #                           'Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings', 
        #                           0, win32con.KEY_ALL_ACCESS)
        # win32api.RegSetValueEx(key, 'DnsCacheTimeout', 0, win32con.REG_DWORD, 1) # 注意这里还区分类型，必须是数字 1 不能是字符 '1'
        # win32api.RegSetValueEx(key, 'ServerInfoTimeOut', 0, win32con.REG_DWORD, 1)
        
        # # 提示清除成功
        # dlg = wx.MessageDialog(self, u"清除系统 DNS Cache 成功。\n浏览器的 DNS Cache 超时时间被设置为 1s (如果是第一次执行，需要重启系统以后才能生效)。",
        #                        u"提示",
        #                        wx.OK | wx.ICON_INFORMATION)
        # dlg.ShowModal()
        # dlg.Destroy()
        
    def onAbout(self, event):
        info = u"开发计划：\n"
        feture_list = []
        feture_list.append(u"\n=== beta1")
        feture_list.append(u'+ 提醒功能')
        feture_list.append(u'+ 便签程序的内容也暂时先保存到 sqlite')
        feture_list.append(u'+ 显示提醒时显示即将到期的若干个提醒，并可以直接点击查看具体内容甚至修改调整')
        feture_list.append(u"\n=== beta2")
        feture_list.append(u'+ 循环多次的周期性提醒')
        feture_list.append(u'+ 系统启动时一起运行程序')
        feture_list.append(u'+ 网络保存提醒和便签')
        info += '\n'.join(feture_list)
        
        dlg = wx.MessageDialog(self, info,  u"提示", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

        
    def onSetTopMost(self, event):
        """
        置顶窗口
        """
        # 获鼠标得位置
        #curr_pos = win32gui.GetCursorPos();
        # 获得鼠标位置的窗体(注意一个视觉上的窗口比如记事本标题栏和编辑区是不同的窗体)
        #curr_frame = win32gui.WindowFromPoint(curr_pos)
        curr_frame = win32gui.GetForegroundWindow()   ### 这才是获得视觉上的窗口的最佳方法
        # 获得当前窗口(Z-Order)相关窗口，猜测 GW_HWNDFIRST 可以获得窗顶层窗口相关(下面的值就是窗口 handle 时表示当前窗口置顶)
        
        ### 以下几行代码可以删除指定窗口的菜单栏 MenuBar(当然也可以做其他操作)
        #curr_menu = win32gui.GetMenu(curr_frame)
        #print win32gui.GetMenuItemCount(curr_menu)
        #print win32gui.RemoveMenu(curr_menu, 0, win32con.MF_BYPOSITION)
        #print win32gui.DrawMenuBar(curr_frame)
        
        #curr_win = win32gui.GetForegroundWindow()
        
        #self.log(curr_frame)
        #self.log(curr_win)
        
        ### GetWindowLong  获得窗口扩展风格(其中包含 Z-oder 信息)
        win_style = win32gui.GetWindowLong(curr_frame, win32con.GWL_EXSTYLE)
        ### 从 MSDN 看到窗体 window 的介绍，测试出下面的运行返回 8 时表示是顶层窗口，其他的一般是 0 ，更多参考 http://msdn.microsoft.com/en-us/library/ms632599(VS.85).aspx
        if win_style & win32con.WS_EX_TOPMOST:
            top_flag = win32con.HWND_NOTOPMOST
        else:
            top_flag = win32con.HWND_TOPMOST
            
        #self.log(top_flag)
        # 设置置顶
        win32gui.SetWindowPos(curr_frame, top_flag, 0 , 0, 0, 0, win32con.SWP_NOMOVE|win32con.SWP_NOSIZE)
        

    def onToggleMenuBar(self, event):
        """
        显示和隐藏主菜单
        """
        if self.MenuBar.GetMenuCount():
            self.SetMenuBar(wx.MenuBar())
        else:
            self.SetMenuBar(self.MenuBarReal)
        
        
    def onNew(self, event):
        """
        新建 tab
        """
        self.notebook.tabCount += 1
        label = u"页签 #%i" % self.notebook.tabCount
        self.notebook.AddPage(PageEditor(self), label, False)
        
    def onSwitchDisplay(self, event):
        """
        切换显示和隐藏
        """
        if self.IsShown():
            tts_say("藏起来啦")
            self.Iconize(True)
            self.Show(False)
        else:
            tts_say("现形啦")
            self.Iconize(False)
            self.Show(True)
            self.Raise()
            #self.Textarea.SetFocus()
 
    def onExit(self, event):
        """
        退出事件
        """
        dolog("hickpad退出了")
        tts_say("亲亲的，小爷走了")
        self.taskBarIcon.Destroy()
        self.Destroy()


if __name__ == "__main__":
    app = wx.PySimpleApp()
    frame = HickFrame()
    frame.Show()
    app.MainLoop()

