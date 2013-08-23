#!/usr/bin/env python
#coding=utf-8

import wx
import wx.stc

STE_STYLE_TEXT = "fore:#000001"
STE_STYLE_KEYWORD = "fore:#0000FF,bold"
STE_STYLE_COMMENT = "fore:#238E23,back:#E8FFE8"
STE_STYLE_STRING = "fore:#9F9F9F"
STE_STYLE_STRINGEOL = "fore:#FF0000,back:#E0C0E0,size:14,eol"
STE_STYLE_OPERATOR = "fore:#000001"
STE_STYLE_IDENTIFIER = "fore:#000001"
STE_STYLE_NUMBER = "fore:#00000F"
STC_STYLE_DEFAULT = "fore:#000001,back:#FFFFFF,face:%(mono)s,size:%(size)d"
STC_STYLE_TITLE1 = "fore:#00BFFF,back:#000002"
STC_STYLE_TITLE2 = "fore:#3333FF,back:#000002"
STC_STYLE_TITLE3 = "fore:#FF7F00,back:#000002"
STC_STYLE_TITLE4 = "fore:#CD6839,back:#000002"
STC_STYLE_TITLE5 = "fore:#D4D0C8,back:#000002"
STC_STYLE_LIST = "fore:#33AA33,back:#DDDDDD"


#Fixedsys
if wx.Platform == '__WXMSW__':
    faces = { 'mono' : u'Fixedsys',
              'size' : 10,
             }
else:
    faces = { 'mono' : 'Courier 10 Pitch',
              'size' : 12,
             }

def color(win, lex, keywords, styles):
    win.StyleResetDefault()
    win.SetLexer(lex)
    win.SetStyleBits(7)
    
    if lex != wx.stc.STC_LEX_CONTAINER:
        for i in range(len(keywords)):
            win.SetKeyWords(i, keywords[i])

    win.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, 
        STC_STYLE_DEFAULT % faces)
    win.StyleClearAll()
    for style, stylestring in styles:
        win.StyleSetSpec(style, stylestring)
    win.Colourise(0, win.GetTextLength())
