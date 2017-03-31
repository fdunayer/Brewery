#!/usr/bin/python3

'''
AutoBrew

by

Fred Dunayer

This is the main module of the brewing system

Start on Test Tab where you tell it if you're running on a live pi,
test pi or test pc system
'''

import sys
# import Queue as queue
# import threading


import time, glob, os, platform, csv

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QThread, QBasicTimer, QTime, QDateTime
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QGridLayout, QLabel, QLineEdit, QMainWindow
from PyQt5.QtWidgets import QTextEdit, QWidget, QDialog, QApplication

from twilio.rest import TwilioRestClient

#accountSID = 'ACe6ba2ebf969770296498f6ae5a12b3ce'
#authToken = 'c67b52a7631ac3d7fd5ae98dc1ca2339'
#twilioCli = TwilioRestClient(accountSID, authToken)
#myTwilioNumber = '+9412020403'
#myCellPhone = '+19415499312'

# from Start_Windows_GUI import Ui_StartupWindow
from AutoBrew_MainPage_V1 import Ui_AutoBrew
runningsystem = platform.system()


# GPIO Basic Setup
if runningsystem != "Windows":
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # GPIO Setup for Inputs (Float Switches)
    
    GPIO.setup(19, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Mash Tun Float Switch
    GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP) #HLT Float Switch
    
    Mash_Float_GPIO = 19
    HLT_Float_GPIO = 26
    input_state_Mash = GPIO.input(Mash_Float_GPIO)
    #print("Mash Input State:", input_state_Mash)
    input_state_HLT = GPIO.input(HLT_Float_GPIO)
    #print("HLT Input State:", input_state_HLT)
    
    # GPIO Setup for Outputs
    
    GPIO.setup(22, GPIO.OUT) # Pump Primary
    GPIO.setup(27, GPIO.OUT) # Pump LED
    GPIO.setup(5, GPIO.OUT)  # HLT Primary
    GPIO.setup(6, GPIO.OUT)  # HLT LED

    # Temp Probe Setup
    
    base_dir = '/sys/bus/w1/devices/'
    
    device_folder_Mash = glob.glob(base_dir + '28-0315162490ff')
    device_folder_HLT = glob.glob(base_dir + '28-0315161a6dff')

    device_file_Mash = (base_dir + "28-0315162490ff/w1_slave")
    device_file_HLT = (base_dir + "28-0315161a6dff/w1_slave")

Pump_Primary_GPIO = 22
Pump_Secondary_GPIO = 27
HLT_Primary_GPIO = 5
HLT_Secondary_GPIO = 6

timeformat = "hh:mm:ss"
clockformat = "hh:mm:ss AP"

