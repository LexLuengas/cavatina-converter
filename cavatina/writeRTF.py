# -*- coding: utf-8 -*-

header = r"""{\rtf1\ansi\ansicpg1252\cocoartf1038\cocoasubrtf360
{\fonttbl\f0\fnil\fcharset0 Cavatina-Regular;}
{\colortbl;\red255\green255\blue255;}
\paperw11900\paperh16840\margl1440\margr1440\vieww24280\viewh13660\viewkind0\hyphauto0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\ql\qnatural\pardirnatural

\f0\fs288 \cf0 """

notascii = {
    "ö" : "\\'f6",
    "ü" : "\\'fc",
    "ä" : "\\'e4",
    "°" : "\\'b0",
    "§" : "\\'a7",
    "ß" : "\\'df",
    "Ö" : "\\'d6",
    "Ü" : "\\'dc",
    "Ä" : "\\'c4",
    "¿" : "\\'bf",
    "ñ" : "\\'f1",
    "¡" : "\\'a1",
    "Ñ" : "\\'d1",
    "é" : "\\'e9",
    "è" : "\\'e8",
    "ç" : "\\'e7",
    "à" : "\\'e0",
    "ù" : "\\'f9",
    "μ" : "\\uc0\\u956 ",
    "³" : "\\'b3",
    "²" : "\\'b2",
    "ò" : "\\'f2",
    "à" : "\\'e0",
    "Ç" : "\\'c7",
    "´" : "\\'b4",
    "¨" : "\\'a8",
    "«" : "\\'ab",
    "»" : "\\'bb",
    "º" : "\'ba",
    "ª" : "\'aa",
    "±" : "\\'b1",
    "·" : "\\'b7",
    "¬" : "\\'ac",
    "£" : "\\'a3",
}

def writeRTF(textBox, curPos):
    text = textBox.GetValue()
    wasBold = False
    rtf = header
    for i in range(len(text)):
        textBox.SetCaretPosition(i)
        if textBox.IsSelectionBold() and not wasBold:
            rtf += "\\b "
            wasBold = True
        if not textBox.IsSelectionBold() and wasBold:
            rtf += "\\b0 "
            wasBold = False

        if text[i] in ["\\", "\n", "{", "}"]:
            rtf += "\\" + text[i]
        elif text[i] in notascii:
            rtf += notascii[text[i]]
        else:
            rtf += text[i]
    rtf += "}"
    textBox.SetCaretPosition(curPos)
    return rtf

def writeRTFshort(centipede):
    """
    This method is for playback purposes only.
    - centipede: list of 2-tuples (unicode string character, bool isBold)
    """
    wasBold = False
    rtf = header
    for s, isBold in centipede:
        if isBold and not wasBold:
            rtf += "\\b "
            wasBold = True
        if not isBold and wasBold:
            rtf += "\\b0 "
            wasBold = False

        if s in ["\\", "\n", "{", "}"]:
            rtf += "\\" + s
        elif s in notascii:
            rtf += notascii[s]
        else:
            rtf += s
    rtf += "}"
    return rtf
