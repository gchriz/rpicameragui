#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Explore the Raspberry Pi Camera in a GUI
# The cmd line instruction used to generate the photo is shown below the photo
# Originally by Bill Grainger June 2013 updated Sept 2013
# 
# Bill wrote:
# > I learnt a lot about python to create this from 
# > various articles on stackoverflow forum
# > and image_viewer2.py by created on 03-20-2010 by Mike Driscoll

# Refactored and enhanced by Christian Ziemski, 26.07.2014

# Helpful links:
#
#   Discussion: 
#       "Graphical interface for raspistill" 
#           http://www.raspberrypi.org/forums/viewtopic.php?t=47857
#   Original repository: 
#       https://github.com/sixbacon/RPICameraGUI
#   wxPython:
#       http://www.blog.pythonlibrary.org/2009/08/25/wxpython-using-wx-timers/

import os
import wx
import subprocess  # needed to run external program raspistill 
import time
from wx.lib.pubsub import Publisher


########################################################################
class App(wx.PySimpleApp):
    """ Class to make it work with PyCrust """

    def OnInit(self):
        self.frame = ViewerFrame()

        return True
    
########################################################################
class ViewerPanel(wx.Panel):
    """ create the main screen """
    
    #----------------------------------------------------------------------
    def __init__(self, parent):
        """ set up for playing with images """
        wx.Panel.__init__(self, parent)
        
        width, height = wx.DisplaySize()
       
        self.photoMaxSize = height - 200
        self.img = wx.EmptyImage(self.photoMaxSize,self.photoMaxSize)

        self.cam_options = [
             # option name  initially set?  parameter syntax    short description               default value       range/choices (note the data types!)
             #-----------------------------------------------------------------------------------------------------------------------------------------
            {"name": 'w',   "set": False, "param": '%s',   "descr": 'width in pixels',         "default":    1920, "range": (20, 5000)},
            {"name": 'h',   "set": False, "param": '%s',   "descr": 'height in pixels',        "default":    1080, "range": (20, 5000)},
            {"name": 'o',   "set": True,  "param": '"%s"', "descr": 'filename for picture',    "default": "image.jpg", "range": ""},
            {"name": 'q',   "set": False, "param": '%s',   "descr": 'quality of jpg  0..100',  "default":      75, "range": (0, 100)},
            {"name": 't',   "set": True,  "param": '%s',   "descr": 'time delay (ms) before',  "default":     100, "range": (100, 100000000)},
            {"name": 'sh',  "set": False, "param": '%s',   "descr": 'sharpness    -100..100',  "default":       0, "range": (-100, 100)},
            {"name": 'co',  "set": False, "param": '%s',   "descr": 'contrast     -100..100',  "default":       0, "range": (-100, 100)},
            {"name": 'br',  "set": False, "param": '%s',   "descr": 'brightness      0..100',  "default":       0, "range": (0, 100)},
            {"name": 'sa',  "set": False, "param": '%s',   "descr": 'saturation   -100..100',  "default":       0, "range": (-100, 100)},
            {"name": 'rot', "set": False, "param": '%s',   "descr": 'rotate image',            "default":       0, "range": ['0','90','180','270']},
            {"name": 'ex',  "set": False, "param": '%s',   "descr": 'exposure mode',           "default": "auto",  "range": ['off','auto','night','nightpreview','backlight', 'spotlight','sports','snow','beach','verylong','fixedfps','antishake','fireworks']},
            {"name": 'ev',  "set": False, "param": '%s',   "descr": 'exposure compensation -10..10', "default": 0, "range": (-10, 10)},
            {"name": 'awb', "set": False, "param": '%s',   "descr": 'automatic white balance', "default": "auto",  "range": ['off','auto','sun','cloudshade','tungsten','fluorescent','incandescent','flash','horizon']},
            {"name": 'ifx', "set": False, "param": '%s',   "descr": 'image effect',            "default": "none",  "range": ['none','negative','solarise','whiteboard','blackboard','sketch','denoise','emboss','oilpaint','hatch','gpen','pastel','watercolour','film','blur']},
        ]

        # dictionaries to store the later created controls 
        self.checkboxes = {}
        self.inputs = {}

        # set up for communication between instances of differnet classes
        Publisher().subscribe(self.updateImages, ("update images"))

        # timer for testing. Need to be continued...
        self.timer = wx.Timer(self, wx.ID_ANY)
        self.Bind(wx.EVT_TIMER, self.timerUpdate, self.timer)
        self.timer2 = wx.Timer(self, wx.ID_ANY)
        self.Bind(wx.EVT_TIMER, self.timerUpdate, self.timer2)

        self.remaining = 0

        self.layout()

    #----------------------------------------------------------------------
    def layout(self):
        """ layout the widgets on the panel """

        self.bigsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.imageCtrl = wx.StaticBitmap(self, wx.ID_ANY, wx.BitmapFromImage(self.img))
        self.mainSizer.Add(self.imageCtrl, 0, wx.ALL|wx.CENTER, 5)
        self.imageLabel = wx.StaticText(self, label="")
        self.mainSizer.Add(self.imageLabel, 1, wx.ALL, 5)
        
        btnData = [("Rot Clock 90°", btnSizer, self.onRotClock),
                   ("Rot Anti-clock 90°", btnSizer, self.onRotAclock)]
        for data in btnData:
            label, sizer, handler = data
            self.btnBuilder(label, sizer, handler)
            
        self.mainSizer.Add(btnSizer, 1, wx.CENTER)
        self.CS=wx.Panel(self,0, size=(100,500))
        self.fillCS()
        self.bigsizer.Add(self.CS, 0, wx.ALL,5)
        self.bigsizer.Add(self.mainSizer, 1, wx.ALL,5)
        self.SetSizer(self.bigsizer)
            
    #----------------------------------------------------------------------
    def btnBuilder(self, label, sizer, handler):
        """ build a button, binds it to an event handler and adds it to a sizer """

        btn = wx.Button(self, label=label)
        btn.Bind(wx.EVT_BUTTON, handler)
        sizer.Add(btn, 0, wx.ALL|wx.CENTER, 5)
        
    #----------------------------------------------------------------------
    def fillCS(self):
        """ draw window to collect all the options for the next image """

        #todo: do positioning with sizers and not hardcoded!
        
        # screen layout
        xbase= 2
        xbtnbase = 30
        xspinbase = 60
        xcombase=190
        ybase = 50
        ydistance = 30

        yoffset = 0

        # Just a title for the options
        wx.StaticText(self.CS, -1, 'DETAILS', (xcombase,15))

        # option list
        for opt in self.cam_options:
            oname = opt["name"]
            orange = opt["range"]
            odefault = opt["default"]
            
            # create checkboxes and check/uncheck as defined above
            self.checkboxes[oname] = wx.CheckBox(self.CS, -1, '-%s  ' % oname, (xbase, ybase + yoffset))
            self.checkboxes[oname].SetValue(opt["set"])

            # allow changes some with restricted ranges or restricted choices

            # string = default value  ==>  TextCtrl
            if isinstance(orange, str):
                self.inputs[oname] = wx.TextCtrl(self.CS, pos=(xbase+xspinbase,ybase+yoffset),size=(120, -1),value=odefault)

            # tuple = range  ==>  SpinCtrl
            elif isinstance(orange, tuple):
                self.inputs[oname] = wx.SpinCtrl(self.CS, -1, str(odefault), (xbase+xspinbase, ybase+yoffset), (60, -1), min=orange[0], max=orange[1])

            # list = choices  ==>  Combobox
            elif isinstance(orange, list):
                self.inputs[oname] = wx.ComboBox(self.CS, -1, str(odefault), pos=(xbase+xspinbase, ybase+yoffset), size=(90, -1), choices=orange, style=wx.CB_READONLY)

            # add brief explanations of settings
            wx.StaticText(self.CS, -1, opt["descr"] , (xcombase,ybase+yoffset))

            yoffset += ydistance

        
        self.shootBtn = wx.Button(self.CS, 1, 'Take Photo', (xbtnbase, ybase+yoffset))
        
        self.loopBtn = wx.Button(self.CS, 2, 'Start timer ...', (xbtnbase + 110, ybase+yoffset))
        self.loopBtn.Bind(wx.EVT_BUTTON, self.onStartStopTimer)

        self.scloop = wx.SpinCtrl(self.CS, 1, str(0), (xbtnbase + 210, ybase+yoffset), (40, -1), min=0, max=30)
        wx.EVT_SPINCTRL(self, 1, self.onChangeSpin) 

        wx.StaticText(self.CS, -1,'loop \nin seconds' , (xbtnbase + 260, ybase+yoffset))

        # when happy take a new picture
        self.Bind(wx.EVT_BUTTON, self.TakePic, id=1)
        
        

    #----------------------------------------------------------------------
    def TakePic(self, event):
        # pick up all the settings selected and add to command line to be used to take a picture

        print "takePic called..."

        self.cmdln='raspistill '

        for opt in self.cam_options:
            oname = opt["name"]
            if self.checkboxes[oname].GetValue():
                value = str(self.inputs[oname].GetValue())
                if value != "":
                    self.cmdln += ' -%s ' % (oname) + opt["param"] % (value)

        #defaultfilename = str(self.picname.GetValue())
        self.imageLabel.SetLabel(self.cmdln)
    
        # call external program to take a picture
        subprocess.check_call([self.cmdln], shell=True)

        # update image on screen
        Publisher().sendMessage("update images","")

       
    #----------------------------------------------------------------------
    def loadImage(self, image):
        """"""
        self.img = wx.Image(image, wx.BITMAP_TYPE_ANY)
        self.rescaleImage()

    #----------------------------------------------------------------------
    def rescaleImage(self):
        """ scale the image to fit frame, preserving the aspect ratio """

        W = self.img.GetWidth()
        H = self.img.GetHeight()

        if W > H:
            NewW = self.photoMaxSize
            NewH = self.photoMaxSize * H / W
        else:
            NewH = self.photoMaxSize
            NewW = self.photoMaxSize * W / H

        self.img = self.img.Scale(NewW,NewH)

        self.imageCtrl.SetBitmap(wx.BitmapFromImage(self.img))
        self.Refresh()
        Publisher().sendMessage("resize", "")
                
    #----------------------------------------------------------------------
    def rotatePicture(self, clockwise=True):
        """ rotate the current picture clockwise/anticlockwise but only does it once
            as it does not store the rotated image
        """
       
        self.img = self.img.Rotate90(clockwise)
        
        # may need to scale the image, preserving the aspect ratio
        self.rescaleImage()

    #----------------------------------------------------------------------
    
    def updateImages(self,msg):
        """"""
        #pass
        self.loadImage(str(self.inputs["o"].GetValue()))
              
    #----------------------------------------------------------------------
    def onRotClock(self, event):
        """ rotate image clockwise, note it works on the image not the camera """

        self.rotatePicture(clockwise = True)

    #----------------------------------------------------------------------
    def onRotAclock(self, event):
        """ rotate image anti-clockwise """

        self.rotatePicture(clockwise = False)

    #----------------------------------------------------------------------
    def onChangeSpin(self, event):
        #if event.GetEventObject() == self.scloop:
            secs = self.scloop.GetValue()

            if self.timer.IsRunning():
                self.timer.Stop()
                self.timer2.Stop()
                self.loopBtn.SetLabel("Start Timer ...")
                print "timer stopped!"
                print "starting timer ..."
                self.remaining = secs
                self.timer.Start(secs*1000)
                self.timer2.Start(1000)
                self.loopBtn.SetLabel("Delay: %d" % (self.remaining))

    #----------------------------------------------------------------------
    def startTimers(self):
        secs = self.scloop.GetValue()
        print "starting timer ..." #% timerNum
        self.remaining = secs
        self.timer.Start(secs*1000)
        self.timer2.Start(1000)
        self.loopBtn.SetLabel("Delay: %d" % (self.remaining))

    #----------------------------------------------------------------------
    def stopTimers(self):
        self.timer.Stop()
        self.timer2.Stop()
        self.loopBtn.SetLabel("Start Timer ...")
        print "timer stopped!" #% timerNum

    #----------------------------------------------------------------------
    def onStartStopTimer(self, event):
        #btn = event.GetEventObject()

        secs = self.scloop.GetValue()
        if secs == 0:
            return

        if self.timer.IsRunning():
            self.stopTimers()
        else:
            self.startTimers()
        
    #----------------------------------------------------------------------
    def timerUpdate(self, event):
        secs = self.scloop.GetValue()
        timerId = event.GetId()

        self.loopBtn.SetLabel("Delay: %d" % (self.remaining))
        
        if timerId == self.timer.GetId():  # the loop timer fired
            self.remaining = secs
            print "\ntimer fired: CLICK", 
            # taking a picture may be slooow. So better delay the timers...
            self.stopTimers()
            self.TakePic(event)
            self.startTimers()
            
        else:  # the one-second timer
            self.remaining -= 1


        print time.ctime()


########################################################################
class ViewerFrame(wx.Frame):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        wx.Frame.__init__(self, None, title="Raspberry Pi Camera Simple GUI")
        panel = ViewerPanel(self)
        
        Publisher().subscribe(self.resizeFrame, ("resize"))
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
        
        self.Show()
        self.sizer.Fit(self)
        self.Center()     


    #----------------------------------------------------------------------
    def resizeFrame(self, msg):
        """"""
        self.sizer.Fit(self)
        
#----------------------------------------------------------------------
if __name__ == "__main__":
    app = App()
    app.MainLoop()