class AutoBrew(QMainWindow, Ui_AutoBrew, QWidget):
    
    def __init__(self):
        super(AutoBrew, self).__init__()    
        self.setupUi(self)
        # self.showFullScreen() # Only activate when running from touchscreen
        self.spaces = "                                                                          "               
        self.logboxtimes = []
        self.logboxtexts = []
        self.logboxbrewtimes = []
        self.calcclocktimedifference = 0
        self.lastsecond = 0
        
        self.Log_Write("Program Initiated - Running on " + runningsystem)
        # Make some local modifications.
    
        self.systemActive = "TestPC"  # initial until something chosen
        self.HLTOff.setStyleSheet("background-color: red")
        self.HLTOn.setStyleSheet("background-color: white")
        self.PumpOff.setStyleSheet("background-color: red")
        self.PumpOn.setStyleSheet("background-color: white")
        self.Go.setStyleSheet("background-color: white")
        self.CurrentMashTempDisplay.setText("0")
        self.CurrentHLTTempDisplay.setText("0")
     
        self.Pump = "Off"
        self.HLT = "Off"
        self.Log_Write("Pump is off")
        self.go_button_indicator = 0
        i = 0
        self.Change_Flag = 1
        self.autobrew = False
        self.autobrewstatus = "Not started"
        
        # Twilio - used to send text message when autobrew completes
        
        self.accountSID = self.TwilioSID.displayText()
        self.authToken = self.TwilioAuthToken.displayText()
        self.twilioCli = TwilioRestClient(self.accountSID, self.authToken)
        self.myTwilioNumber = self.TwilioPhone.displayText()
        self.myCellPhone = self.TwilioSendTo.displayText()
        
        self.MashSetChartPoint = []
        self.MashChartPoint = []
        self.HLTSetChartPoint = []
        self.HLTChartPoint = []
        self.ChartTime = []

              
        if self.systemActive[0:4] == "Live":
            self.MashTemp = self.read_temp_Mash()
            self.HLTTemp = self.read_temp_HLT()
      
        else:
            self.MashFloatSwitch = 0
            self.HLTFloatSwitch = 0
            self.MashTemp = 90 # Dummy for testing
            self.HLTTemp = 100 # Dummy for testing              

        self.Update_Displays()
        
        # Connect up the buttons.
        
        self.LivePiButton.clicked.connect(self.Live_Pi_Button_Pressed)
        self.TestPiButton.clicked.connect(self.Test_Pi_Button_Pressed)
        self.TestPCButton.clicked.connect(self.Test_PC_Button_Pressed)
        self.LivePCButton.clicked.connect(self.Live_PC_Button_Pressed)
        
        self.Rest1Button.clicked.connect(self.RecipeButton_Pressed)
        self.Rest2Button.clicked.connect(self.RecipeButton_Pressed)
        self.Rest3Button.clicked.connect(self.RecipeButton_Pressed)
        self.Rest4Button.clicked.connect(self.RecipeButton_Pressed)
        self.Rest5Button.clicked.connect(self.RecipeButton_Pressed)
        self.Rest6Button.clicked.connect(self.RecipeButton_Pressed)
        self.Rest7Button.clicked.connect(self.RecipeButton_Pressed)
        self.Rest8Button.clicked.connect(self.RecipeButton_Pressed)
        
        self.PumpOn.clicked.connect(self.Pump_On_Button_Pressed)
        self.PumpOff.clicked.connect(self.Pump_Off_Button_Pressed)
        self.HLTOn.clicked.connect(self.HLT_On_Button_Pressed)
        self.HLTOff.clicked.connect(self.HLT_Off_Button_Pressed)
        self.RespectMashTempSet.stateChanged.connect(self.Change_Flag_Set)
        self.RespectMashFloatSwitchPump.stateChanged.connect(self.Change_Flag_Set)
        self.RespectHLTFloatSwitchPump.stateChanged.connect(self.Change_Flag_Set)
        self.RespectHLTTempSet.stateChanged.connect(self.Change_Flag_Set)
        self.RespectHLTFloatSwitchHLT.stateChanged.connect(self.Change_Flag_Set)
        self.MashTempSet.valueChanged.connect(self.Change_Flag_Set)
        self.HLTTempSet.valueChanged.connect(self.Change_Flag_Set)
        self.Go.clicked.connect(self.Go_Button_Clicked)
        self.ReturntoSessionButton.clicked.connect(self.Leave_Manual_Control_Mode)
        self.StartButton.clicked.connect(self.Start_Button_Pressed)
        self.BrewButton.clicked.connect(self.calc_brew)
        self.GenerateRecipeButton.clicked.connect(self.Build_Recipe_Page)
        self.ExportLogButton.clicked.connect(self.Export_Log)
        self.ExportChartButton.clicked.connect(self.Export_Chart)
        self.ExitButtonAutoBrew.clicked.connect(self.End_Of_AutoBrew)
        self.ExitButtonRecipe.clicked.connect(self.Leave_Manual_Control_Mode)
        
        # print("everything setup starting loop")

    def Live_Pi_Button_Pressed(self):
        self.systemActive = "LivePi"
        self.showFullScreen()  # for touchscreen
        self.MashTemp = self.read_temp_Mash() - 1
        self.HLTTemp = self.read_temp_HLT() - 1
        self.Log_Write("Live - Mash Temp is: " + str(self.MashTemp + 1))
        self.Log_Write("Live - HLT Temp is: " + str(self.HLTTemp + 1))
        self.Update_Displays()
        self.Build_Recipe_Page()
        self.RecipeButton_Pressed()
        self.Tabs.setCurrentIndex(1)

    def Test_Pi_Button_Pressed(self):
        self.systemActive = "TestPi"
        self.showFullScreen()  # for touchscreen
        self.MashFloatSwitch = 0
        self.HLTFloatSwitch = 0
        self.MashTemp = 90 # Dummy for testing
        self.HLTTemp = 100 # Dummy for testing        
        self.Log_Write("Testing (Pi) - Mash Temp is: " + str(self.MashTemp))
        self.Log_Write("Testing (Pi) - HLT Temp is: " + str(self.HLTTemp))
        self.Build_Recipe_Page()
        self.RecipeButton_Pressed()
        self.Tabs.setCurrentIndex(1)
        
    def Live_PC_Button_Pressed(self):
        self.systemActive = "LivePC"
        # self.showFullScreen()  # for touchscreen mainly
        self.MashTemp = self.read_temp_Mash() - 1
        self.HLTTemp = self.read_temp_HLT() - 1
        self.Log_Write("Live - Mash Temp is: " + str(self.MashTemp) + 1)
        self.Log_Write("Live - HLT Temp is: " + str(self.HLTTemp) + 1)
        self.Update_Displays()
        self.Build_Recipe_Page()
        self.RecipeButton_Pressed()
        self.Tabs.setCurrentIndex(1)
        
        
    def Test_PC_Button_Pressed(self):
        self.systemActive = "TestPC"
        self.MashFloatSwitch = 0
        self.HLTFloatSwitch = 0
        self.MashTemp = 90 # Dummy for testing
        self.HLTTemp = 100 # Dummy for testing        
        self.Log_Write("Testing (PC) - Mash Temp is: " + str(self.MashTemp))
        self.Log_Write("Testing (PC) - HLT Temp is: " + str(self.HLTTemp))
        self.Build_Recipe_Page()
        self.RecipeButton_Pressed()
        self.Tabs.setCurrentIndex(1)

    def Build_Recipe_Page(self):
    
        # Rest 1
        self.aligntext = self.DRest1Name.displayText()
        x = self.aligntext.index(" ")        
        if x != 0:
            self.aligntext = self.aligntext[0:x] + "\n" + self.aligntext[x+1:]       
        self.Rest1Button.setText(self.aligntext + "\n(" + str(self.DRest1Temp.value())+"/" + str(self.DRest1Time.value()) + ")")
        if self.DRest1Check.isChecked():
            self.Rest1Button.setChecked(True)
        else:
            self.Rest1Button.setChecked(False)
            
        # Rest 2
        self.aligntext = self.DRest2Name.displayText()
        x = self.aligntext.index(" ")        
        if x != 0:
            self.aligntext = self.aligntext[0:x] + "\n" + self.aligntext[x+1:]       
        self.Rest2Button.setText(self.aligntext + "\n(" + str(self.DRest2Temp.value())+"/" + str(self.DRest2Time.value()) + ")")
        if self.DRest2Check.isChecked():
            self.Rest2Button.setChecked(True)
        else:
            self.Rest2Button.setChecked(False)
            
        # Rest 3
        self.aligntext = self.DRest3Name.displayText()
        x = self.aligntext.index(" ")        
        if x != 0:
            self.aligntext = self.aligntext[0:x] + "\n" + self.aligntext[x+1:]       
        self.Rest3Button.setText(self.aligntext + "\n(" + str(self.DRest3Temp.value())+"/" + str(self.DRest3Time.value()) + ")")
        if self.DRest3Check.isChecked():
            self.Rest3Button.setChecked(True)
        else:
            self.Rest3Button.setChecked(False)
            
        # Rest 4
        self.aligntext = self.DRest4Name.displayText()
        x = self.aligntext.index(" ")        
        if x != 0:
            self.aligntext = self.aligntext[0:x] + "\n" + self.aligntext[x+1:]       
        self.Rest4Button.setText(self.aligntext + "\n(" + str(self.DRest4Temp.value())+"/" + str(self.DRest4Time.value()) + ")")
        if self.DRest4Check.isChecked():
            self.Rest4Button.setChecked(True)
        else:
            self.Rest4Button.setChecked(False)
            
        # Rest 5
        self.aligntext = self.DRest5Name.displayText()
        x = self.aligntext.index(" ")        
        if x != 0:
            self.aligntext = self.aligntext[0:x] + "\n" + self.aligntext[x+1:]       
        self.Rest5Button.setText(self.aligntext + "\n(" + str(self.DRest5Temp.value())+"/" + str(self.DRest5Time.value()) + ")")
        if self.DRest5Check.isChecked():
            self.Rest5Button.setChecked(True)
        else:
            self.Rest5Button.setChecked(False)
            
        # Rest 6
        self.aligntext = self.DRest6Name.displayText()
        x = self.aligntext.index(" ")        
        if x != 0:
            self.aligntext = self.aligntext[0:x] + "\n" + self.aligntext[x+1:]       
        self.Rest6Button.setText(self.aligntext + "\n(" + str(self.DRest6Temp.value())+"/" + str(self.DRest6Time.value()) + ")")
        if self.DRest6Check.isChecked():
            self.Rest6Button.setChecked(True)
        else:
            self.Rest6Button.setChecked(False)

        # Rest 7
        self.aligntext = self.DRest7Name.displayText()
        x = self.aligntext.index(" ")        
        if x != 0:
            self.aligntext = self.aligntext[0:x] + "\n" + self.aligntext[x+1:]       
        self.Rest7Button.setText(self.aligntext + "\n(" + str(self.DRest7Temp.value())+"/" + str(self.DRest7Time.value()) + ")")
        if self.DRest7Check.isChecked():
            self.Rest7Button.setChecked(True)
        else:
            self.Rest7Button.setChecked(False)
                                 
        # Rest 8
        self.aligntext = self.DRest8Name.displayText()
        x = self.aligntext.index(" ")        
        if x != 0:
            self.aligntext = self.aligntext[0:x] + "\n" + self.aligntext[x+1:]       
        self.Rest8Button.setText(self.aligntext + "\n(" + str(self.DRest8Temp.value())+"/" + str(self.DRest8Time.value()) + ")")
        if self.DRest8Check.isChecked():
            self.Rest8Button.setChecked(True)
        else:
            self.Rest8Button.setChecked(False)
            
        # Press Recipe Button to set up recipes
        # then switch to Recipe Tab
        self.RecipeButton_Pressed()
        self.Tabs.setCurrentIndex(1)
        
                                 
    def RecipeButton_Pressed(self):
        
        self.index = 0
        self.recipenames = []
        self.recipetemps = []
        self.recipetimes = []
            
        if self.Rest1Button.isChecked():
            self.recipenames.append(self.DRest1Name.text())
            self.recipetemps.append(self.DRest1Temp.value())
            self.recipetimes.append(self.DRest1Time.value())
            self.index += 1

        if self.Rest2Button.isChecked():
            self.recipenames.append(self.DRest2Name.text())
            self.recipetemps.append(self.DRest2Temp.value())
            self.recipetimes.append(self.DRest2Time.value())
            self.index += 1            

        if self.Rest3Button.isChecked():
            self.recipenames.append(self.DRest3Name.text())
            self.recipetemps.append(self.DRest3Temp.value())
            self.recipetimes.append(self.DRest3Time.value())
            self.index += 1
            
        if self.Rest4Button.isChecked():
            self.recipenames.append(self.DRest4Name.text())
            self.recipetemps.append(self.DRest4Temp.value())
            self.recipetimes.append(self.DRest4Time.value())
            self.index += 1
    
        if self.Rest5Button.isChecked():
            self.recipenames.append(self.DRest5Name.text())
            self.recipetemps.append(self.DRest5Temp.value())
            self.recipetimes.append(self.DRest5Time.value())
            self.index += 1            

        if self.Rest6Button.isChecked():
            self.recipenames.append(self.DRest6Name.text())
            self.recipetemps.append(self.DRest6Temp.value())
            self.recipetimes.append(self.DRest6Time.value())
            self.index += 1
            
        if self.Rest7Button.isChecked():
            self.recipenames.append(self.DRest7Name.text())
            self.recipetemps.append(self.DRest7Temp.value())
            self.recipetimes.append(self.DRest7Time.value())
            self.index += 1
            
        if self.Rest8Button.isChecked():
            self.recipenames.append(self.DRest8Name.text())
            self.recipetemps.append(self.DRest8Temp.value())
            self.recipetimes.append(self.DRest8Time.value())
            self.index += 1    
        
        for i in range(0, self.index):
            if i == 0:
                self.Rest1Name = self.recipenames[i]
                self.Rest1Temp.setValue(self.recipetemps[i])
                self.Rest1Time.setValue(self.recipetimes[i])
            if i == 1:
                self.Rest2Name = self.recipenames[i] 
                self.Rest2Temp.setValue(self.recipetemps[i])
                self.Rest2Time.setValue(self.recipetimes[i])
            if i == 2:
                self.Rest3Name = self.recipenames[i] 
                self.Rest3Temp.setValue(self.recipetemps[i])
                self.Rest3Time.setValue(self.recipetimes[i])
            if i == 3:
                self.Rest4Name = self.recipenames[i] 
                self.Rest4Temp.setValue(self.recipetemps[i])
                self.Rest4Time.setValue(self.recipetimes[i])
            if i == 4:
                self.Rest5Name = self.recipenames[i] 
                self.Rest5Temp.setValue(self.recipetemps[i])
                self.Rest5Time.setValue(self.recipetimes[i])
            if i == 5:
                self.Rest6Name = self.recipenames[i] 
                self.Rest6Temp.setValue(self.recipetemps[i])
                self.Rest6Time.setValue(self.recipetimes[i])
                
        for i in range(self.index, 6):
            if i == 0:
                self.Rest1Name = "Null"                
                self.Rest1Temp.setValue(0)
                self.Rest1Time.setValue(0)
            if i == 1:
                self.Rest2Name = "Null"
                self.Rest2Temp.setValue(0)
                self.Rest2Time.setValue(0)
            if i == 2:
                self.Rest3Name = "Null"
                self.Rest3Time.setValue(0)
                self.Rest3Temp.setValue(0)
            if i == 3:
                self.Rest4Name = "Null"
                self.Rest4Temp.setValue(0)
                self.Rest4Time.setValue(0)
            if i == 4:
                self.Rest5Name = "Null"
                self.Rest5Temp.setValue(0)
                self.Rest5Time.setValue(0)
            if i == 5:
                self.Rest6Name = "Null"
                self.Rest6Temp.setValue(0)
                self.Rest6Time.setValue(0)
            if i == 6:
                self.Rest6Name = "Null"
                self.Rest6Temp.setValue(0)
                self.Rest6Time.setValue(0)
                
    def timerEvent(self, event):
        if self.Tabs.currentIndex() == 4:
            if self.autobrew == False:          
                if self.go_button_indicator != 1:
                    self.Let_Er_Rip()
                else:
                    return
        else:
            if self.Tabs.currentIndex() == 3:              
                self.autobrewstatus = "In Progress"            
                if self.autobrew == True:
                    self.AutoBrew_Loop()
                if self.autobrewstatus == "Complete":
                    self.Tabs.setCurrentIndex(4)
                    
    def Change_Flag_Set(self):

        if self.Change_Flag != 1:
            self.Go.setEnabled(True)
            self.Go.setStyleSheet("background-color: green")
            self.Change_Flag = 1
            # Stop timer until Go button pushed
            self.go_button_indicator = 1

    def Go_Button_Clicked(self):
            self.go_button_indicator = 0
            self.Let_Er_Rip()
             
    def Leave_Manual_Control_Mode(self):
        # self.showMaximized()
        
        # Stop timer
        # form.timer.stop()
        
        # Turn off Everything (for now)
        self.Pump_Off_Button_Pressed()
        self.HLT_Off_Button_Pressed()
        self.Log_Write("Exiting - Turning Off Pump and HLT")
        
        if self.systemActive[0:4] == "Live":
            GPIO.output(Pump_Primary_GPIO, False)
            GPIO.output(Pump_Secondary_GPIO, False)
            GPIO.output(HLT_Primary_GPIO, False)
            GPIO.output(HLT_Secondary_GPIO, False)

        sys.exit()
        
    def Pump_On_Button_Pressed(self):
        self.Pump = "On"
        self.Log_Write("Manually Turn on Pump")
        self.Change_Pump_Button_Colors_On()
        self.Let_Er_Rip()
        
    def Pump_Off_Button_Pressed(self):
        self.Pump = "Off"
        self.Log_Write("Manually Turn off Pump")
        self.Change_Pump_Button_Colors_Off()
        self.Let_Er_Rip()
        
    def HLT_On_Button_Pressed(self):
        self.HLT = "On"
        self.Log_Write("Manually Turn on HLT")
        self.Change_HLT_Button_Colors_On()
        self.Let_Er_Rip()
        
    def HLT_Off_Button_Pressed(self):
        self.HLT = "Off"
        self.Log_Write("Manually Turn off HLT")
        self.Change_HLT_Button_Colors_Off()
        self.Let_Er_Rip()
        
    def Change_Pump_Button_Colors_Off(self):
        self.PumpOn.setStyleSheet("background-color: white")
        self.PumpOff.setStyleSheet("background-color: red") 

    def Change_Pump_Button_Colors_On(self):
        self.PumpOn.setStyleSheet("background-color: green")
        self.PumpOff.setStyleSheet("background-color: white")

    def Change_HLT_Button_Colors_Off(self):
        self.HLTOn.setStyleSheet("background-color: white")
        self.HLTOff.setStyleSheet("background-color: red") 

    def Change_HLT_Button_Colors_On(self):
        self.HLTOn.setStyleSheet("background-color: green")
        self.HLTOff.setStyleSheet("background-color: white")

    def read_temp_raw_Mash(self):
        f = open(device_file_Mash, 'r')
        self.lines = f.readlines()
        f.close()
        return self.lines

    def read_temp_Mash(self):
        # Line below should be removed to go live
        if self.systemActive[0:4] == "Test":
            return self.MashTemp
        else:
            self.lines = self.read_temp_raw_Mash()
            while self.lines[0].strip()[-3] != 'Y':
                #print(self.lines[0].strip()[-3])
                time.sleep(0.2)
                self.lines = self.read_temp_raw_Mash()
            self.equals_pos = self.lines[1].find('t=')
            if self.equals_pos != -1:
                self.temp_string = self.lines[1][self.equals_pos+2:]
                self.temp_c = float(self.temp_string) / 1000.0
                self.MashTemp = self.temp_c * 9.0 / 5.0 +32.0
                # print("mash temp =", self.MashTemp)
                return self.MashTemp

    def read_temp_raw_HLT(self):
        f = open(device_file_HLT, 'r')
        self.lines = f.readlines()
        f.close()
        return self.lines

    def read_temp_HLT(self):
        # Line below should be removed to go live
        if self.systemActive[0:4] == "Test":
            return self.HLTTemp
        else:
            self.lines = self.read_temp_raw_HLT()
            while self.lines[0].strip()[-3] != 'Y':
                time.sleep(0.2)
                self.lines = self.read_temp_raw_HLT()
            self.equals_pos = self.lines[1].find('t=')
            if self.equals_pos != -1:
                self.temp_string = self.lines[1][self.equals_pos+2:]
                self.temp_c = float(self.temp_string) / 1000.0
                self.HLTTemp = self.temp_c * 9.0 / 5.0 +32.0
                return self.HLTTemp
            
    def calc_brew(self):
    
    # Set up for computation of start times
        
        self.ScheduleBox.clear()
        self.startclocktime = QTime.currentTime()
        self.startcomputetime =  QTime.currentTime()
        self.startcomputetime.setHMS(0, 0, 0)
        self.mashcomputetime = self.startcomputetime
        self.hltcomputetime = self.startcomputetime
        self.currentstephlttime = 0
        self.previousstephlttime = 0
        self.currentstephlttemp = 0
        self.previousstepmashtime = 0
        self.previousstepmashtemp = 0
        self.clocktimeprep = self.startclocktime
        self.timeprep = self.startcomputetime
        
        # This allows clock time to be calculated from brew time
        
        self.calcclocktimedifference = self.startcomputetime.secsTo(self.startclocktime)       
        self.starttimes = []  # Brew time (not clock time)
        self.mashtemps = []
        self.hlttemps = []
        self.names = []
        self.types = []
        self.durationtimes = []
        
        # These are for exporting the schedule
        self.sched1 = []
        self.sched2 = []
        self.sched3 = []
        self.sched4 = []
        self.sched5 = []
        
        self.weredone = False
        
        # Step_Sequencer parameters:
        
        # Field #   Description              From Call      Inside Function
        
        #   1       Recipe Step Index         integer         stepindex
        #   2       Recipe Step Name          RestxName       currentstepname
        #   3       Mash Time                 RestxTime       currentstepmashtime
        #   4       Mash Temp                 RestxTemp       currentstepmashtemp
        #   5       Previous Step Name        Rest(x-1)Name   previousstepname
        #   6       Previous Step Time        Rest(x-1)Time   previousstepmashtime
        #   7       Next Step Name            Rest(x+1)Name   nextstepname
        #   8       Next Mash Temp            Rest(x+1)Temp   nextstepmashtemp
        
        # Transformed variables pushed to ScheduleBox
        
        #   1       self.schedulefield1       currentstepname
        #   2       self.schedulefield2       self.timedisplay
        #   3       self.schedulefield3       self.clocktimedisplay (calculated from timedisplay)
        #   4       self.schedulefield4       currentstepmashtemp
        #   5       self.schedulefield5       self.currentstephlttemp
        
        # Convert Recipe to lists
        
        RecipeNames = []
        RecipeMashTemps = []
        RecipeHLTTemps = []
        RecipeDisplayMashDurations = []
        RecipeMashDurations = []
        RecipeMashStartTimes = []
        RecipeHLTStartTimes = []
        RecipeHLTOffsets = []
        RecipeHLTDurations = []
        RecipeMashDelays = []
        
        if self.Rest1Name != "Null" and self.weredone == False:
            RecipeNames.append(self.Rest1Name)
            RecipeMashTemps.append(self.Rest1Temp.value())
            RecipeMashDurations.append(self.Rest1Time.value() * 60)
            RecipeDisplayMashDurations.append(self.Rest1Time.value() * 60)
            RecipeMashDelays.append(0)
        else:
            self.weredone = True
            
        if self.Rest2Name != "Null" and self.weredone == False:
            RecipeNames.append(self.Rest2Name)
            RecipeMashTemps.append(self.Rest2Temp.value())
            RecipeMashDurations.append(self.Rest2Time.value() * 60)
            RecipeDisplayMashDurations.append(self.Rest2Time.value() * 60)
            RecipeMashDelays.append(self.MashRaiseTimeCalc((self.Rest2Time.value() * 60), self.Rest2Temp.value(), self.Rest1Temp.value()))
        else:
            self.weredone = True
            
        if self.Rest3Name!= "Null" and self.weredone == False:
            RecipeNames.append(self.Rest3Name)
            RecipeMashTemps.append(self.Rest3Temp.value())      
            RecipeMashDurations.append(self.Rest3Time.value() * 60)
            RecipeDisplayMashDurations.append(self.Rest3Time.value() * 60)
            RecipeMashDelays.append(self.MashRaiseTimeCalc((self.Rest3Time.value() * 60), self.Rest3Temp.value(), self.Rest2Temp.value()))
        else:
            self.weredone = True
            
        if self.Rest4Name != "Null" and self.weredone == False:
            RecipeNames.append(self.Rest4Name)
            RecipeMashTemps.append(self.Rest4Temp.value())      
            RecipeMashDurations.append(self.Rest4Time.value() * 60)
            RecipeDisplayMashDurations.append(self.Rest4Time.value() * 60)
            RecipeMashDelays.append(self.MashRaiseTimeCalc((self.Rest4Time.value() * 60), self.Rest4Temp.value(), self.Rest3Temp.value()))
        else:
            self.weredone = True
            
        if self.Rest5Name != "Null" and self.weredone == False:
            RecipeNames.append(self.Rest5Name)
            RecipeMashTemps.append(self.Rest5Temp.value())
            RecipeMashDurations.append(self.Rest5Time.value() * 60)
            RecipeDisplayMashDurations.append(self.Rest5Time.value() * 60)
            RecipeMashDelays.append(self.MashRaiseTimeCalc((self.Rest5Time.value() * 60), self.Rest5Temp.value(), self.Rest4Temp.value()))
        else:
            self.weredone = True
            
        if self.Rest6Name != "Null" and self.weredone == False:
            RecipeNames.append(self.Rest6Name)
            RecipeMashTemps.append(self.Rest6Temp.value())        
            RecipeMashDurations.append(self.Rest6Time.value() * 60)
            RecipeDisplayMashDurations.append(self.Rest6Time.value() * 60)
            RecipeMashDelays.append(self.MashRaiseTimeCalc((self.Rest6Time.value() * 60), self.Rest6Temp.value(), self.Rest5Temp.value()))             
             
        # Calculate HLT Temps from Mash Temps        
        for y in range(len(RecipeNames)):
            RecipeHLTTemps.append(str(int(RecipeMashTemps[y] + self.MTHLTDifferential.value())))
        
        # Calculate HLT Durations - number of seconds to 
        for y in range(len(RecipeNames) - 1):
            
                self.hltoffset = int(1 / (self.HLTRaiseTime.value()) * (int(RecipeHLTTemps[y+1]) - int(RecipeHLTTemps[y])) * 60)               
                RecipeHLTOffsets.append(self.hltoffset)       
                RecipeHLTDurations.append(int(RecipeDisplayMashDurations[y]) - self.hltoffset)
        
        RecipeHLTOffsets.append(int(1 / int(self.HLTRaiseTime.value()) * (int(RecipeHLTTemps[y+1]) - int(RecipeHLTTemps[y])) * 60))     
        RecipeHLTDurations.append(int(RecipeDisplayMashDurations[y]) - (1 / int(self.HLTRaiseTime.value()) * (int(RecipeHLTTemps[y+1]) - int(RecipeHLTTemps[y])) * 60))
