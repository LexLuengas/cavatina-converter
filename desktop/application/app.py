# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, trailing-whitespace, undefined-loop-variable, redefined-builtin, too-many-arguments, unused-argument, missing-docstring, unused-variable, no-self-use, attribute-defined-outside-init, protected-access, line-too-long, too-many-locals, bare-except, too-many-instance-attributes
import sys, os, ntpath
import wx
import wx.richtext as rt
import images
import time
import re
import tempfile

import pygame.mixer as mixer

from music21 import stream #    try harder to avoid importing
#                               from music21 from outside the parser

from tools import parser as scoreParser
from tools import translateToMusic21 as translator
from tools.writeRTF import writeRTF, writeRTFshort

ID_VIEW_MENU = wx.NewId()

ID_EXPORT = wx.NewId()
ID_VIEW = wx.NewId()
ID_HIDE = wx.NewId()
ID_BOLD = wx.NewId()
ID_FONT = wx.NewId()
ID_STOP = wx.NewId()
ID_PLAY_PAUSE = wx.NewId()

ID_EVT_TEXT = 10183
ID_EVT_LEFT_UP = 10028
ID_EVT_SASH_CHANGE = 1
ARROW_KEYS = [wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_UP, wx.WXK_DOWN]

WILDCARD = "RTF files (*.rtf)|*.rtf|Text files (*.txt)|*.txt"
TYPES = [rt.RICHTEXT_TYPE_RTF, rt.RICHTEXT_TYPE_TEXT]

# Musical raw input
NOTES = "zxcvbnmasdfghjqwertyu1234567890ZXCVBNMASDFGHJQWERTYU!@#$%^&*()"
FLOATING_NOTES = [eval("u\"\\u%04.x\"" % i) for i in range(592, 623)] # unicode codepoints assigned *.ft glyphs. (Glyph substitutions don't seem to work on private use area [U+E000-U+F8FF] coded glyphs.)
INVISIBLE_NOTES = [eval("u\"\\u%04.x\"" % i) for i in range(623, 654)] # unicode codepoints assigned *.tp glyphs.
NOTE_MODIFIERS = """-="'[{\|<"""
MODIFIER_GROUPS = {
    0: r"-=",
    1: r"\"\'",
    2: r"\[{",
    3: r"\\|",
    4: r"<"
}
CLEFS = "_+"
TIMEMOD = "~"
INVERTER = "`"

class MainFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        super(MainFrame, self).__init__(*args, **kwargs)
        # self.SetBackgroundColour('WHITE') # doesn't diminish flickering
        # file info
        self.dirName = ''
        self.filePath = ''
        self.fileName = ''
        # midi control
        self.midiFile = None
        self.isPaused = False
        # metadata
        self.scoreTitle = 'Untitled'
        self.composer = os.getlogin() # UNIX only
        self.instruments = ['Piano']
        self.tempo = 80
        frameTitle = "Cavatina — Untitled"
        self.SetTitle(frameTitle)
        # audio
        mixer.init()
        mixer.music.set_volume(1.0)
        # UI
        self.initUI()
        self.initContent()
        self.Centre()
        # stopwatch
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
        self.startTime = 0.0
        self.timeElapsed = 0.0
        self.playAll = False
    
    def initUI(self):
        # Menubar
        self.initMenubar()
        
        # Toolbar
        self.initToolbars()
        toolBar = wx.BoxSizer(wx.HORIZONTAL)
        toolBar.Add(self.toolBarLeft, 1, wx.ALIGN_LEFT | wx.EXPAND)
        toolBar.Add(self.toolBarRight, 0, wx.ALIGN_RIGHT | wx.EXPAND)
        
        # Status bar (necessary?)
        self.statusBar = self.CreateStatusBar()
        self.statusBar.Show() 
        
        # Geometry
        self.SetSize((800, 600))
        
        # Splitter
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.splitter = wx.SplitterWindow(self, style = wx.SP_3DSASH | wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(108)
        
        # ---Top Panel
        self.topPanel = wx.Panel(self.splitter) # Text Panel
        
        self.textBox = rt.RichTextCtrl(self.topPanel,
            style = wx.VSCROLL | wx.HSCROLL | wx.NO_BORDER | rt.RE_MULTILINE)
        self.textAttr = rt.RichTextAttr()
        self._setFontStyle(self.textBox, self.textAttr,
            fontColor=wx.Colour(0, 0, 0),
            fontSize=18,
            fontFace="Lucida Sans Typewriter")
        self.textBox.SetMargins(wx.Point(5, 5))
        # temp variables
        self.lastCaretPos = self.textBox.GetCaretPosition()
        self.lastTextLength = 0
        self.lastCaretPosClicked = -1
        self.lastEvent = None
        self.repositionCaret = None
        self.wasSelected = False
        
        tpSizer = wx.BoxSizer(wx.VERTICAL)
        tpSizer.Add(self.textBox, wx.ID_ANY, wx.EXPAND | wx.ALL, 15)
        self.topPanel.SetSizer(tpSizer)
        
        self.textBox.Bind(wx.EVT_TEXT, self.OnTextEnter)
        self.textBox.Bind(wx.EVT_KEY_UP, self.OnTextEnter)
        self.textBox.Bind(wx.EVT_LEFT_UP, self.OnTextEnter)
        self.textBox.Bind(wx.EVT_KEY_DOWN, self.OnKey)
        
        # ---Bottom Panel
        self.bottomPanel = wx.Panel(self.splitter) # Score Panel
        
        self.scoreBox = rt.RichTextCtrl(self.bottomPanel,
            style = wx.VSCROLL | wx.HSCROLL | wx.NO_BORDER | rt.RE_READONLY)
        self.scoreAttr = rt.RichTextAttr()
        self._setFontStyle(self.scoreBox, self.scoreAttr,
            fontColor=wx.Colour(0, 0, 0),
            fontSize=144,
            fontFace="Cavatina Regular")
        self.scoreBox.SetMargins(wx.Point(50, 10))
        self.scoreBox.GetCaret().Hide()
        self.scoreBox.SetDoubleBuffered(True)
        self.removeColored = None
        self.lastColoredLength = 0
        self.tsActive = 0
        
        bpSizer = wx.BoxSizer(wx.VERTICAL)
        bpSizer.Add(self.scoreBox, wx.ID_ANY, wx.EXPAND|wx.RIGHT, -15) # Negative border, TODO: fix border bug the right way
        self.bottomPanel.SetSizer(bpSizer)
        self.scoreBox.Bind(wx.EVT_LEFT_UP, self.OnClick)
        
        # Main Sizer
        mainSizer.Add(toolBar, 0, wx.EXPAND | wx.ALL)
        mainSizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL)
        self.SetSizer(mainSizer)
        
        # Splitter (continued)
        self.splitter.SplitHorizontally(self.topPanel, self.bottomPanel)
        self.sashPosition = self.GetSize()[1] / 3
        self.splitter.SetSashPosition(self.sashPosition)
        # self.splitter.Unsplit(self.topPanel) # Hide Text Panel
        
        if not self._fontInstalled():
            print "Cavatina is not (yet) installed on this computer!"
            # raise Exception
    
    def initMenubar(self):
        # Handler bindings
        def doBind(item, handler, updateUI=None):
            self.Bind(wx.EVT_MENU, handler, item)
            if updateUI:
                self.Bind(wx.EVT_UPDATE_UI, updateUI, item)
        
        # Menus
        fileMenu = wx.Menu()
        editMenu = wx.Menu()
        viewMenu = wx.Menu()
        formatMenu = wx.Menu()
        helpMenu = wx.Menu()
        
        # ---File Menu
        menuOpen = wx.MenuItem(fileMenu, wx.ID_OPEN, "&Open\tCtrl+O", "Open a file to edit")
        menuSave = wx.MenuItem(fileMenu, wx.ID_SAVE, "&Save\tCtrl+S", "Save current file")
        menuSaveAs = wx.MenuItem(fileMenu, wx.ID_SAVEAS, "&Save As...\tCtrl+Alt+S", "Save current file as...")
        menuScoreInfo = wx.MenuItem(fileMenu, wx.ID_ANY, "&Score Info...\tCtrl+I", "Edit score information")
        menuExport = wx.MenuItem(fileMenu, ID_EXPORT, '&Export...\tCtrl+E', "Export a file to MusicXML or MIDI")
        menuExit = wx.MenuItem(fileMenu, wx.ID_EXIT, "E&xit", "Terminate the program")
        
        fileMenu.AppendItem(menuOpen)
        fileMenu.AppendSeparator()
        fileMenu.AppendItem(menuSave)
        fileMenu.AppendItem(menuSaveAs)
        fileMenu.AppendSeparator()
        fileMenu.AppendItem(menuScoreInfo)
        fileMenu.AppendSeparator()
        fileMenu.AppendItem(menuExport)
        # fileMenu.AppendSeparator()
        # fileMenu.AppendItem(menuExit)
        
        # ---Edit Menu
        menuUndo = wx.MenuItem(editMenu, wx.ID_UNDO, "&Undo\tCtrl+Z", "Undo")
        menuRedo = wx.MenuItem(editMenu, wx.ID_REDO, "&Redo\tCtrl+Y", "Redo")
        
        menuCut = wx.MenuItem(editMenu, wx.ID_CUT, "Cu&t\tCtrl+X", "Cut Selection")
        menuCopy = wx.MenuItem(editMenu, wx.ID_COPY, "&Copy\tCtrl+C", "Copy Selection")
        menuPaste = wx.MenuItem(editMenu, wx.ID_PASTE, "&Paste\tCtrl+V", "Paste Selection")
        menuClear = wx.MenuItem(editMenu, wx.ID_CLEAR, "&Delete\tDel", "Delete Selection")
        menuSelectAll = wx.MenuItem(editMenu, wx.ID_SELECTALL, "Select A&ll\tCtrl+A", "Select All Text")
        
        editMenu.AppendItem(menuUndo)
        editMenu.AppendItem(menuRedo)
        editMenu.AppendSeparator()
        editMenu.AppendItem(menuCut)
        editMenu.AppendItem(menuCopy)
        editMenu.AppendItem(menuPaste)
        editMenu.AppendItem(menuClear)
        editMenu.AppendSeparator()
        editMenu.AppendItem(menuSelectAll)
        
        # ---View Menu
        menuShow = wx.MenuItem(viewMenu, ID_VIEW, "&Show Text Panel\tCtrl+Alt+T", "Show text panel")
        menuHide = wx.MenuItem(viewMenu, ID_HIDE, "&Hide Text Panel\tCtrl+Alt+T", "Hide text panel")
        
        # viewMenu.AppendItem(menuShow)
        viewMenu.AppendItem(menuHide)
        
        # ---Format Menu
        menuBold = wx.MenuItem(viewMenu, ID_BOLD, "&Bold\tCtrl+B", "Switch to bold weight", kind=wx.ITEM_CHECK)
        menuFont = wx.MenuItem(viewMenu, ID_FONT, "&Font...", "Select font face")
        
        formatMenu.AppendItem(menuBold)
        formatMenu.AppendSeparator()
        formatMenu.AppendItem(menuFont)
        
        # ---Help Menu
        menuAbout = helpMenu.Append(wx.ID_ABOUT, "&About", "About this program")
        
        # Menu Bar
        menubar = wx.MenuBar()
        menubar.Append(fileMenu, '&File')
        menubar.Append(editMenu, '&Edit')
        menubar.Append(viewMenu, '&View')
        menubar.Append(formatMenu, '&Format')
        menubar.Append(helpMenu, '&Help')
        
        self.SetMenuBar(menubar)
        
        # Menu Events
        doBind(menuOpen, self.OnOpen)
        doBind(menuSave, self.OnSave)
        doBind(menuSaveAs, self.OnSaveAs)
        doBind(menuScoreInfo, self.OnScoreInfo)
        doBind(menuExport, self.OnExport)
        doBind(menuAbout, self.OnAbout)
        doBind(menuExit, self.OnExit)
        
        doBind(menuUndo, self.ForwardEvent, self.ForwardEvent)
        doBind(menuRedo, self.ForwardEvent, self.ForwardEvent)
        doBind(menuCut, self.ForwardEvent, self.ForwardEvent)
        doBind(menuCopy, self.ForwardEvent, self.ForwardEvent)
        doBind(menuPaste, self.ForwardEvent, self.ForwardEvent)
        doBind(menuClear, self.ForwardEvent, self.ForwardEvent)
        doBind(menuSelectAll, self.ForwardEvent, self.ForwardEvent)
        
        # doBind(menuShow, self.OnToggleView)
        doBind(menuHide, self.OnToggleView)
        
        doBind(menuBold, self.OnBold, self.OnUpdateBold)
        doBind(menuFont, self.OnFont)
    
    def initToolbars(self):
        # Handler bindings
        def doBind(item, handler, updateUI=None):
            self.Bind(wx.EVT_TOOL, handler, item)
            if updateUI:
                self.Bind(wx.EVT_UPDATE_UI, updateUI, item)
        
        # Left toolbar
        tbar1 = wx.ToolBar(self, id=wx.ID_ANY)
        self.toolBarLeft = tbar1
        
        openTool = tbar1.AddTool(-1, images._rt_open.GetBitmap(), shortHelpString="Open")
        saveTool = tbar1.AddTool(-1, images._rt_save.GetBitmap(), shortHelpString="Save")
        tbar1.AddSeparator()
        undoTool = tbar1.AddTool(wx.ID_UNDO, images._rt_undo.GetBitmap(), shortHelpString="Undo")
        redoTool = tbar1.AddTool(wx.ID_REDO, images._rt_redo.GetBitmap(), shortHelpString="Redo")
        tbar1.AddSeparator()
        boldTool = tbar1.AddTool(-1, images._rt_bold.GetBitmap(), isToggle=True, shortHelpString="Bold")
        tbar1.AddSeparator()
        fontTool = tbar1.AddTool(-1, images._rt_font.GetBitmap(), shortHelpString="Font")
        
        # wx.ArtProvider_GetBitmap(wx.ART_UNDO, wx.ART_OTHER, wx.Size(16, 16))
        doBind(openTool, self.OnOpen)
        doBind(saveTool, self.OnSave)
        doBind(undoTool, self.ForwardEvent, self.ForwardEvent)
        doBind(redoTool, self.ForwardEvent, self.ForwardEvent)
        doBind(boldTool, self.OnBold, self.OnUpdateBold)
        doBind(fontTool, self.OnFont)
        
        self.toolBarLeft.EnableTool(wx.ID_UNDO, False)
        self.toolBarLeft.EnableTool(wx.ID_REDO, False)
        
        # Right toolbar
        tbar2 = wx.ToolBar(self, id=wx.ID_ANY)
        self.toolBarRight = tbar2
        
        stop_logging = wx.LogNull() # Bug workaround for image imports
        self.playBitmap = wx.Bitmap('images/play.png', wx.BITMAP_TYPE_PNG)
        self.pauseBitmap = wx.Bitmap('images/pause.png', wx.BITMAP_TYPE_PNG)
        stopBitmap = wx.Bitmap('images/stop.png', wx.BITMAP_TYPE_PNG)
        self.playPause = tbar2.AddLabelTool(ID_PLAY_PAUSE, "Play", self.playBitmap, shortHelp="Play")
        self.stop = tbar2.AddLabelTool(ID_STOP, "Stop", stopBitmap, shortHelp="Stop")
        self.toolBarRight.EnableTool(ID_STOP, False)
        
        doBind(self.playPause, self.OnPlayPause)
        doBind(self.stop, self.OnStop)
        del stop_logging
        
        self.toolBarLeft.Realize()
        self.toolBarRight.Realize()
    
    def initContent(self):
        self.textBox.BeginSuppressUndo()
        self.textBox.WriteText(",+ ")
        self.textBox.EndSuppressUndo()
    
    # ==================
    # = Event Handlers =
    # ==================
    def ForwardEvent(self, e):
        self.textBox.ProcessEvent(e)
    
    def OnTextEnter(self, e):
        self.textBox.BeginSuppressUndo()
        self.scoreBox.BeginSuppressUndo()
        
        # Post-event fixes
        if self.repositionCaret: # TODO: reposition correction
            self.textBox.SetInsertionPoint(self.repositionCaret)
            self.repositionCaret = None
            
        self.caretPos = self.textBox.GetCaretPosition()
        isUpdateKeyEvent = e.GetEventType() != wx.EVT_KEY_UP or e.GetKeyCode() in ARROW_KEYS
        
        if self.removeColored and self.lastCaretPos != self.caretPos:
            colorStart, colorLength = self.removeColored
            ip = self.scoreBox.GetInsertionPoint()
            self.scoreBox.Remove(colorStart, colorStart + colorLength)
            self.scoreBox.SetInsertionPoint(ip)
            self.scoreBox.Refresh()
            self.removeColored = None
        
        if self.lastCaretPos != self.caretPos and isUpdateKeyEvent:
            text = self.textBox.GetValue()
            scoreText = self.scoreBox.GetValue()
            
            # Text modification
            if e.GetEventType() == ID_EVT_TEXT:
                if self.lastTextLength > len(text): # on text deletion
                    scoreCaret = self.scoreBox.GetCaretPosition()
                    self.scoreBox.Remove(scoreCaret, scoreCaret + 1)
                else:
                    if not self.wasSelected:
                        self.scoreBox.WriteText(text[(self.lastCaretPos + 1):(self.caretPos + 1)])
                    else:
                        self.scoreBox.SetValue(text)
                text = self._fixGrandStaves(text)
                scoreText = self.scoreBox.GetValue()
                scoreText = self._fixTextOffsets(text, scoreText)
                
            # Update insertion point
            if len(scoreText) > 0 and scoreText[0] == "\n":
                self.scoreBox.SetInsertionPoint(self.textBox.GetInsertionPoint() + 1)
            else:
                self.scoreBox.SetInsertionPoint(self.textBox.GetInsertionPoint())
            
            # Click event fix
            if self.lastEvent == ID_EVT_LEFT_UP and self.lastCaretPosClicked > -1:
                self.lastCaretPos = self.lastCaretPosClicked
                self.lastCaretPosClicked = -1
            
            if self.caretPos - self.lastCaretPos > 1:
                # Re-color
                colorAttr = rt.RichTextAttr()
                colorAttr.SetFlags(wx.TEXT_ATTR_TEXT_COLOUR)
                colorAttr.SetTextColour("BLACK")
                self.textBox.SetStyle((0, len(text) + 1), colorAttr)
            
            # Update information
            # self.scoreBox.Refresh()
            # self._transferBold()
            self._updateColors()
            self.lastCaretPos = self.caretPos
            self.lastTextLength = len(self.textBox.GetValue())
        
        fr, to = self.textBox.GetSelection()
        if fr != -2:
            self.wasSelected = True
        else:
            self.wasSelected = False
        
        self.lastEvent = e.GetEventType()
        self.textBox.EndSuppressUndo()
        self.scoreBox.EndSuppressUndo()
        e.Skip()
    
    def OnKey(self, e):
        if e.GetKeyCode() == wx.WXK_DELETE or e.GetKeyCode() == wx.WXK_BACK:
            fr, to = self.textBox.GetSelection()
            if fr != -2:
                event = wx.PyCommandEvent(wx.EVT_TEXT.typeId, self.GetId())
                self.OnTextEnter(event)
        if e.GetKeyCode() == wx.WXK_RIGHT:
            fr, to = self.textBox.GetSelection()
            if fr != to and to >= 2:
                self.textBox.SelectNone()
                self.textBox.SetCaretPosition(to - 2)
        if e.GetKeyCode() == wx.WXK_UP:
            e.m_keyCode = wx.WXK_RIGHT
        if e.GetKeyCode() == wx.WXK_DOWN:
            e.m_keyCode = wx.WXK_LEFT
        e.Skip()
    
    def OnFont(self, e):
        fontData = wx.FontData()
        fontData.EnableEffects(False)
        attr = rt.RichTextAttr()
        attr.SetFlags(wx.TEXT_ATTR_FONT)
        ip = self.textBox.GetInsertionPoint()
        if self.textBox.GetStyle(ip, attr):
            fontData.SetInitialFont(attr.GetFont())
        
        dlg = wx.FontDialog(self, fontData)
        if dlg.ShowModal() == wx.ID_OK:
            fontData = dlg.GetFontData()
            font = fontData.GetChosenFont()
            if font:
                attr.SetFont(font)
                attr.SetFlags(wx.TEXT_ATTR_FONT)
                self.textBox.Freeze()
                self.textBox.SetSelection(-1, -1)
                r = self.textBox.GetSelectionRange()
                self.textBox.SetStyle(r, attr)
                self.textBox.SetInsertionPoint(ip)
                self.textBox.Thaw()
                self.repositionCaret = ip
        dlg.Destroy()
    
    def OnBold(self, e):
        self.textBox.ApplyBoldToSelection()
        fr, to = self.textBox.GetSelection()
        if fr != -2:
            self.scoreBox.SetSelection(*self.textBox.GetSelection())
        self.scoreBox.ApplyBoldToSelection()
        
        self.textBox.Refresh()
        self.scoreBox.Refresh()
        # self.scoreBox.SetInsertionPoint(self.textBox.GetInsertionPoint())
        e.Skip()
    
    def OnUpdateBold(self, e):
        e.Check(self.textBox.IsSelectionBold())
        e.Check(self.scoreBox.IsSelectionBold())
    
    def OnOpen(self, e):
        self.dirName = ''
        
        dlg = wx.FileDialog(self, "Choose a file...",
            defaultDir=os.getcwd(),
            wildcard=WILDCARD,
            style=wx.OPEN|wx.FD_FILE_MUST_EXIST)
            
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if path:
                self.filePath = path
                self.dirName = dlg.GetDirectory()
                self.fileName = ntpath.basename(path)[:-4]
                self.scoreTitle = self.fileName
                self.composer = os.getlogin()
                fileType = TYPES[dlg.GetFilterIndex()]
                if fileType == rt.RICHTEXT_TYPE_RTF:
                    with open(path, "rt") as fin:
                        txt = scoreParser.getTextAndRTFBoldRegion(fin.read())[0]
                        self.textBox.SetValue(txt)
                        self.textBox.SetInsertionPointEnd()
                        self.textBox.SetStyle((0, self.textBox.GetCaretPosition() + 1), self.textAttr ) # re-color
                        self.textBox.Scroll(0, sys.maxint)
                        self.textBox.SetFocus()
                        self.textBox.SetFilename(self.filePath)
                else:
                    self.textBox.LoadFile(path, fileType)
        dlg.Destroy()        
    
    def OnSave(self, e):
        suffix = self.filePath[-3:]
        if not self.fileName: # not self.textBox.GetFilename()
            self.OnSaveAs(e)
            return
        if suffix == "rtf":
            fout = file( self.filePath, 'w' )
            fout.write(writeRTF(self.textBox, self.caretPos))
            del fout
        else:
            self.textBox.SaveFile()
    
    def OnSaveAs(self, e):
        if not self.dirName:
            savePath = os.getcwd()
        else:
            savePath = self.dirName
        if not self.fileName:
            fileName = "Untitled"
        else:
            fileName = self.fileName
        
        dlg = wx.FileDialog(self, "Save score as...",
            defaultDir=savePath,
            defaultFile=fileName,
            wildcard=WILDCARD,
            style=wx.SAVE|wx.OVERWRITE_PROMPT)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if path:
                self.dirName = dlg.GetDirectory()
                fileType = TYPES[dlg.GetFilterIndex()]
                ext = ["rtf", "txt"][dlg.GetFilterIndex()]
                if not path.endswith(ext):
                    path += "." + ext
                self.filePath = path
                
                if self.scoreTitle == self.fileName:
                    self.scoreTitle = ntpath.basename(path)[:-4]
                self.fileName = ntpath.basename(path)[:-4]
                frameTitle = "Cavatina — %s" % self.scoreTitle
                self.SetTitle(frameTitle)
                
                if fileType == rt.RICHTEXT_TYPE_RTF:
                    fout = file( path, 'w' )
                    fout.write(writeRTF(self.textBox, self.caretPos))
                    del fout
                else:
                    self.textBox.SaveFile(path, fileType)
        dlg.Destroy()
    
    def OnScoreInfo(self, e):
        scInfo = ChangeMetaDialog(None, -1,
            partNumber=self._partNumber(),
            scoreTitle=self.scoreTitle,
            scoreComposer=self.composer,
            scoreTempo=self.tempo,
            scoreInstruments=self.instruments)
        if scInfo.ShowModal() == wx.ID_OK:
            self.scoreTitle, self.composer, self.instruments, self.tempo = scInfo.getMetadata()
            frameTitle = "Cavatina — %s" % self.scoreTitle
            self.SetTitle(frameTitle)
        scInfo.Destroy()
    
    def OnExport(self, e):
        if not self.dirName:
            savePath = os.getcwd()
        else:
            savePath = self.dirName
        if not self.fileName:
            fileName = "Untitled"
        else:
            fileName = self.fileName
        
        wildcard = "MusicXML files (*.xml)|*.xml|MIDI files (*.mid)|*.mid"
        dlg = wx.FileDialog(self, "Export score",
            defaultDir=savePath,
            defaultFile=self.fileName,
            wildcard=wildcard,
            style=wx.SAVE|wx.OVERWRITE_PROMPT)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if path:
                fileName = ntpath.basename(path)
                dirName = dlg.GetDirectory()
                ext = ["xml", "mid"][dlg.GetFilterIndex()]
                if not path.endswith(ext):
                    path += "." + ext
                fmt = ["musicxml", "midi"][dlg.GetFilterIndex()]
                
                # 
                text = self.textBox.GetValue()
                rtf = writeRTF(self.textBox, self.caretPos)
                tree = scoreParser.parse(rtf)
                score = translator.translateToMusic21(tree)
                self.instruments = self.instruments[:self._partNumber()]
                translator.writeStream(score,
                    format=fmt, wrtpath=path,
                    scoreTitle=self.scoreTitle,
                    scoreComposer=self.composer,
                    scoreTempo=self.tempo,
                    scoreInstruments=self.instruments)
        dlg.Destroy()
    
    def OnToggleView(self, e):
        mb = self.GetMenuBar()
        viewMenu = wx.Menu()
        
        if not self.splitter.IsSplit(): # Show
            # self.textBox.SetFont(self.font)
            self.splitter.SplitHorizontally(self.topPanel, self.bottomPanel)
            self.splitter.SetSashPosition(self.sashPosition)
            
            menuHide = wx.MenuItem(viewMenu, ID_HIDE, "&Hide Text Panel\tCtrl+Alt+T", "Hide text panel")
            viewMenu.AppendItem(menuHide)
            self.Bind(wx.EVT_MENU, self.OnToggleView, menuHide)
            
            wx.CallAfter(self.textBox.SetFocus)
        else: # Hide
            self.sashPosition = self.splitter.GetSashPosition()
            self.splitter.Unsplit(self.topPanel)
            self.textBox.SetFocus()
            
            menuShow = wx.MenuItem(viewMenu, ID_VIEW, "&Show Text Panel\tCtrl+Alt+T", "Show text panel")
            viewMenu.AppendItem(menuShow)
            self.Bind(wx.EVT_MENU, self.OnToggleView, menuShow)
            
        mb.Replace(2, viewMenu, '&View')
        mb.UpdateMenus()
    
    def OnClick(self, e):
        if not self.splitter.IsSplit():
            self.textBox.SetFocus()
        
        self.lastCaretPos = self.caretPos
        text = self.textBox.GetValue()
        try:
            spaceIndex = len(text[:self.scoreBox.GetInsertionPoint() + 1]) \
                + re.search(r"[ /,.]", text[self.scoreBox.GetInsertionPoint() + 1:]).start(0)
        except AttributeError:
            spaceIndex = len(text)
        self.textBox.SetInsertionPoint(spaceIndex)
        
        scoreText = self.scoreBox.GetValue()
        if len(scoreText) > 0 and scoreText[0] == "\n":
            self.scoreBox.SetInsertionPoint(self.textBox.GetInsertionPoint() + 1)
        else:
            self.scoreBox.SetInsertionPoint(self.textBox.GetInsertionPoint())
        
        self.caretPos = self.textBox.GetCaretPosition()
        self.lastCaretPosClicked = self.caretPos
        
        self.textBox.Refresh()
        self._updateColors()
        self.textBox.SetFocus()
        self.lastEvent = e.GetEventType()
    
    def OnAbout(self, e):
        pass
    
    def OnPlayPause(self, e):
        caret = self.textBox.GetCaretPosition()
        if (caret >= len(self.textBox.GetValue()) - 1
        or caret <= 0
        or self.textBox.GetValue()[caret] == "\n"
        or self.textBox.GetValue()[caret + 1] == "\n"):
            self.playAll = True
            self.OnPlayAll(e)
            return
        else:
            self.playAll = False
            
        if not self.midiFile:
            # print "Loading file"
            try:
                self._loadFile()
            except scoreParser.SyntaxException:
                print "INVALID SYNTAX"
                self.midiFile = None
                # mixer.init()
                return
        
        self._doPlayPause()
        self.toolBarRight.EnableTool(ID_STOP, True)
    
    def OnPlayAll(self, e):
        if not self.midiFile:
            # print "Loading file"
            try:
                self._loadFile(playAll=True)
            except scoreParser.SyntaxException:
                print "INVALID SYNTAX"
                self.midiFile = None
                return
        
        self._doPlayPause()
        self.toolBarRight.EnableTool(ID_STOP, True)
    
    def OnTimer(self, e):
        if not mixer.music.get_busy():
            # print "End of music"
            self.OnStop(None)
    
    def OnStop(self, e):
        self.timer.Stop()
        mixer.music.stop()
        self.startTime = 0.0
        self.timeElapsed = 0.0
        
        if not self.isPaused:
            self._togglePlayPauseTool()
            self.isPaused = False
		
        self.midiFile = None
        self.toolBarRight.EnableTool(ID_STOP, False)
    
    def OnExit(self, e):
        self.timer.Stop()
        self.Close(True)
    
    # ===================
    # = Private Methods =
    # ===================
    def _setFontStyle(self, box, attr, fontColor = None, fontBgColor = None, fontFace = "", fontSize = None):
        if fontColor:
            attr.SetTextColour(fontColor)
        if fontBgColor:
            attr.SetBackgroundColour(fontBgColor)
        if fontFace:
            fontOptions = [fontFace, 'Menlo', 'Consolas', 'Courier']
        else:
            fontOptions = ['Menlo', 'Consolas', 'Courier']
        font = wx.Font(fontSize, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, 
            wx.FONTWEIGHT_NORMAL)
        for n in fontOptions:
            if font.SetFaceName(n):
                attr.SetFontFaceName(n)
                break
        if fontSize:
            attr.SetFontSize(fontSize)
        # attr.SetLineSpacing(15)
        box.SetBasicStyle(attr)
        box.SetDefaultStyle(attr)
    
    def _fontInstalled(self):
        # fe = wx.FontEnumerator()
        # flist = fe.GetFacenames()
        # for n in flist:
        #     if "Cavatina" in n:
        #         print n
        testFont = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        return testFont.SetFaceName('Cavatina Regular') # or testFont.SetFaceName('Cavatina') # boolean
    
    def _updateColors(self):
        """
        Red coloring of the charecter at the caret position.
        
        This method only colors the text at the last and current caret positions to 
        diminish window flickering on the upper textbox.
        """
        
        # The idea is to first insert the dummy characters that are
        # required for reasonable coloring (i.e. to help preserve the  
        # triggering of character alternates), and *then* apply the
        # standard coloring, instead of following a different coloring 
        # procedure for such characters. If such characters were inserted, 
        # they have to be deleted on the next text event (OnTextEnter).
        
        score = self.scoreBox.GetValue()
        caret = self.scoreBox.GetCaretPosition()
        colorStart = self.caretPos
        colorLength = 1
        colorAttr = rt.RichTextAttr()
        colorAttr.SetFlags(wx.TEXT_ATTR_TEXT_COLOUR)
        
        dontColor = False # for testing
        
        # ==================
        # = Color Text Box =
        # ==================
        
        colorAttr.SetTextColour("BLACK")
        self.textBox.SetStyle( (self.lastCaretPos, self.lastCaretPos + 1), colorAttr )
        colorAttr.SetTextColour(wx.Colour(0xF2, 0x20, 0x20, 255)) # F22020, FF7700
        self.textBox.SetStyle( (self.caretPos, self.caretPos + 1), colorAttr )
        
        # ===================
        # = Color Score Box =
        # ===================
        def insertColorString(coloredChunk, insertionPoint=None):
            """
            Inserts the temporary color string at the end of the chord 
            (or at insertionPoint if specified).
            """
            if insertionPoint is None:
                chordEnd = len(score) - 1
                for s in " ,;:/":
                    index = score.find(s, caret)
                    if index != -1:
                        chordEnd = min(index, chordEnd)
                insertionPoint = chordEnd
            
            self.scoreBox.SetInsertionPoint(insertionPoint)
            self.scoreBox.WriteText(coloredChunk) # writes before the character at the insertion point
            self.scoreBox.SetInsertionPoint(caret + 1)
            return insertionPoint
        
        # Cases for score[caret]:
        while True:
            try: # if score[caret] is suffix of a time signature
                if score[caret].isdigit():
                    tildeIndex = score.rfind("~", max(0, caret - 4), caret)
                    if tildeIndex <= 0:
                        raise ValueError
                    a = score[tildeIndex - 1]
                    if a in "-=":
                        reversedStr = score[max(0, tildeIndex - 8):tildeIndex][::-1]
                        if not re.match(r"([-=]*[_\+])", reversedStr):
                            raise ValueError
                    if a in ",;:_+":
                        if all(score[i].isdigit() for i in range(tildeIndex + 1, caret)):
                            dontColor = True
                            break
                            # color time signature
                            tsEnd = tildeIndex + self._getTimeSignatureEnd(score[tildeIndex:])
                            # ts = score[tildeIndex:tsEnd] # TODO: case after key signature
                            colorStart = tildeIndex - 1
                            colorLength = tsEnd - tildeIndex + 1
                            break
            except ValueError:
                pass
        
            try: # if score[caret] in NOTES
                if score[caret] in [INVERTER, TIMEMOD]:
                    reversedStr = score[:caret + 1][::-1] # include caret position
                    nounIndex = caret - re.search(r"([-=\"\'\[{\\|<`~]+)", reversedStr).end() # reverse re search
                    i = NOTES.index(score[nounIndex])
                    isModifier = True
                else:
                    i = NOTES.index(score[caret])
                    isModifier = False
                note = score[caret]
                noteIndex = i % 31
                
                # check if the note is a floating neighbor note
                if not isModifier:
                    chord, chordIndex, inverted = self._getChordNotes(score, caret)
                else:
                    chord, chordIndex, inverted = self._getChordNotes(score, nounIndex)
                direction = 1 if noteIndex < 13 else 0 # 1: up, 0: down
                if inverted: # TODO: not working
                    direction = 1 - direction
                
                isFloating = False
                if direction == 1:
                    consecSizeBefore = self._getConsecSize(chord, chordIndex, noteIndex, -1)
                    if consecSizeBefore > 0:
                        isFloating = (consecSizeBefore % 2 == 1)
                elif direction == 0:
                    consecSizeAfter = self._getConsecSize(chord, chordIndex, noteIndex, 1)
                    if consecSizeAfter > 0:
                        isFloating = (consecSizeAfter % 2 == 1)
                
                if isFloating: # if note is floating neighbor note
                    ghostNote = INVISIBLE_NOTES[noteIndex]
                    if direction == 1:
                        coloredChunk = ghostNote + note
                    elif direction == 0:
                        coloredChunk = note + ghostNote
                    
                    insertionIndex = insertColorString(coloredChunk)
                    colorStart = insertionIndex
                    colorLength = 2
                    self.removeColored = (colorStart, colorLength)
                    break
                
                floatingNote = FLOATING_NOTES[noteIndex]
                insertionIndex = insertColorString(floatingNote)
                colorStart = insertionIndex
                colorLength = 1
                self.removeColored = (colorStart, colorLength)
                break
            except ValueError:
                pass
            
            try: # if score[caret] in NOTE_MODIFIERS
                modIndex = NOTE_MODIFIERS.index(score[caret])
                reversedStr = score[:caret + 1][::-1]
                nounIndex = caret - re.search(r"([-=\"\'\[{\\|<`~]+)", reversedStr).end() # reverse re search
                if score[nounIndex] not in NOTES:
                    raise ValueError
                modGroupString = MODIFIER_GROUPS[modIndex / 2]
                reString = eval("r\"[" + modGroupString + "]+\"")
                start = caret - re.search(reString, reversedStr).end() + 1
                end = caret + re.search(reString, score[caret:]).end()
                modifier = score[start:end]
                self.coloredModSpan = (start, modifier) # TODO: erase the original modifier to get rid of the overlap
                
                i = NOTES.index(score[nounIndex])
                note = score[nounIndex]
                noteIndex = i % 31
                ghostNote = INVISIBLE_NOTES[noteIndex]
                coloredChunk = ghostNote + modifier
                
                insertionIndex = insertColorString(coloredChunk)
                colorStart = insertionIndex
                colorLength = len(coloredChunk)
                self.removeColored = (colorStart, colorLength)
                break
            except ValueError:
                pass
            
            if score[caret] in ",.;:": # TODO: systemic barlines
                if caret > 0 and score[caret - 1] == ",":
                    dontColor = True
                    break
                    # colorStart = caret - 1
                    # colorLength = 2
                elif caret + 1 < len(score) and score[caret + 1] == ",":
                    caret = caret + 1
                    colorStart = self.caretPos # color barline
                    colorLength = 2
                    removeColorAfter = () # this variable is needed when the colored span wont be removed with self.removeColored
                    
                ghostComma =  u"\u02FD"
                insertionIndex = insertColorString(ghostComma, caret + 1)
                # colorStart = self.caretPos; default
                self.removeColored = (insertionIndex, 1) # remove U+02FD", which is *not* colored
                break
            
            # else
            if score[caret] in " `~":
                dontColor = True
                break
            
            break
        
        colorAttr.SetTextColour("BLACK")
        self.scoreBox.SetStyle( (self.lastCaretPos, self.lastCaretPos + 1 + colorLength), colorAttr )
        if not dontColor:
            colorAttr.SetTextColour(wx.Colour(0xF2, 0x20, 0x20, 255)) # F22020, FF7700
            self.scoreBox.SetStyle( (colorStart, colorStart + colorLength), colorAttr )
    
    def _transferBold(self):
        text = self.textBox.GetValue()
        scoreText = self.scoreBox.GetValue()
        for i in range(0, len(text)):
            self.textBox.SetCaretPosition(i)
            if len(scoreText) > 0 and scoreText[0] == "\n":
                i = i+1
            self.scoreBox.SetSelection(i, i+1)
            if self.textBox.IsSelectionBold():
                if not self.scoreBox.IsSelectionBold():
                    self.scoreBox.ApplyBoldToSelection()
            else:
                if self.scoreBox.IsSelectionBold():
                    self.scoreBox.ApplyBoldToSelection()
                    
        self.textBox.SetCaretPosition(self.caretPos)
        
        if len(scoreText) > 0 and scoreText[0] == "\n":
            self.scoreBox.SetInsertionPoint(self.textBox.GetInsertionPoint() + 1)
        else:
            self.scoreBox.SetInsertionPoint(self.textBox.GetInsertionPoint())
        self.scoreBox.Refresh()
    
    def _fixGrandStaves(self, text):
        # Post-processing grand staffs
        grandStaffIndex = text.rfind(",\\\\")
        while grandStaffIndex > -1:
            newLineIndex = text[:grandStaffIndex - 1].rfind("\n")
            if newLineIndex > -1:
                text = (text[:newLineIndex]
                    + u"\n␣"
                    + text[(newLineIndex+1):grandStaffIndex]
                    + u"␣,\\\\"
                    + text[(grandStaffIndex+3):])
            else:
                text = u"␣" + text[:grandStaffIndex] + u"␣,\\\\" + text[(grandStaffIndex+3):]
                self.scoreBox.SetValue(text)
                break
            grandStaffIndex = text[:newLineIndex].rfind(",\\\\")
        return text
    
    def _fixTextOffsets(self, text, scoreText):
        """
        Correct offset clippings of the text rendering engine.
        """
        
        # The offset issues (top, bottom and interlineal) arise from the 
        # fact that the (font glyph) overshoot of extremal notes is 
        # unusually large, which was necessary to set the a normalized line 
        # separation. This happens becuase the text rendering engine seems 
        # to only refresh the currently entered line within its bounding 
        # box.
        # 
        # Top and bottom offset clipping is dealt with by adding newline 
        # characters. Setting new margins doesn't help because every offset 
        # is clipped *outside* the bounding box of the text area; the 
        # margins only control the size of the bounding box, not the 
        # distance to it.
        # 
        # Interlineal offset clipping is solved by selecting text 
        # contained inside the lines causing the issue, so we just select 
        # all text.
        
        if len(scoreText) == 0:
            return scoreText
            
        # fix bottom offsets
        if scoreText[-1] != "\n":
            self.scoreBox.AppendText("\n")
        # fix top offsets
        firstLineIndex = text.find("\n")
        firstLine = text[:firstLineIndex] if firstLineIndex > -1 else text
        #   remove time signatures strings
        lineSuffix = firstLine
        cutfirstLine = ""
        while self._getTimeSignatureEnd(lineSuffix): # equal to 0 in case there is no ts
            tsEnd = self._getTimeSignatureEnd(lineSuffix)
            cutfirstLine += lineSuffix[:tsEnd-4]
            lineSuffix = lineSuffix[tsEnd:]
        else:
            cutfirstLine += lineSuffix
        if len(cutfirstLine) > 0:
            firstLine = cutfirstLine
            
        tilde = firstLine.rfind('~')
        if (tilde != -1
        and tilde != len(firstLine) - 1
        and all(c.isdigit() for c in firstLine[tilde + 1:])):
            firstLine = firstLine[:tilde] # remove the time signature being written
        #   (end) remove time signatures strings
        anyDigits = any(c.isdigit() for c in firstLine)
        anyTall = (any(c in firstLine for c in [s + "`" for s in list("qwertyu")])
            or re.search(r"`[jqwertyuJQWERTYU]\S*[wertyu]", firstLine)
            or re.search(r"[zxcvbnmasdfghZXCVBNMASDFGH]\S*[wertyu]", firstLine))
        if (anyDigits or anyTall) and scoreText[0] != "\n":
            scoreText = "\n" + scoreText
            self.scoreBox.SetValue(scoreText)
            spacing = rt.RichTextAttr()
            spacing.SetFlags(wx.TEXT_ATTR_LINE_SPACING)
            spacing.SetLineSpacing(4)
            self.scoreBox.SetStyle((0, 1), spacing)
                
        # fix multi-line offsets
        self.scoreBox.SetFocus()
        self.scoreBox.SetSelection(-1, -1)
        self.scoreBox.SetSelection(0, 0)
        self.textBox.SetFocus()
        return scoreText
    
    def _loadFile(self, playAll=False):
        if playAll:
            text = self.textBox.GetValue()
            rtf = writeRTF(self.textBox, self.caretPos)
        else:
            centipede = self._textAfterPosition()
            rtf = writeRTFshort(centipede)
        
        self.midiFile = tempfile.NamedTemporaryFile(suffix='.mid', delete=False)
        path = self.midiFile.name
        tree = scoreParser.parse(rtf)
        score = translator.translateToMusic21(tree)
        self.instruments = self.instruments[:self._partNumber()]
        translator.writeStream(score,
            format='midi', wrtpath=path,
            scoreTitle=self.scoreTitle,
            scoreComposer=self.composer,
            scoreTempo=self.tempo,
            scoreInstruments=self.instruments)
        mixer.init()
        mixer.music.load(path)
    
    def _doPlayPause(self):
        if self.isPaused: # Unpause
            # print "Unpausing"
            self._unpause()
            self.isPaused = False
        else:
            if mixer.music.get_busy(): # Pause
                # print "Pausing"
                self._pause()
                self.isPaused = True
            else: # Play
                # print "Playing"
                self._play()
                self.isPaused = False
        self._togglePlayPauseTool()
    
    def _togglePlayPauseTool(self):
        self.toolBarRight.RemoveTool(ID_PLAY_PAUSE)
        if self.isPaused or not mixer.music.get_busy():
            self.playPause = self.toolBarRight.InsertTool(0, ID_PLAY_PAUSE,
                self.playBitmap, shortHelpString="Play", longHelpString="Play")
        else:
            self.playPause = self.toolBarRight.InsertTool(0, ID_PLAY_PAUSE,
                self.pauseBitmap, shortHelpString="Play", longHelpString="Play")
            
        self.Bind(wx.EVT_TOOL, self.OnPlayPause, self.playPause)
        self.toolBarRight.Realize()
    
    def _play(self):
        if self.midiFile:
            path = self.midiFile.name # re-load file
            mixer.music.load(path)
        mixer.music.play()
        # time.sleep(0.2)
        self.timer.Start(500)
        self.startTime = time.time()
    
    def _pause(self):
        self.timeElapsed += time.time() - self.startTime
        self.timer.Stop()
        mixer.music.stop() # pausing not supported for midi
        # time.sleep(0.2)
        
        self.midiFile = None
        self._loadMIDISuffix(self.timeElapsed)
    
    def _unpause(self):
        mixer.music.play()
        # time.sleep(0.2)
        self.timer.Start(500)
        self.startTime = time.time()
    
    def _textAfterPosition(self):
        """
        Returns the score generated after cutting from the current caret
        position (through all score parts), as well as the ordered list of
        indices of the extracted region. This method is just for playback 
        purposes, as well as all dependent methods.
        """
        text = self.textBox.GetValue()
        caret = self.textBox.GetCaretPosition()
        boldRegion = self._getBoldRegion(text, caret)
        partSwt = self._getPartSwitches(text)
        
        if len(partSwt) == 1:
            cutText = text[caret:]
            cutBold = boldRegion[caret:]
            cutCentipede = self._embedBold(cutText, cutBold)
        else:
            centipede = self._embedBold(text, boldRegion)
            sParts =  self._unzipParts(partSwt, centipede)
            p = self._getPartIndex(partSwt, caret)
            cutCentipede = self._zipParts(sParts, p)
        return cutCentipede
    
    def _getBoldRegion(self, text, curCaretPos):
        """
        Generate a list of booleans with bold information with the same 
        length as the text. This way, we can cut/extract the text and the 
        list parallelly.
        """
        boldRegion = [False] * len(text)
        self.textBox.Freeze()
        
        for i in range(len(text)):
            self.textBox.SetCaretPosition(i)
            if self.textBox.IsSelectionBold():
                boldRegion[i] = True
        
        self.textBox.SetCaretPosition(curCaretPos)
        self.textBox.Thaw()
        return boldRegion
    
    def _embedBold(self, text, boldRegion):
        centipede = zip(text, boldRegion)
        if len(centipede) != len(text):
            raise Exception
        return centipede
    
    def _getPartSwitches(self, text):
        partSwitches = [(0, 0)] # (part number, start index); end of index range is next start index
        partIndex = text.find("\n,\\")
        lastIndex = partIndex
        i = 1
        
        while partIndex > -1:
            partSwitches.append( (i, partIndex + 1) )
            
            newLineIndex = text.find("\n,", lastIndex + 1)
            newPartIndex = text.find("\n,\\", lastIndex + 1)
            
            if newPartIndex <= newLineIndex:
                partIndex = newPartIndex
                i += 1
            else:
                partIndex = newLineIndex
                i = 0
            
            lastIndex = partIndex
        
        return partSwitches
    
    def _unzipParts(self, partSwitches, centipede):
        """
        Partitions the score according to the part switches.
        - partSwitches: list of 2-tuples describing the range of each
            score part.
        - centipede: list, this is just the text and boldRegion zipped
        
        Returns:
        - parts: dict, {part number: part as centipede}
        """
        parts = {}
        partNumber = max([n for (n, i) in partSwitches]) + 1
        
        for c in range(partNumber):
            parts[c] = []
        switchIndex = 0
        
        if len(partSwitches) == 1:
            parts[0] += centipede
            return parts
        
        partNumber, a = partSwitches[switchIndex]
        nextPartNumber, b = partSwitches[switchIndex + 1]
        
        for index, s in enumerate(centipede):
            if index < b: # no need to check a <= index, becuase the indices in partSwitches are ordered
                parts[partNumber] += [s]
            else:
                switchIndex += 1
                partNumber, a = partSwitches[switchIndex]
                if switchIndex + 1 < len(partSwitches):
                    nextPartNumber, b = partSwitches[switchIndex + 1]
                else:
                    b = len(centipede) # big enough
                    # a unchanged
                parts[partNumber] += [s]
        
        return parts
    
    def _getPartIndex(self, partSwitches, pos):
        """
        Determines the part at which the caret currently is.
        
        Returns: (curPartNumber, relativeIndex)
            curPartNumber: int, the current part number
            relativeIndex: int, index of the current position within the corresponding part
        """
        switchIndex = 0
        nextPartNumber, b = partSwitches[switchIndex + 1]
        
        while pos >= b:
            switchIndex += 1
            try:
                nextPartNumber, b = partSwitches[switchIndex + 1]
            except IndexError:
                break
            
        curPartNumber, a = partSwitches[switchIndex] # partNumber is the part number that corresponds to pos
        
        # relativeIndex = 0
        # for i in range(len(partSwitches)):
        #     partNo, index = partSwitches[i]
        #     if partNo == curPartNumber and index < a:
        #         nextIndex = partSwitches[i+1][1]
        #         relativeIndex += nextIndex - index
        # relativeIndex += (pos - a)
        
        relativeIndex = sum([
            (partSwitches[i+1][1] - index) for i, (part, index) in enumerate(partSwitches) \
            if (part == curPartNumber and index < a)])
        
        relativeIndex += (pos - a)
        return (curPartNumber, relativeIndex)
    
    def _zipParts(self, separateParts, p):
        """
        Cut the part suffixes end merge them into a new score.
        (Expects that the current text position is not at the end of 
        a score part.)
        """
        curPartNo, partIndex = p
        curPartPrefix = separateParts[curPartNo][:partIndex]
        curPartPrefixString = "".join([s for (s, b) in curPartPrefix])
        
        # get signatures
        signatures = {}
        for partNumber, part in separateParts.iteritems():
            # we want to start playback from the last measure before the caret,
            # thus avoiding more complex calculations to cut multipart measures.
            partString = "".join([s for (s, b) in part]) # remember that parts are also centipedes
            i = re.search(r"[,\\]+", partString).end(0)
            j = re.search(r"[^-=,_+\\]", partString).start(0)
            k = j + self._getTimeSignatureEnd(partString[j:])
            signatures[partNumber] = (partString[i:j], partString[j:k]) # (key signature, time signature)
        
        # cut parts
        barsNo = (curPartPrefixString.count(',')
            + curPartPrefixString.count(';')
            + curPartPrefixString.count(':')) # '.' is not relevant because it's a terminal
        
        for partNumber, part in separateParts.iteritems():
            partString = "".join([s for (s, b) in part])
            cutIndex = list(re.finditer(',|;|:', partString))[barsNo - 1].start()
            if barsNo > 1: # insert formerly defined signatures
                keySignature = signatures[partNumber][0]
                timeSignature = signatures[partNumber][1]
                
                i = re.search(r"[,\\]+", partString[cutIndex:]).end(0)
                if partString[cutIndex + i] in ["_", "+"]:
                    keySignature = ""
                    
                j = re.search(r"[^-=,_+\\]", partString[cutIndex:]).start(0)
                if partString[cutIndex + j] == "~":
                    timeSignature = ""
                
                keySignature = [(s, False) for s in keySignature]
                timeSignature = [(s, False) for s in timeSignature]
                
                separateParts[partNumber] = (
                    part[cutIndex:(cutIndex + i)] +
                    keySignature +
                    timeSignature +
                    part[(cutIndex + i):])
            else:
                separateParts[partNumber] = part[cutIndex:]
        
        # remove line breaks
        for partNumber, part in separateParts.iteritems():
            partString = "".join([s for (s, b) in part])
            i = partString.find(",\\\n")
            while i > -1:
                partString = partString[:i] + partString[i+3:]
                part = part[:i+1] + part[i+3:]
                i = partString.find(",\\\n")
            i = partString.find(",\n")
            while i > -1:
                partString = partString[:i] + partString[i+2:]
                part = part[:i+1] + part[i+2:]
                i = partString.find(",\n")
            separateParts[partNumber] = part
        
        # zip
        zippedText = []
        for partNumber, part in separateParts.iteritems():
            if partNumber != len(separateParts) - 1:
                zippedText += part + [("\n", False)]
            else:
                zippedText += part
        
        # print "".join([s for s, b in zippedText])
        return zippedText
    
    def _getTimeSignatureEnd(self, target):
        """
        Returns the end-index of the first time signature in the target 
        string.
        """
        try:
            firstTS = re.search(r"(~\d\d)", target).end(0)
        except AttributeError:
            return 0
        
        end = firstTS
        for reString in [r"(~12\d)", r"(~\d16)", r"(~1216)"]:
            try:
                end = max(re.match(reString, target[firstTS-3:]).end(0) + firstTS - 3, end)
            except AttributeError:
                continue
        return end
    
    def _getChordNotes(self, score, caret):
        """
        Assumes the *caret* is pointing at a note in *score*. Returns the 
        chord of that note, its index inside the *chord* list, and an 
        inversion boolean.
        """
        chords = []
        chordStart = max(score.rfind(" ", 0, caret), score.rfind(",", 0, caret))
        tsOffset = self._getTimeSignatureEnd(score[chordStart:])
        if chordStart + tsOffset <= caret:
            chordStart += max(0, tsOffset - 1)
        i = chordStart + 1
        inverted = False
        while i < len(score) and score[i] not in " ,.;:":
            if len(chords) == 1 and score[i] == INVERTER:
                inverted = True
            if score[i] in NOTES:
                if i == caret:
                    chordIndex = len(chords)
                chords.append(score[i])
            i += 1
        return (chords, chordIndex, inverted)
    
    def _getConsecSize(self, chord, chordIndex, noteIndex, d):
        """
        Returns the size of the biggest successive sequence before/after 
        chord[chordIndex] without including it.
        
        - d: the direction in which the sequence is checked,
            1: up, -1: down
        """
        consecutiveSeqSize = 0
        if (chordIndex == 0 and d == -1) or (chordIndex == len(chord) - 1 and d == 1):
            return consecutiveSeqSize
        c = chord[:chordIndex] if d == -1 else chord[chordIndex:]
        i = noteIndex
        j = d
        n = c[j] 
        while NOTES.index(n) % 31 == i + d: # while consecutive
            consecutiveSeqSize += 1
            # traversing in d direction
            i = i + d
            j = j + d
            if j < -chordIndex or j >= len(chord) - chordIndex:
                return consecutiveSeqSize
            n = c[j]
        return consecutiveSeqSize
    
    def _partNumber(self):
        text = self.textBox.GetValue()
        return max([n for (n, i) in self._getPartSwitches(text)]) + 1
    
    def _loadMIDISuffix(self, timeElapsed):
        """
        Method written for pause/unpause functionality
        """
        if self.playAll:
            text = self.textBox.GetValue()
            rtf = writeRTF(self.textBox, self.caretPos)
        else:
            centipede = self._textAfterPosition()
            rtf = writeRTFshort(centipede)
            
        score = self._getOffsetScore(round(timeElapsed, 2), rtf) # rounding superfluous?
        self.midiFile = tempfile.NamedTemporaryFile(suffix='.mid', delete=False)
        path = self.midiFile.name
        self.instruments = self.instruments[:self._partNumber()]
        translator.writeStream(score,
            format='midi', wrtpath=path,
            scoreTempo=self.tempo,
            scoreInstruments=self.instruments)
        mixer.music.load(path)
    
    def _getOffsetScore(self, timeElapsed, text):
        tree = scoreParser.parse(text)
        m21stream = translator.translateToMusic21(tree)
        try:
            m21stream = m21stream.expandRepeats()
        except:
            pass
        quartersPerSecond = float(self.tempo) / 60
        currentOffset = quartersPerSecond * timeElapsed
        streamDuration = m21stream.duration.quarterLength
        
        if len(m21stream.parts) == 1:
            m21stream[-1] = m21stream[-1].getElementsByOffset(
                currentOffset, offsetEnd=streamDuration, mustBeginInSpan=False)
            if len(m21stream[-1]) == 0:
                self.OnStop(None)
                return
            for i in range(len(m21stream[-1])):
                if isinstance(m21stream[-1][i], stream.Measure):
                    break
            firstMeasure = m21stream[-1][i]
            measureDuration = firstMeasure.duration.quarterLength
            relMeasureOffset = currentOffset - firstMeasure.offset
            m21stream[-1][i] = firstMeasure.getElementsByOffset(
                relMeasureOffset, offsetEnd=measureDuration, mustBeginInSpan=False)
            lowestMeasureOffset = m21stream[-1][i].lowestOffset
        else:
            lowestMeasureOffset = 100.0 # arbitrary number, large enough
            for p in range(len(m21stream.parts)):
                m21stream[-(p+2)] = m21stream[-(p+2)].getElementsByOffset(
                    currentOffset, offsetEnd=streamDuration, mustBeginInSpan=False)
                if len(m21stream[-(p+2)]) == 0:
                    break
                for i in range(len(m21stream[-(p+2)])):
                    if isinstance(m21stream[-(p+2)][i], stream.Measure):
                        break
                firstMeasure = m21stream[-(p+2)][i]
                measureDuration = firstMeasure.duration.quarterLength
                relMeasureOffset = currentOffset - firstMeasure.offset
                m21stream[-(p+2)][i] = firstMeasure.getElementsByOffset(
                    relMeasureOffset, offsetEnd=measureDuration, mustBeginInSpan=False)
                lowestMeasureOffset = min(lowestMeasureOffset, m21stream[-(p+2)][i].lowestOffset)
                
        
        lowestOffset = streamDuration # large enough for calculation of min
        for p in m21stream.parts:
            lowestOffset = min(lowestOffset, p.lowestOffset)
        
        for e in m21stream.recurse():
            if isinstance(e, stream.Measure):
                e.offset = e.offset - lowestOffset
                for n in e:
                    try: # ask for forgiveness
                        n.offset = n.offset - lowestMeasureOffset
                    except: # not for permission
                        pass
        return m21stream
    



