#
# Copyright 2015, Michael Caverley
#

import wx
from hp816x_Oband_N77Det_instr import hp816x_Oband_N77Det
import laserPanel

class hp816x_Oband_N77Det_instrParameters(wx.Panel):
    name='Laser: hp816x - Oband with N77 Detector'
    def __init__(self, parent, connectPanel, **kwargs):
        super(hp816x_Oband_N77Det_instrParameters, self).__init__(parent)
        self.connectPanel = connectPanel
        self.visaAddrLst = kwargs['visaAddrLst']
        self.InitUI()


    def InitUI(self):
        sb = wx.StaticBox(self, label='Agilent 816x With N77 Detector Parameters');
        vbox = wx.StaticBoxSizer(sb, wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.para1 = wx.BoxSizer(wx.HORIZONTAL)
        self.para1name = wx.StaticText(self,label='Mainframe Address')
        self.para1tc = wx.ComboBox(self, choices=self.visaAddrLst)
        #self.para1tc = wx.TextCtrl(self,value='GPIB0::20::INSTR')
        self.para1.AddMany([(self.para1name,1,wx.EXPAND),(self.para1tc,1,wx.EXPAND)])

        self.para2 = wx.BoxSizer(wx.HORIZONTAL)
        self.para2name = wx.StaticText(self,label='Detector Address')
        self.visaAddrLst = self.visaAddrLst + ('TCPIP0::100.65.11.185::inst0::INSTR',) ##EDITED on 17.11
        self.para2tc = wx.ComboBox(self, choices=self.visaAddrLst)
        #self.para2tc = wx.TextCtrl(self,value='TCPIP0::100.65.11.185::inst0::INSTR')
        self.para2.AddMany([(self.para2name,1,wx.EXPAND),(self.para2tc,1,wx.EXPAND)])

        self.disconnectBtn = wx.Button(self, label='Disconnect')
        self.disconnectBtn.Bind( wx.EVT_BUTTON, self.disconnect)
        self.disconnectBtn.Disable()

        self.connectBtn = wx.Button(self, label='Connect')
        self.connectBtn.Bind( wx.EVT_BUTTON, self.connect)

        hbox.AddMany([(self.disconnectBtn, 0), (self.connectBtn, 0)])

        vbox.AddMany([(self.para1,0,wx.EXPAND), (self.para2,0,wx.EXPAND), (hbox, 0)])



        self.SetSizer(vbox)


    def connect(self, event):
        self.laser = hp816x_Oband_N77Det();
        self.laser.connect(self.para1tc.GetValue(), self.para2tc.GetValue(), reset=0, forceTrans=1)
        self.laser.panelClass = laserPanel.laserTopPanel # Give the laser its panel class
        self.connectPanel.instList.append(self.laser)
        self.disconnectBtn.Enable()
        self.connectBtn.Disable()

    def disconnect(self, event):
        self.laser.disconnect()
        if self.laser in self.connectPanel.instList:
            self.connectPanel.instList.remove(self.laser)
        self.disconnectBtn.Disable()
        self.connectBtn.Enable()

