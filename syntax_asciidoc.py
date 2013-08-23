#!/usr/bin/env python
#coding=utf-8

import wx.stc
from syntax_color import *

keywords = ['create']
    
STYLE_DEFAULT = 1
STYLE_KEYWORD = 2
STYLE_NUMBER = 3
STYLE_STRING = 4
STYLE_STRING_TITLE = 5
STYLE_TITLE1 = 6
STYLE_TITLE2 = 7
STYLE_TITLE3 = 8
STYLE_TITLE4 = 9
STYLE_TITLE5 = 10
STYLE_LIST = 11


def syntax_asciidoc(editor):
    styles = [
        (STYLE_DEFAULT, STE_STYLE_TEXT),        #default
        (STYLE_KEYWORD, STE_STYLE_KEYWORD),     #keyword
        (STYLE_NUMBER, STE_STYLE_NUMBER),       #number
        (STYLE_STRING, STE_STYLE_STRING),       #string
        (STYLE_STRING_TITLE, STE_STYLE_STRINGEOL),       #标题
        (STYLE_TITLE1, STC_STYLE_TITLE1),       #标题1
        (STYLE_TITLE2, STC_STYLE_TITLE2),       #标题2
        (STYLE_TITLE3, STC_STYLE_TITLE3),       #标题3
        (STYLE_TITLE4, STC_STYLE_TITLE4),       #标题4
        (STYLE_TITLE5, STC_STYLE_TITLE5),       #标题5
        (STYLE_LIST, STC_STYLE_LIST),           #列表
    ]
    
    color(editor, wx.stc.STC_LEX_CONTAINER, [], styles)

import re
token_re = re.compile(r'''(?x)
    (?P<string>"[^"]*")
    |(?P<int>\b\d+\.?\d*\b)
    |(?P<iden>\b\w+\b)
    |(?P<title5>^=====.*)
    |(?P<title4>^====.*)
    |(?P<title3>^===.*)
    |(?P<title2>^==.*)
    |(?P<title1>^=.*)
    |(?P<list>^-.*)
''', re.MULTILINE)

def do_asciidoc_color(editor, pos):
    begin = editor.PositionFromLine(editor.LineFromPosition(
        editor.GetEndStyled()))
    text = editor.GetTextRange(begin, pos).encode('utf-8')
    
    i = 0
    while begin + i < pos:
        style = STYLE_DEFAULT

        r = token_re.match(text, i)
        if r:
            if r.groupdict()['int']:
                style = STYLE_NUMBER
            elif r.groupdict()['string']:
                style = STYLE_STRING
            elif r.groupdict()['title5']:
                style = STYLE_TITLE5
            elif r.groupdict()['title4']:
                style = STYLE_TITLE4
            elif r.groupdict()['title3']:
                style = STYLE_TITLE3
            elif r.groupdict()['title2']:
                style = STYLE_TITLE2
            elif r.groupdict()['title1']:
                style = STYLE_TITLE1
            elif r.groupdict()['list']:
                style = STYLE_LIST

            else:
                if r.groupdict()['iden'].lower() in keywords:
                    style = STYLE_KEYWORD

            step = r.end() - r.start()
        else:
            step = 1
            
        set_style(editor, begin+i, begin+i+step, style)
        i += step
            
def set_style(win, start, end, style):
    win.StartStyling(start, 0xff)
    win.SetStyling(end - start, style)