class ChangeMetaDialog(wx.Dialog):
    def __init__(self, parent, id, partNumber, scoreTitle, scoreComposer, scoreTempo, scoreInstruments):
        self.partNumber = partNumber
        self.lastSliderValue = scoreTempo
        super(ChangeMetaDialog, self).__init__(parent, id)
        self.InitUI(partNumber, scoreTitle, scoreComposer, scoreTempo, scoreInstruments)
        self.SetSize((350, 300))
        self.SetTitle("Score Info")
        wx.CallAfter(self.titleEntry.SetFocus) 
        
    def InitUI(self, partNumber, scoreTitle, scoreComposer, scoreTempo, scoreInstruments):
        # Panel
        panel = wx.Panel(self, style=wx.TAB_TRAVERSAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        fgs = wx.FlexGridSizer(5, 2, 6, 12)
        
        title = wx.StaticText(panel, label="Title")
        composer = wx.StaticText(panel, label="Composer")
        if partNumber == 1:
            instrument = wx.StaticText(panel, label="Instrument")
        else:
            instrument = wx.StaticText(panel, label="Instruments")
        tempo = wx.StaticText(panel, label="Tempo")
        review = wx.StaticText(panel, label="Comments")
        
        self.titleEntry = wx.TextCtrl(panel, value=scoreTitle)
        self.composerEntry = wx.TextCtrl(panel, value=scoreComposer)
        
        if partNumber == 1:
            instrumentEntry = wx.TextCtrl(panel)
            instrumentEntry.SetValue(scoreInstruments[0])
            self.instrumentEntry = instrumentEntry
        else:
            instrumentsSizer = wx.FlexGridSizer(rows=partNumber, cols=2, hgap=6, vgap=6)
            self.instrumentEntries = []
            for n in range(partNumber):
                label = wx.StaticText(panel, label="Part " + str(n + 1))
                try:
                    i = scoreInstruments[n]
                except IndexError:
                    i = "Piano"
                textEntry = wx.TextCtrl(panel)
                textEntry.SetValue(i)
                instrumentsSizer.Add(label, flag=wx.EXPAND|wx.TOP, border=1)
                instrumentsSizer.Add(textEntry,  proportion=1, flag=wx.EXPAND)
                self.instrumentEntries.append(textEntry)
            instrumentsSizer.AddGrowableCol(1, 1)
            self.instrumentEntry = instrumentsSizer
        
        tempoHBox = wx.BoxSizer(wx.HORIZONTAL)
        tempoVBox =  wx.BoxSizer(wx.VERTICAL)
        self.tempoSlider = wx.Slider(panel, -1, scoreTempo, 16, 208, wx.DefaultPosition, size=(-1, -1))
        self.tempoEntry = wx.TextCtrl(panel, value=str(scoreTempo), size=(36, -1))
        self.tempoString = wx.StaticText(panel, label=self._getTempoString(scoreTempo))
        tempoHBox.Add(self.tempoEntry, 0, wx.EXPAND|wx.ALIGN_RIGHT)
        tempoHBox.Add((10, -1))
        tempoHBox.Add(self.tempoString, 0, wx.TOP|wx.EXPAND|wx.ALIGN_CENTER, border=2)
        tempoVBox.Add(self.tempoSlider, 0, wx.EXPAND|wx.ALIGN_CENTER)
        tempoVBox.Add(tempoHBox, wx.EXPAND)
        
        self.commentEntry = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        
        fgs.AddMany([(title, 0, wx.ALIGN_RIGHT), (self.titleEntry, 1, wx.EXPAND),
            (composer, 0, wx.ALIGN_RIGHT), (self.composerEntry, 1, wx.EXPAND),
            (instrument, 0, wx.ALIGN_RIGHT), (self.instrumentEntry, 1, wx.EXPAND),
            (tempo, 0, wx.ALIGN_RIGHT), (tempoVBox, 1, wx.EXPAND),
            (review, 0, wx.ALIGN_RIGHT), (self.commentEntry, 1, wx.EXPAND)])
        fgs.AddGrowableCol(1, 1)
        fgs.AddGrowableRow(4, 1)
        
        hbox.Add(fgs, proportion=1, flag=wx.ALL|wx.EXPAND, border=15)
        panel.SetSizer(hbox)
        
        # Button sizer
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, id=wx.ID_OK)
        closeButton = wx.Button(self, id=wx.ID_CANCEL)
        hbox2.Add(okButton)
        hbox2.Add(closeButton, flag=wx.LEFT, border=5)
        
        # Main vertical sizer
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(panel, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)
        vbox.Add(hbox2, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
        self.SetSizer(vbox)
        
        # Event bindings
        self.titleEntry.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        self.composerEntry.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        if partNumber == 1:
            self.instrumentEntry.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        else:
            for e in self.instrumentEntries:
                e.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        self.tempoSlider.Bind(wx.EVT_SCROLL, self.OnSliderScroll)
        self.tempoEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
    
    def OnFocus(self, e):
        textCtrl = e.GetEventObject()
        textCtrl.SetSelection(-1, -1)
    
    def OnKillFocus(self, e):
        try:
            v = int(self.tempoEntry.GetValue())
        except ValueError:
            self.tempoEntry.SetValue(str(self.lastSliderValue))
            return
        if self.tempoSlider.GetValue() == v:
            return
        if self.tempoSlider.GetMin() <= v <= self.tempoSlider.GetMax():
            self.tempoSlider.SetValue(v)
            self.lastSliderValue = v
        else:
            self.tempoSlider.SetValue(self.lastSliderValue)
            self.tempoEntry.SetValue(str(self.lastSliderValue))
    
    def OnSliderScroll(self, e):
        obj = e.GetEventObject()
        tempo = obj.GetValue()
        self.lastSliderValue = tempo
        self.tempoEntry.SetLabel(str(tempo))
        self.tempoString.SetLabel(self._getTempoString(tempo))
    
    def _getTempoString(self, tempo):
        """
        tempo: int; ranges from 16 to 208
        """
        d = {
            16 : "Larghissimo",
            20 : "Grave",
            40 : "Largo",
            60 : "Larghetto",
            66 : "Adagio",
            76 : "Andante",
            108 : "Moderato",
            120 : "Allegro",
            152 : "Vivace",
            168 : "Presto",
            200 : "Prestissimo",
            256 : None,
        }
        
        for k in sorted(d.iterkeys()):
            if tempo < k:
                break
            lastKey = k
        tempoString = d[lastKey]
        return tempoString
    
    def getMetadata(self):
        if self.partNumber == 1:
            instruments = [self.instrumentEntry.GetValue()]
        else:
            instruments = [e.GetValue() for e in self.instrumentEntries]
        
        return [self.titleEntry.GetValue(),
            self.composerEntry.GetValue(),
            instruments,
            self.tempoSlider.GetValue()]
    


def main():
    app = wx.App() # redirect=False
    
    frame = MainFrame(None)
    frame.Show(True)
    frame.SetMinSize((450, 350))
    
    app.MainLoop()    

if __name__ == '__main__':
    main()