# line above had y+1 in first []
            
        for y in range(len(RecipeNames)):
                 
            self.Step_Sequencer(y, RecipeNames, RecipeMashTemps, RecipeMashStartTimes, RecipeMashDurations, RecipeDisplayMashDurations, RecipeHLTTemps, RecipeHLTStartTimes, RecipeHLTDurations, RecipeHLTOffsets, RecipeMashDelays)
            
        self.Close_Out_Calc(y, RecipeNames, RecipeMashTemps, RecipeMashStartTimes, RecipeMashDurations, RecipeDisplayMashDurations, RecipeHLTTemps, RecipeHLTStartTimes, RecipeHLTDurations, RecipeMashDelays)


    def MashRaiseTimeCalc(self, startingduration, newtemp, oldtemp):
        x = newtemp - oldtemp
        y = (x / self.MTRaiseTime.value()) * 60
        newduration = startingduration + y
        return int(y)
        
    def Step_Sequencer(self, y, RecipeNames, RecipeMashTemps, RecipeMashStartTimes, RecipeMashDurations, RecipeDisplayMashDurations, RecipeHLTTemps, RecipeHLTStartTimes, RecipeHLTDurations, RecipeHLTOffsets, RecipeMashDelays):
             
            self.stepindex = y
            
            if y == 0:
                self.hltcomputetime = self.mashcomputetime
                RecipeMashStartTimes.append(0)
                RecipeHLTStartTimes.append(0)
                
            if y > 0:
                self.mashcomputetime = self.mashcomputetime.addSecs(RecipeDisplayMashDurations[y-1])
                self.delayedmashtime = self.mashcomputetime.addSecs(RecipeMashDelays[y])
                self.timedisplay = QTime.toString(self.mashcomputetime, timeformat)           
                self.clocktimedisplay = QTime.toString(self.mashcomputetime.addSecs(self.calcclocktimedifference), clockformat)
                self.schedulefield1 = RecipeNames[y] + " Mash Preheat"
                self.schedulefield2, self.schedulefield3, self.schedulefield4, self.schedulefield5 = str(self.timedisplay), str(self.clocktimedisplay), str(RecipeMashTemps[y]) , str(RecipeHLTTemps[y]) 
                self.changetype = "Mash"
                self.Schedule_Write()
                self.mashcomputetime = self.mashcomputetime.addSecs(RecipeMashDelays[y])
                
            self.timedisplay = QTime.toString(self.mashcomputetime, timeformat)           
            self.clocktimedisplay = QTime.toString(self.mashcomputetime.addSecs(self.calcclocktimedifference), clockformat)
            self.schedulefield1, self.schedulefield2, self.schedulefield3, self.schedulefield4, self.schedulefield5 = RecipeNames[y] + " Begins", str(self.timedisplay), str(self.clocktimedisplay), str(RecipeMashTemps[y]) , str(RecipeHLTTemps[y]) 
            self.changetype = "Mash"
            self.Schedule_Write()
            
            if self.stepindex < len(RecipeNames) - 1 and RecipeNames[y] != "Null": 
                self.hltcomputetime = self.mashcomputetime.addSecs(RecipeHLTDurations[y])
                self.timedisplay = QTime.toString(self.hltcomputetime, timeformat)           
                self.clocktimedisplay = QTime.toString(self.hltcomputetime.addSecs(self.calcclocktimedifference), clockformat)
                self.schedulefield1, self.schedulefield2, self.schedulefield3, self.schedulefield4, self.schedulefield5 = RecipeNames[y] + " HLT Preheat", str(self.timedisplay), str(self.clocktimedisplay), str(RecipeMashTemps[y]) , str(RecipeHLTTemps[y+1]) 
                self.changetype = "HLT"                
                if y < len(RecipeNames) - 1:
                    self.Schedule_Write()
    
                self.previousstephlttime = self.hltcomputetime
                self.previousstepmashtime = self.mashcomputetime

            else:
                self.previousstephlttime = self.hltcomputetime
                self.previousstepmashtime = self.mashcomputetime
                self.Close_Out_Calc(y, RecipeNames, RecipeMashTemps, RecipeMashStartTimes, RecipeMashDurations, RecipeDisplayMashDurations, RecipeHLTTemps, RecipeHLTStartTimes, RecipeHLTDurations, RecipeHLTOffsets)
            return
            
    def Close_Out_Calc(self, y, RecipeNames, RecipeMashTemps, RecipeMashStartTimes, RecipeMashDurations, RecipeDisplayMashDurations, RecipeHLTTemps, RecipeHLTStartTimes, RecipeHLTDurations, RecipeHLTOffsets):
                if self.schedulefield1 != "Mash End / Sparge":
                    self.mashcomputetime = self.mashcomputetime.addSecs(RecipeDisplayMashDurations[y])
                    self.timedisplay = QTime.toString(self.mashcomputetime, timeformat)     
                    self.clocktimedisplay = QTime.toString(self.mashcomputetime.addSecs(self.calcclocktimedifference), clockformat)    
                    self.schedulefield1, self.schedulefield2, self.schedulefield3, self.schedulefield4, self.schedulefield5 = "Mash End / Sparge", str(self.timedisplay), str(self.clocktimedisplay), "   " , "   "
                    self.Schedule_Write()
                    self.hlttemps.append(str(int(RecipeHLTTemps[y])))
                    self.hlttemps.append('   ')
                    self.RecipeNames = RecipeNames
                    self.RecipeMashTemps = RecipeMashTemps
                    self.RecipeHLTTemps = RecipeHLTTemps
                    self.RecipeMashDurations = RecipeMashDurations
                    self.RecipeDisplayMashDurations = RecipeDisplayMashDurations
                    self.RecipeMashStartTimes = RecipeMashStartTimes
                    self.RecipeHLTStartTimes = RecipeHLTStartTimes
                    self.RecipeHLTDurations = RecipeHLTDurations
                    self.RecipeHLTOffsets = RecipeHLTOffsets
                self.Tabs.setCurrentIndex(2)

    def Schedule_Write(self):
        if platform.system() == "Windows":
            self.inserttext = self.schedulefield1 + self.spaces[0:31-len(self.schedulefield1)] + self.schedulefield2 + self.spaces[0:4] + self.schedulefield3 + self.spaces[0:6]+ self.schedulefield4 + self.spaces[0:4] + self.schedulefield5
        else:
            self.inserttext = self.schedulefield1 + self.spaces[0:39-len(self.schedulefield1)] + self.schedulefield2 + self.spaces[0:8] + self.schedulefield3 + self.spaces[0:9]+ self.schedulefield4 + self.spaces[0:6] + self.schedulefield5
        self.ScheduleBox.insertPlainText(self.inserttext)
        self.ScheduleBox.insertHtml("<br>")
        self.starttimes.append(self.schedulefield2)        
       
        #if self.schedulefield1 != "Mash Ramp Up":
        self.types.append(self.changetype)
        if self.changetype == "Mash":
            self.mashtemps.append(self.schedulefield4)
            self.names.append(self.schedulefield1)
        else:
            self.hlttemps.append(self.schedulefield5) 

        # Build array just for export of schedule
        self.sched1.append(self.schedulefield1)
        self.sched2.append(self.schedulefield2)
        self.sched3.append(self.schedulefield3)
        self.sched4.append(self.schedulefield4)
        self.sched5.append(self.schedulefield5)
            
    def Start_Button_Pressed(self, RecipeNames):
        
        # first make sure temps are at proper place prior to starting time tracking

        self.Log_Write("Initiating automated brewing cycle")
        self.autobrew = True
        
        # set parameters away from manual, appropriate for autobrew
        
        self.Pump = "On"
        self.HLT = "On"
        self.RespectHLTFloatSwitchHLT.setChecked(True)
        self.RespectHLTFloatSwitchPump.setChecked(True)
        self.RespectHLTTempSet.setChecked(True)
        self.RespectMashFloatSwitchPump.setChecked(True)
        self.RespectMashTempSet.setChecked(True)
        
        self.numberofsteps = len(self.RecipeMashTemps)

        self.calctotalstarttime = QTime.currentTime()
        self.calctotalstarttime1 = self.calctotalstarttime
        self.calctotalstarttime1.setHMS(0, 0, 0)
        self.calctotalstarttimedifferential = self.calctotalstarttime1.secsTo(QTime.currentTime())
        self.calctotalstarttime.start()
   
        self.CurrentTempStepHLTBegan.setText(QTime.currentTime().toString(clockformat))
    
        self.calchltstarttime = QTime.currentTime()
        self.calchltstarttime1 = self.calchltstarttime
        self.calchltstarttime1.setHMS(0, 0, 0)
        self.calchltstarttimedifferential = self.calchltstarttime1.secsTo(QTime.currentTime())
        self.calchltstarttime.start()            

    def AutoBrew_Loop(self):
        
        for self.i in range(0, self.numberofsteps):
            self.Log_Write("Mash Step "+str(self.i + 1)+":  " + self.RecipeNames[self.i] + " Initiated")
            self.Mash_Step()

        # End of AutoBrew
        self.End_Of_AutoBrew()
               
    def End_Of_AutoBrew(self):
        self.autobrew = False
        self.Pump = "Off"
        self.HLT = "Off"        
        self.CurrentRecipeStepTimeToNext.setText("")
        self.autobrewstatus = "Complete"
        self.Log_Write("Automated brewing cycle complete")
        self.go_button_indicator = 0
        self.Export_Chart()
        self.Export_Log()
        self.Export_Sched()
        if self.systemActive[0:4] != "Test":
            message = self.twilioCli.messages.create(body='AutoBrew Complete - Time to Sparge!', from_= self.myTwilioNumber, to= self.myCellPhone)   
        self.Tabs.setCurrentIndex(4)
                
    def Waiting_For_Mash_Display(self):
        self.CurrentRecipeStepName.setText(self.RecipeNames[self.i])           
        self.CurrentTempStepMashSet.setText(str(self.RecipeMashTemps[self.i]))
        self.CurrentTempStepHLTSet.setText(str(self.RecipeHLTTemps[self.i]))
        #self.CurrentTempStepMashTimeToNext.setText("Waiting")
        self.CurrentTempStepHLTTimeToNext.setText("Waiting")
        if self.i < self.numberofsteps - 1:
            self.UpcomingRecipeStepName.setText(self.RecipeNames[self.i+1])
            self.UpcomingMashTempSet.setText(str(self.RecipeMashTemps[self.i+1]))
            self.UpcomingHLTTempSet.setText(str(self.RecipeHLTTemps[self.i+1]))
        else:
            self.UpcomingRecipeStepName.setText("Complete")
            self.UpcomingMashTempSet.setText("")
            self.UpcomingHLTTempSet.setText("")        
        
        self.Master_Display_Update()
 
    def Mash_Temp_Reached_Display(self):
        self.currentrecipebegan = QTime.currentTime()        
        self.CurrentRecipeStepBegan.setText(self.currentrecipebegan.toString(clockformat))
        # self.CurrentTempStepMashBegan.setText(self.currentrecipebegan.toString(clockformat))
        self.Log_Write("Mash Step " + str(self.i + 1) + ":  " + self.RecipeNames[self.i] + " (" + str(self.RecipeMashTemps[self.i]) + ") Started")

        if self.i + 1 < self.numberofsteps - 1:   
            self.CurrentTempStepHLTTimeToNext.setText(self.currentrecipebegan.addSecs(self.RecipeHLTDurations[self.i]).toString(timeformat))
        else:
            self.CurrentTempStepHLTTimeToNext.setText("") 

        if self.i < self.numberofsteps - 1:
            self.UpcomingRecipeStepBegins.setText(self.currentrecipebegan.addSecs(self.RecipeMashDurations[self.i]).toString(clockformat))           
            self.UpcomingHLTBegins.setText(self.currentrecipebegan.addSecs(self.RecipeMashDurations[self.i] - self.RecipeHLTOffsets[self.i]).toString(clockformat))
        else:
            self.UpcomingRecipeStepBegins.setText("")              
            self.UpcomingHLTBegins.setText("")  
    
        self.Master_Display_Update()
        
    def Mash_In_Progress_Display(self, calcmashstarttime):
        self.currenttime = QTime.currentTime()
        m1, s1 = divmod(self.calcmashstarttime.elapsed() / 1000, 60)
        h1, m1 = divmod(m1, 60)
        self.CurrentRecipeStepElapsed.setText("%d:%02d:%02d" % (h1, m1, s1))      

        self.timetonextcalc = self.RecipeMashDurations[self.i] - (h1 * 3600 + m1 * 60 + s1)
        m1, s1 = divmod(self.timetonextcalc, 60)
        h1, m1 = divmod(m1, 60)        
        self.CurrentRecipeStepTimeToNext.setText("%d:%02d:%02d" % (h1, m1, s1))                
        
        if self.i < self.numberofsteps - 1:
            if self.hlttimereached == False:
                self.nexthlttime = self.RecipeMashDurations[self.i] - (calcmashstarttime.elapsed() / 1000) - self.RecipeHLTOffsets[self.i]
                m1, s1 = divmod(self.nexthlttime, 60)
                h1, m1 = divmod(m1, 60)
                if h1 >= 0 and self.UpcomingHLTBegins.displayText() != "Calculating":
                    self.CurrentTempStepHLTTimeToNext.setText("%d:%02d:%02d" % (h1, m1, s1))
                else:
                    self.CurrentTempStepHLTTimeToNext.setText("Calculating")            
            else:
                if self.i < self.numberofsteps - 1:
                    self.nexthlttime = self.RecipeMashDurations[self.i+1] - (calcmashstarttime.elapsed() / 1000) - self.RecipeHLTOffsets[self.i+1]
                    m1, s1 = divmod(self.nexthlttime, 60)
                    h1, m1 = divmod(m1, 60)
                    if h1 >= 0 and self.UpcomingHLTBegins.displayText() != "Calculating":
                        self.CurrentTempStepHLTTimeToNext.setText("%d:%02d:%02d" % (h1, m1, s1))
                    else:
                        self.CurrentTempStepHLTTimeToNext.setText("Calculating")
                else:
                    self.CurrentTempStepHLTTimeToNext.setText("Complete")
        else:
            self.CurrentTempStepHLTTimeToNext.setText("")     

        self.Master_Display_Update()
          
    def HLT_Temp_Reached_Display(self):
        
        self.hltstarttime = QTime.currentTime()        
        self.CurrentTempStepHLTBegan.setText(self.hltstarttime.toString(clockformat))

        if self.i + 1 < self.numberofsteps - 1:
            self.UpcomingHLTTempSet.setText(str(int(self.RecipeHLTTemps[self.i+2])))
            self.calchltstarttime.start()
            self.Log_Write("Mash Step "+str(self.i + 1)+":  " + self.RecipeNames[self.i]+" Setting HLT To: " + self.RecipeHLTTemps[self.i+1])  #+2
        else:
            if self.i < self.numberofsteps - 1:
                self.UpcomingHLTTempSet.setText(str(int(self.RecipeHLTTemps[self.i+1])))
                self.calchltstarttime.start()
                self.Log_Write("Mash Step "+str(self.i + 1)+":  " + self.RecipeNames[self.i]+" Setting HLT To: " + self.RecipeHLTTemps[self.i+1])
            else:
                self.UpcomingHLTTempSet.setText("")
        if self.i < self.numberofsteps - 1:
            self.CurrentTempStepHLTSet.setText(str(int(self.RecipeHLTTemps[self.i+1])))
            self.HLTTempSet.setValue(int(self.RecipeHLTTemps[self.i+1]))
            self.calchltstarttime.start() 
            #self.Log_Write("Mash Step "+str(self.i + 1)+":  " + self.RecipeNames[self.i]+" Setting HLT To: " + self.RecipeHLTTemps[self.i+1])
        else:
            self.CurrentTempStepHLTSet.setText(str(int(self.RecipeHLTTemps[self.i])))            

        
        if self.i + 1 < self.numberofsteps - 1:
            self.UpcomingHLTBegins.setText("Calculating")
            self.CurrentTempStepHLTTimeToNext.setText("Calculating")
        else:
            self.UpcomingHLTBegins.setText("")
            self.CurrentTempStepHLTTimeToNext.setText("")            


        self.Master_Display_Update()
        

    def Master_Display_Update(self):
        # Update Current Time and Total Elapsed Time

        self.TimeOfDay.setText(QTime.currentTime().toString(clockformat))
        
        m1, s1 = divmod(self.calctotalstarttime.elapsed() / 1000, 60)
        h1, m1 = divmod(m1, 60)
        self.TotalElapsedTime.setText("%d:%02d:%02d" % (h1, m1, s1))
                
        m1, s1 = divmod(self.calchltstarttime.elapsed() / 1000, 60)
        h1, m1 = divmod(m1, 60)
        self.CurrentTempStepHLTElapsed.setText("%d:%02d:%02d" % (h1, m1, s1))        
    
    def Mash_Step(self):
        
        self.hlttimereached = False
        self.Waiting_For_Mash_Display()
        self.MashTempSet.setValue(self.RecipeMashTemps[self.i])
        self.HLTTempSet.setValue(int(self.RecipeHLTTemps[self.i]))
        
        self.calcmashstarttime = QTime.currentTime()
        self.calcmashstarttime1 = self.calcmashstarttime
        self.calcmashstarttime1.setHMS(0, 0, 0)
        self.calcmashstarttimedifferential = self.calcmashstarttime1.secsTo(QTime.currentTime())
        self.calcmashstarttime.start()
        
        while self.MashTemp < self.RecipeMashTemps[self.i]:
            self.CurrentRecipeStepBegan.setText("Waiting")
            m1, s1 = divmod(self.calcmashstarttime.elapsed() / 1000, 60)
            h1, m1 = divmod(m1, 60)
            self.CurrentRecipeStepElapsed.setText("%d:%02d:%02d" % (h1, m1, s1))
            
            self.UpcomingRecipeStepBegins.setText("Waiting")
            self.CurrentRecipeStepTimeToNext.setText("")
            self.Let_Er_Rip()
            self.Waiting_For_Mash_Display()
            # time.sleep(1)

        
        self.calcmashstarttime = QTime.currentTime()
        self.calcmashstarttime1 = self.calcmashstarttime
        self.calcmashstarttime1.setHMS(0, 0, 0)
        self.calcmashstarttimedifferential = self.calcmashstarttime1.secsTo(QTime.currentTime())
        self.calcmashstarttime.start()
             
        # Ready to start mash cycle
        
        self.Mash_Temp_Reached_Display()
        
        while self.calcmashstarttime.elapsed() / 1000 < self.RecipeMashDurations[self.i] - self.RecipeHLTOffsets[self.i]:
            self.Let_Er_Rip()
            self.Mash_In_Progress_Display(self.calcmashstarttime)

        self.HLTTempSet.setValue(int(self.RecipeHLTTemps[self.i]))
        self.Let_Er_Rip()
        self.HLT_Temp_Reached_Display()
        self.hlttimereached = True
        
        while self.calcmashstarttime.elapsed() / 1000 < self.RecipeMashDurations[self.i]:
            self.Let_Er_Rip()
            self.Mash_In_Progress_Display(self.calcmashstarttime)        
    
    def Let_Er_Rip(self):

        QApplication.processEvents()
        # print("going through rip loop")
        # print("Respect Mash Temp?", self.RespectMashTempSet.isChecked())
        if self.systemActive[0:4] == "Test" and self.AutobrewPumpStatus.displayText() != "Off":
            self.MashTemp = self.MashTemp + 1
        if self.systemActive[0:4] == "Test" and self.AutobrewHLTStatus.displayText() != "Off":
            self.HLTTemp = self.HLTTemp + 1
            time.sleep(1)
        # Get Current Temps and Float Switch Settings
        
        if self.systemActive[0:4] == "Live":
            self.read_temp_Mash()
            self.read_temp_HLT()
            self.MashFloatSwitch = GPIO.input(Mash_Float_GPIO)
            self.HLTFloatSwitch = GPIO.input(HLT_Float_GPIO)

        self.Update_Displays()
         
        if (self.Pump == "On" and
            (self.RespectMashTempSet.isChecked()==0 or self.MashTemp < self.MashTempSet.value()) and
            (self.RespectMashFloatSwitchPump.isChecked() == 0 or self.MashFloatSwitch == 0) and
            (self.RespectHLTFloatSwitchPump.isChecked() == 0 or self.HLTFloatSwitch == 0)):

           # Raise GPIO Pin for Pump
           
            if self.systemActive[0:4] == "Live":
                GPIO.output(Pump_Primary_GPIO, True)
                GPIO.output(Pump_Secondary_GPIO, True)
            self.PumpRunningText.setText("Running")
            self.AutobrewPumpStatus.setText("On")
            # self.PumpRunningText.setStyleSheet("background-color: green")
            # print("Pump Running")

        else:

           # Lower GPIO Pin for Pump
           
            if self.systemActive[0:4] == "Live":
                GPIO.output(Pump_Primary_GPIO, False)
                GPIO.output(Pump_Secondary_GPIO, False)
            self.PumpRunningText.setText("Stopped")
            self.AutobrewPumpStatus.setText("Off")
            # self.PumpRunningText.setStyleSheet("background-color: red")
            # print("Pump Stopped")

        if (self.HLT == "On" and
           (self.RespectHLTTempSet.isChecked()==0 or self.HLTTemp < self.HLTTempSet.value()) and
           (self.RespectHLTFloatSwitchHLT.isChecked() == 0 or self.HLTFloatSwitch == 0)):

           # Raise GPIO Pin for HLT
            #print (self.HLTTemp)
            if self.systemActive[0:4] == "Live":
                    GPIO.output(HLT_Primary_GPIO, True)
                    GPIO.output(HLT_Secondary_GPIO, True)
            self.HLTRunningText.setText("Running")
            self.AutobrewHLTStatus.setText("On")
           
           # self.HLTRunningText.setStyleSheet("background-color: green")
           # print("HLT Running")

        else:

           # Lower GPIO Pin for HLT
           
            if self.systemActive[0:4] == "Live":
                GPIO.output(HLT_Primary_GPIO, False)
                GPIO.output(HLT_Secondary_GPIO, False)
            self.HLTRunningText.setText("Stopped")
            self.AutobrewHLTStatus.setText("Off") 
           # self.HLTRunningText.setStyleSheet("background-color: red")
           # print("HLT Stopped")         

        # Update Displays

    def Update_Displays(self):
           
        self.CurrentMashTempDisplay.setText(str(int(self.MashTemp)))
        self.CurrentHLTTempDisplay.setText(str(int(self.HLTTemp)))
        self.AutobrewCurrentMashTempDisplay.setText(str(int(self.MashTemp)))
        self.AutobrewCurrentHLTTempDisplay.setText(str(int(self.HLTTemp)))
        
        self.Change_Flag = 0
        self.Go.setEnabled(False)
        self.Go.setStyleSheet("background-color: white")
           
        if self.MashFloatSwitch == 0:
            self.MashFloatText.setText("Down")
            # self.MashFloatText.setStyleSheet("background-color: green")

        else:

            self.MashFloatText.setText("Up")
            # self.MashFloatText.setStyleSheet("background-color: red") 

        if self.HLTFloatSwitch == 0:
            self.HLTFloatText.setText("Up")
            # self.HLTFloatText.setStyleSheet("background-color: green")

        else:

            self.HLTFloatText.setText("Down")
            # self.HLTFloatText.setStyleSheet("background-color: red")
        
        self.charttimecalc = QTime.currentTime()
        if self.charttimecalc.second() != self.lastsecond:            
            
            self.mashsetchartpoint = str(self.MashTempSet.value())
            self.mashchartpoint = str(self.MashTemp)
            self.hltsetchartpoint = str(self.HLTTempSet.value())
            self.hltchartpoint = str(self.HLTTemp)
            self.charttime = self.charttimecalc.toString(timeformat)
            
            self.charttext = self.charttime + self.spaces[0:4] + self.mashsetchartpoint + self.spaces[0:4] + self.mashchartpoint + self.spaces[0:4] + self.hltsetchartpoint + self.spaces[0:4] + self.hltchartpoint
            
            self.ChartBox.insertPlainText(self.charttext)
            self.ChartBox.insertHtml("<br>")              

            self.MashSetChartPoint.append(self.mashsetchartpoint)
            self.MashChartPoint.append(self.mashchartpoint)
            self.HLTSetChartPoint.append(self.hltsetchartpoint)
            self.HLTChartPoint.append(self.hltchartpoint)
            self.ChartTime.append(self.charttime)
                       
            self.lastsecond = self.charttimecalc.second()
    
    def Log_Write(self, logactivity):
        self.logfieldcalc1 = QTime.currentTime()
        self.logbrewtime = self.logfieldcalc1.addSecs(self.calcclocktimedifference * -1)
        self.logfield1 = self.logfieldcalc1.toString(clockformat)
        self.logfield2 = self.logbrewtime.toString(timeformat)
        self.logfield3 = logactivity
        self.inserttext = self.logfield1 + self.spaces[0:2] + self.logfield2  +  self.spaces[0:2] + self.logfield3 #+ self.spaces[0:6]+ self.logfield4 + self.spaces[0:4] + self.logfield5[:-2]
        self.LogBox.insertPlainText(self.inserttext)
        self.LogBox.insertHtml("<br>")  
        self.logboxtimes.append(self.logfield1)
        self.logboxtexts.append(self.logfield3)
        self.logboxbrewtimes.append(self.logfield2)
        
    def Export_Log(self):

        timestr = time.strftime("%Y%m%d-%H%M%S")
        self.filename = timestr + "_BrewLog.csv"
        f = open(self.filename, 'wt')
        self.rowtext = ("Clock Time" + "," + "Brew Time" + "," + "Log Entry" + "\n")
        f.write(self.rowtext)

        for j in range(0, len(self.logboxtimes)):
            self.rowtext = (self.logboxtimes[j] + "," + self.logboxbrewtimes[j] + "," + self.logboxtexts[j] + "\n")
            f.write(self.rowtext)
        f.close()
    
    def Export_Chart(self):
    
        timestr = time.strftime("%Y%m%d-%H%M%S")
        self.filename = timestr + "_BrewChart.csv"
        f = open(self.filename, 'wt')
        self.rowtext = ("Time" + "," + "Mash Set"+ "," + "Mash Temp" + "," + "HLT Set" + "," + "HLT Temp" + "\n")
        f.write(self.rowtext)

        for j in range(0, len(self.ChartTime)):
            self.rowtext = (self.ChartTime[j] + "," + str(self.MashSetChartPoint[j]) + "," + str(self.MashChartPoint[j]) + "," + str(self.HLTSetChartPoint[j]) + "," + str(self.HLTChartPoint[j]) + "\n")
            f.write(self.rowtext)
        f.close()        

    def Export_Sched(self):
    
        timestr = time.strftime("%Y%m%d-%H%M%S")
        self.filename = timestr + "_BrewSched.csv"
        f = open(self.filename, 'wt')
        self.rowtext = ("Step" + "," + "Brew Time"+ "," + "Clock Time" + "," + "Mash Temp Set" + "," + "HLT Temp Set" + "\n")
        f.write(self.rowtext)

        for j in range(0, len(self.sched1)):
            self.rowtext = (self.sched1[j] + "," + str(self.sched2[j]) + "," + str(self.sched3[j]) + "," + str(self.sched4[j]) + "," + str(self.sched5[j]) + "\n")
            f.write(self.rowtext)
        f.close()        

        
#        print("Pump Switch: ",self.Pump)
#        print("HLT Switch:  ",self.HLT)
#        print("Mash Temp Set:", (self.MashTempSet.value()))
#        print("Mash Temp: ", self.MashTemp)
#        print("HLT Temp Set:", (self.HLTTempSet.value()))
#        print("HLT Temp:", self.HLTTemp)
#        print("Respect Mash Temp? ", self.RespectMashTempSet.isChecked())
#        print("Respect Mash Float Switch? ", self.RespectMashFloatSwitchPump.isChecked())
#        print("Respect HLT Float Switch for Mash? ", self.RespectHLTFloatSwitchPump.isChecked())
#        print("Respect HLT Temp? ", self.RespectHLTTempSet.isChecked())
#        print("Respect HLT Float Switch for HLT? ", self.RespectHLTFloatSwitchHLT.isChecked())
#        print("Mash Tun Float Switch Position: ", self.MashFloatSwitch)
#        print("HLT Float Switch Position: ", self.HLTFloatSwitch)
#        print("==============================================")        


def main():
    app = QApplication(sys.argv)
    form = AutoBrew()
    form.show()
    timer = QBasicTimer()
    timer.start(3000, form)
    form.show()
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()
    
sys.exit()

