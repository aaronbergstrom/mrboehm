#!/usr/bin/python3
############################################################
# Project Boehm
#
# MrBoehm - a USB and Bluetooth interface for classic Atari
#           gaming consoles.
#
# Supported Consoles:
# - Atari 2600 VCS
# - Atari 5200F
# - Atari 7800
#
# This project is dedicated to my middle school physics
# teacher, Mr. Boehm, who taught me, and many other kids,
# about electric circuits.
#
# L.E. Berger Middle School (now Elementry School)
# West Fargo Public Schools
#
# Authors: Aaron Bergstrom - L.E Berger Alum: 1982-1985
#          David Krause
############################################################

from gpiozero import Button
from gpiozero import PWMLED
from time import sleep
#from xbox360controller import Xbox360Controller

import evdev
from evdev import InputDevice, categorize, ecodes

import os
from os import path
import sys
import subprocess
import asyncio
import smbus
import json
import copy
import math

#from RPLCD.i2c import CharLCD

#lcd = CharLCD(i2c_expander='PCF8574',address=0x27, cols=16, rows=2)
#lcd.backlight_enabled = True

"""usb_bl_devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

for device in usb_bl_devices:
    print(device.path, device.name, device.phys)
    print(device.capabilities(verbose=True))"""

#exit()

#Button used to initiate the controller paring process
pairButton = Button(23)

#Button in place for debugging. Keeps the program
#from ending during testing. Pin will be resassinged
#before release.
killButton = Button(24)

#[0] - Blue - Controller 1 Status
#[1] - Blue - Controller 2 Status
#[2] - Blue - Controller 3 Status
#[3] - Blue - Controller 4 Status
#ledGrp = [PWMLED(6), PWMLED(13), PWMLED(19), PWMLED(26)]
ledGrp = [PWMLED(17)]

#LEDs used to indicate activity and pairing status
#Red - Activity
ledAct = PWMLED(27)

#Variable that prevents the pairing button from executing
#the contents of the pairing function while the pairing is
#taking place.
isPairing = False
isProceeding = False

remainActive = True

#This will store the controller information after pairing. This
#items stored in this list will likely of the class 'Controller'.
#Durring initial development, this is likely to begin as a string
#and change over time into the class.
#cjs = []

#This second list is used to reorder BLE controllers when users
#want to change which controller is tied to which Atari port
#or classic Atari controller.
#scjs = []

ctypes1 = []
ctypes2 = []

xbox360pads  = ""
xboxwireless = ""
xboxonepads  = ""
logitechdual = ""

btrules = ['ACTION=="add", SUBSYSTEM=="input", ATTRS{uniq}=="',#0
           '", ENV{DEVNAME}=="/dev/input/event*", SYMLINK+="input/boehm_',#1
           '", RUN+="/bin/systemctl --no-block start gamepads@boehm_',#2
           '.service"\n',#3
           'ACTION=="remove", SUBSYSTEM=="input", ATTRS{uniq}=="',#4
           '", RUN+="/home/pi/gamepads.sh gamepadDisconnect boehm_',#5
           '"\n']#6
#xx:xx:xx:xx:xx:xx
#xxxxxxxxxxxx
#xxxxxxxxxxxx
#xx:xx:xx:xx:xx:xx
#xxxxxxxxxxxx

#xbox one s wireless
xboxwp1  = "sudo xboxdrv --evdev "
xboxwp2  = " --silent --detach-kernel-driver --force-feedback --deadzone-trigger 15% --deadzone 4000"
xboxwp2 += " --calibration x1=0:32767:65535,y1=0:32767:65535,x2=0:32767:65535,y2=0:32767:65535"
xboxwp2 += " --trigger-as-button --mimic-xpad --four-way-restrictor"
xboxwp2 += " --evdev-absmap ABS_X=x1,ABS_Y=y1,ABS_Z=x2,ABS_RZ=y2,ABS_BRAKE=lt,ABS_GAS=rt,ABS_HAT0X=dpad_x,ABS_HAT0Y=dpad_y"
xboxwp2 += " --evdev-keymap BTN_SOUTH=a,BTN_EAST=b,BTN_NORTH=x,BTN_WEST=y,BTN_TL=lb,BTN_TR=rb,BTN_THUMBL=tl,BTN_THUMBR=tr,BTN_MODE=guide,BTN_BACK=back,BTN_START=start &"

xboxwire = 0
ctypes1.append(xboxwp1)
ctypes2.append(xboxwp2)

xbox1p1  = "sudo xboxdrv --evdev "
xbox1p2  = " --silent --detach-kernel-driver --force-feedback --deadzone-trigger 15% --deadzone 4000"
xbox1p2 += " --calibration x1=0:32767:65535,y1=0:32767:65535,x2=0:32767:65535,y2=0:32767:65535"
xbox1p2 += " --trigger-as-button --mimic-xpad --four-way-restrictor"
xbox1p2 += " --evdev-absmap ABS_X=x1,ABS_Y=y1,ABS_Z=x2,ABS_RZ=y2,ABS_BRAKE=lt,ABS_GAS=rt,ABS_HAT0X=dpad_x,ABS_HAT0Y=dpad_y"
xbox1p2 += " --evdev-keymap BTN_SOUTH=a,BTN_EAST=b,BTN_NORTH=x,BTN_WEST=y,BTN_TL=lb,BTN_TR=rb,BTN_THUMBL=tl,BTN_THUMBR=tr,BTN_MODE=guide,BTN_BACK=back,BTN_START=start &"

xboxones = 1
ctypes1.append(xbox1p1)
ctypes2.append(xbox1p2)

logi1p1  = "sudo xboxdrv --evdev "
logi1p2  = " --silent --detach-kernel-driver --deadzone 16"
logi1p2 += " --calibration x1=0:127:255,y1=0:127:255,x2=0:127:255,y2=0:127:255"
logi1p2 += " --mimic-xpad --four-way-restrictor"
logi1p2 += " --evdev-absmap ABS_X=x1,ABS_Y=y1,ABS_Z=x2,ABS_RZ=y2,ABS_HAT0X=dpad_x,ABS_HAT0Y=dpad_y"
logi1p2 += " --evdev-keymap BTN_THUMB=a,BTN_THUMB2=b,BTN_TRIGGER=x,BTN_TOP=y,BTN_TOP2=lb,BTN_PINKIE=rb,BTN_BASE=lt,BTN_BASE2=rt,BTN_BASE5=tl,BTN_BASE6=tr,BTN_BASE3=back,BTN_BASE4=start &"

logitechd = 2
ctypes1.append(logi1p1)
ctypes2.append(logi1p2)

bus=smbus.SMBus(1)
#bus.write_byte_data(address,0x04,action)
#bus.write_byte_data(0x2C,0x80,floorOne)

#mplex is multiplexer address with A0, A1, and A2 not grounded
mplex = 0x70
    
# The ports array holds the address of multiplexer port channels
#       SD/SC0, SD/SC1, SD/SC2, SD/SC3
#ports=[0x01,0x02,0x04,0x08]
#       SD/SC0, SD/SC1
ports=[0x01,0x02]
#ports=[0x01]

#digipot is digtal pot smb address
digipot = 0x2C

#potaxis list are addresses of pot 0 and 1 on the
#same controller
potaxis = [0x80,0x00]

#schips are the first 3 of 4 715 chip addresses
#s_chips = [0x48,0x49,0x4A]
s_chips = [0x48,0x49,0x4A,0x4B]

dac_chips = [0x48,0x49]
dac_pins = [0x08,0x09,0x0A,0x0B,0x0C,0x0D,0x0E,0x0F]

players = []
conSupport = None

#Runs through light function for testing purposes
def showLights():
    global isPairing
    if isPairing == False:
        isPairing = True
        
        ledAct.on()
        
        for led in ledGrp:
            led.on()
        sleep(3)
        
        ledAct.off()
        sleep(1)
        for led in ledGrp:
            sleep(1)
            led.off()

        isPairing = False
        
gameControllers = []
deviceTasks = []
playerNum   = []
keyboards   = []

devices = None


async def monitorKDevice(device):
    global remainActive
#    device = c.getDevice()
    print("Monitoring Started:",device.path)
    #lloop = device.async_read_loop()
    async for event in device.async_read_loop():
        if event.type == ecodes.EV_KEY:
            if event.code == 107 and event.value == 0:
                remainActive = False
                print("Exiting Program")
            elif event.code == 1 and event.value == 0:
                print("Pairing")
                requestPairing()
            else:
#                asyncio.ensure_future(c.processEvent(event))
                pass


# c is a GameController object
async def monitorController(c):
#async def monitorController(device):
    device = c.getDevice()
    print("Monitoring Started:",device.path)
    async for event in device.async_read_loop():
        strVal = str(event.code)
        if strVal in c.events["elist"] and (event.type == ecodes.EV_ABS or event.type == ecodes.EV_KEY):
            print(strVal)
            evInfo = c.events[strVal]
            if evInfo["chip"][0] == "stv":
                if event.value == 1:
    #                c.setState(4)
                    c.state = 4
                elif event.value == -1:
    #                c.setState(2)
                    c.state = 2
                elif event.value == 0:
    #                c.setState(0)
                    c.state = 0
                else:
                    pass
            elif evInfo["chip"][0] == "sth":
                if event.value == 1:
    #                c.setState(1)
                    c.state = 1
                elif event.value == -1:
    #                c.setState(3)
                    c.state = 3
                elif event.value == 0:
    #                c.setState(0)
                    c.state = 0
                else:
                    pass
            else:
                pass

#            print("Other:",evInfo["chip"][0])



class GameController:
    
    def __init__(self, player, device, conSupport, bus):
        self.player = player
        self.device = device
        self.conSupport = None
        self.isMonitored = False
        self.gamepad = None
        self.template = None
        self.events = None
        self.pots = None
        self.addresses = None
        self.bus = bus
        self.state = 0
        self.lock = [False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False]
        self.updateConSupport(conSupport)
        self.tasks = [asyncio.ensure_future(self.processEvent())]
        print("Created:", self.device.name)

#        async for event in device.async_read_loop():

        
    def setPlayer(self, player):
        self.player = player

    def getPlayer(self):
        return self.player
    
    def getDevice(self):
        return self.device
    
    def setMonitored(self):
        self.isMonitored = True
    
    def setUnmonitored(self):
        self.isMonitored = False
        
    def getMonitored(self):
        return self.isMonitored
    
    def getEvInfo(self, evStr):
        return self.events[evStr]
    
    def setState(self, state):
        self.state = state
        
    def getState(self):
        return self.state
    
    def getAddresses(self, chip):
        return self.addresses[chip]
    
#    async def dacChipsUpdate(self):
#    async def tcaChipUpdate(self):
    
    async def buttonUpdate(self, port, chip, byte):
        self.bus.write_byte(0x70, port)
        self.bus.write_byte(chip,byte)

    async def hatUpdate(self, port, chip, byte, chip1, byte1):
        self.bus.write_byte(0x70, port)
        self.bus.write_byte(chip,byte)
        self.bus.write_byte(chip1,byte1)

    async def potUpdate(self, port, chipVal, data):
        self.bus.write_byte(0x70, port)
        self.bus.write_byte_data(chipVal[0],chipVal[1],data)

    async def pollPentometers(self):
        while True:
            if self.lock[((self.player-1) * 4)]:
                for pot in self.pots:
                    self.bus.write_byte(0x70,self.pots[pot][0])
                    cVal = self.bus.read_byte_data(0x2c,self.pots[pot][1])
                    if cVal > 79:
                        cVal = 79
                    elif cVal <= 0:
                        cVal = 0

                    if self.pots[pot][2] != 0:
                        if self.pots[pot][2] == -1 and cVal < 79:
                            cVal += 1
                        elif self.pots[pot][2] == 1 and cVal > 0:
                            cVal -= 1
                            
                        await self.potUpdate(self.pots[pot][0],[0x2c,self.pots[pot][1]], cVal)
                        
            await asyncio.sleep(0.0333)

############
#EVINFO JSON
############
#{
#    "17":
#        {
#            "bus":0,
#            "inputs": [
#                {
#                    "chip": 27,
#                    "pin": 1
#                },
#                {
#                    "chip": 27,
#                    "pin": 2
#                }
#            ],
#            "actiontype": 1,
#            "dzone":80,
#            "mod":255
#        },
#    "208":
#        {
#            "bus": 0,
#            "inputs": [
#                {
#                    "chip": 27,
#                    "pin": 1
#                },
#                {
#                    "chip": 27,
#                    "pin": 2
#                }
#            ],
#            "actiontype": 1,
#            "dzone":80,
#            "mod":255
#        },
#    "elist":"-17--208-"
#}
#
#actionType:
#    Button 0
#    Hat 1
#    Pot 2

    async def processEvent(self):
        print("pE")
        async for event in self.device.async_read_loop():
            print("Pe2")
            if self.bus != None and (event.type == ecodes.EV_ABS or event.type == ecodes.EV_KEY):
                ### Not sure what self.events["elist"] does
                checkCode = "-"+str(event.code)+"-"
                if checkCode in self.events["elist"]:
                    evInfo = self.events[str(event.code)]
                    print(evInfo)

                    #Set the multiplexer to the correct channel
                    tbus = evInfo["bus"]
                    print("1")
                    self.bus.write_byte(0x70, tbus)
                    print("2")
                    
                    actionType = evInfo["actiontype"]
                    print("3")
                    if actionType == 0:
                        print("4")
                        uPort = 0x06
                        print("5")
                        cIdx = 0
                        print("6")
                        pin = evInfo["inputs"][0]["pin"]
                        print("7")
                        pBit = 1
                        print("8")
                        
                        print("Event Code: " + event.code + ", Event Value: " + event.value+". Button Action Type Called.\n")
                        
                        if pin > 8:
                            print("9")
                            uPort = 0x07
                            print("10")
                            pin = pin-8
                            print("11")
                            cIdx = 1
                            print("12")
                        pBit = pBit << (pin-1)
                        print("13")
                        
                        pCur = self.bus.read_i2c_block_data(gpioc, uPort, 2)
                        print("14")
                        if event.value == 1:
                            print("15")
                            # Change the read from the GPIO pin so that the pin is set to
                            # to input once the byte has been written back to the GPIO
                            pCur[cIdx] = pCur[cIdx] | pBit
                            print("16")
                        else:
                            # Change the read from the GPIO pin so that the pin is set to
                            # to output once the byte has been written back to the GPIO
                            print("17")
                            pCur[cIdx] = pCur[cIdx] ^ pBit
                            print("18")
                        print("19")
                        self.bus.write_i2c_block_data(gpioc, uPort, pCur)
                        print("20")
                else:
                    print("Event Code: " + str(event.code) + ", Event Value: " + str(event.value) + ", not found in elist.\n")
            else:
                
                print("Event Type: " + str(event.type) + ".\n")
                if self.bus == None:
                    print("No bus found.\n")

#                        chipVal = None
#                        if len(evInfo["chip"]) > 2:
#                            chipVal = self.addresses[evInfo["chip"][self.state]]
#                        else:
#                            chipVal = self.addresses[evInfo["chip"][0]]
                            
#                        modifier = evInfo["mod"]
#                        cType = evInfo["type"]
#                        dZone = evInfo["dzone"]

#######################
# Old Code
#######################

#    async def processEvent(self):
#        async for event in self.device.async_read_loop():
#            if self.bus != None and (event.type == ecodes.EV_ABS or event.type == ecodes.EV_KEY):
#                checkCode = "-"+str(event.code)+"-"
#                if checkCode in self.events["elist"]:
#                    evInfo = self.events[str(event.code)]
#                    if evInfo["chip"][0] == "stv": #Stick Vertical
#                        if event.value == 1:
#                            self.state = 4
#                        elif event.value == -1:
#                            self.state = 2
#                        elif event.value == 0:
#                            self.state = 0
#
#                    elif evInfo["chip"][0] == "sth": #Stick Horizontal
#                        if event.value == 1:
#                            self.state = 3
#                        elif event.value == -1:
#                            self.state = 1
#                        elif event.value == 0:
#                            self.state = 0
#                    elif evInfo["chip"][0] == "lk0":
#                        if event.value == 0:
#                            if self.lock[(self.player-1) * 4] == False:
#                                self.lock[(self.player-1) * 4] = True
#                            else:
#                                self.lock[(self.player-1) * 4] = False
#                    elif evInfo["chip"][0] == "lk1":
#                        if event.value == 0:
#                            if self.lock[((self.player-1) * 4) + 1] == False:
#                                self.lock[((self.player-1) * 4) + 1] = True
#                            else:
#                                self.lock[((self.player-1) * 4) + 1] = False
#                    elif evInfo["chip"][0] == "lk2":
#                        if event.value == 0:
#                            if self.lock[((self.player-1) * 4) + 2] == False:
#                                self.lock[((self.player-1) * 4) + 2] = True
#                            else:
#                                self.lock[((self.player-1) * 4) + 2] = False
#                    elif evInfo["chip"][0] == "lk3":
#                        if event.value == 0:
#                            if self.lock[((self.player-1) * 4) + 3] == False:
#                                self.lock[((self.player-1) * 4) + 3] = True
#                            else:
#                                self.lock[((self.player-1) * 4) + 3] = False
#                    else:
#                        tbus = evInfo["bus"]
#                        self.bus.write_byte(0x70, tbus)
#                        chipVal = None
#                        if len(evInfo["chip"]) > 2:
#                            chipVal = self.addresses[evInfo["chip"][self.state]]
#                        else:
#                            chipVal = self.addresses[evInfo["chip"][0]]
#                            
#                        modifier = evInfo["mod"]
#                        cType = evInfo["type"]
#                        dZone = evInfo["dzone"]
#
#                        mvalue = event.value
#                        #button 0
#                        if cType  == 0:
#                            if modifier > 1:
#                                if mvalue < 20:
#                                    mvalue = 0
#                                else:
#                                    mvalue = 1
#                            reg = self.bus.read_byte(chipVal[0])
#                            tReg = chipVal[1]
#                            if mvalue == 0:
#                                tReg = ~chipVal[1]
#                                reg = reg & tReg
#                            else:
#                                reg = reg | tReg
#                            await self.buttonUpdate(tbus, chipVal[0], reg)
#                        elif cType == 1:
#                            chipVal1 = self.addresses[evInfo["chip"][1]]
#                            if modifier != 1:
#                                mvalue = mvalue - (modifier/2)
#                                if mvalue < (-1*dZone):
#                                    mvalue = -1
#                                elif mvalue > dZone:
#                                    mvalue = 1
#                                else:
#                                    mvalue = 0
#                            reg  = self.bus.read_byte(chipVal[0])
#                            reg1 = self.bus.read_byte(chipVal1[0])
#                            if mvalue == -1:
#                                reg  =  reg |  chipVal[1]
#                                reg1 = reg1 & ~chipVal1[1]
#                                await self.hatUpdate(tbus, chipVal[0], reg, chipVal1[0], reg1)
#                            elif mvalue == 1:
#                                reg  =  reg & ~chipVal[1]
#                                reg1 = reg1 | chipVal1[1]
#                                await self.hatUpdate(tbus, chipVal[0], reg, chipVal1[0], reg1)
#                            else:
#                                reg  =  reg & ~chipVal[1]
#                                reg1 = reg1 & ~chipVal1[1]
#                                await self.hatUpdate(tbus, chipVal[0], reg, chipVal1[0], reg1)
#                        #pot    2
#                        else:
#                            nvalue = int(round(mvalue * 255/modifier))
#                            idx = str(tbus)+"-"+str(chipVal[1])
#                            pIndex = self.addresses[idx]
#                            if self.lock[((self.player-1) * 4) + 1] == False:
#                                nvalue = 255 - nvalue
#                            if self.lock[((self.player-1) * 4)]:
#                                if nvalue < 120:
#                                    self.pots[idx][2] = 1
#                                elif nvalue > 132:
#                                    self.pots[idx][2] = -1
#                                else:
#                                    self.pots[idx][2] = 0
#                            else:
#                                if nvalue < 88:
#                                    nvalue = 88
#                                elif nvalue > 167:
#                                    nvalue = 167
#                                nvalue = nvalue-88
#                                await self.potUpdate(tbus, chipVal, nvalue)
        
    def updateConSupport(self, conSupport):
        if conSupport != None:
            self.conSupport = conSupport
            self.setTemplate()
        
    def setTemplate(self):
        for gamepad in self.conSupport["gamepads"]:
            if self.device.info.vendor == gamepad["vendor"] and self.device.info.product == gamepad["product"] and self.device.info.version == gamepad["version"]:
                self.gamepad = gamepad
#                print("Game Pad Found")
#            else:
#                print("Info Vendor:", self.device.info.vendor, "Gamepad Vendor:", gamepad["vendor"])
#                print("Info Product:", self.device.info.product, "Gamepad Vendor:", gamepad["product"])
#                print("Info Version:", self.device.info.version, "Gamepad Vendor:", gamepad["version"])
        for console in self.conSupport["consoles"]:
            if self.conSupport["default"]["console"] == console["name"]:
                self.addresses = console["addresses"]
                self.template = console["templates"][self.conSupport["default"]["template"]]

#        for defs in self.template["defaults"]:
#            bus.write_byte(0x70, defs["bus"])
#            bus.write_byte_data(defs["chip"], defs["addr"], defs["data"])

#        tPot = "{"
        eventSet = "{"
        eventList = ""
        for event in self.gamepad["events"]:
            for port in self.template["ports"]:
                for pevent in port["events"]:
                    if self.player == pevent["player"]:
                        nIndex = pevent["index"][self.gamepad["full"]]
                        if event["index"] == nIndex:
                            ####Check for Pot###
                            #if pevent["itemType"] == 2:
                            #    gAddr = self.addresses[pevent["inputs"][0]]
                            #    nPot = '"' + str(port["busAddr"]) + '-' + str(gAddr[1]) + '": ['
                            #    nPot += str(port["busAddr"]) + ',' + str(gAddr[1]) + ',0],'
                            #    tPot += nPot
                            eventList += "-"
                            eventList += str(nIndex)
                            eventList += "-"
                            eventItem = '"' + str(nIndex) + '": {"bus": ' + str(port["busAddr"]) + ','
                            eventItem += '"inputs": ['
                            for inp in pevent["inputs"]:
                                gAddr = self.addresses[inp]
                                eventItem += '{"chip": ' + str(gAddr[0]) + ',"pin": ' + str(gAddr[1]) + '},'
                            eventItem = eventItem[:len(eventItem)-1]
                            eventItem +='],"actiontype": ' + str(pevent["itemType"]) + ',"dzone": ' + str(int(pevent["dzone"] * event["minmax"][1])) + ',"mod": ' + str(event["minmax"][1]) + '},'
                            eventSet += eventItem
#                        else:
#                            print("EI:", event["index"],"PEI:", nIndex)
#        eventSet = eventSet[:len(eventSet)-1]
#        if len(tPot) > 1:
#            tPot = tPot[:len(tPot)-1]
#            tPot += "}"
#            print(tPot)
#            self.pots = json.loads(tPot)
#        else:
#            self.pots = None
        self.pots = None
        eventSet += '"elist": "'
        eventSet += eventList
        eventSet += '"}'
#        eventSet += "}"
        print(eventSet)

        self.events = json.loads(eventSet)
#        await asyncio.sleep(0.001)

#async def monitorKeyboard(keyboard):
#    async for event in keyboard.async_read_loop():
#        if event.type == ecodes.EV_KEY:
#            print(device.path, "Did something with a keyboard.", event.code)

def resetControllerChips():
    global ports
    global mplex
    global digipot
    global potaxis
    global s_chips

    for port in ports:
        #Change to appropriate multiplex channel based
        #on port.
        bus.write_byte(mplex, port)
        print("action port run")
        print(port)
        #Set both digi pot values to '0'
        for axis in potaxis:
            bus.write_byte_data(digipot,axis,255)
        
        #For all 715 chips, open all switches
        for c in s_chips:
            bus.write_byte(c,0b00000000)
            

def setFor5200():
    resetControllerChips()
    bus.write_byte(pmBk[0],pmBk[1])

def set2600and7800Type(side, cType):
    global ports
    global mplex

    bus.write_byte(mplex,ports[side])    

    if cType   == "JS":
        bus.write_byte(jsBk[0],jsBk[1])
    elif cType == "PD":
        bus.write_byte(pdBk[0],pdBk[1])
    elif cType == "KP":
        bus.write_byte(kpBk[0],kpBk[1])
    elif cType == "TB":
        bus.write_byte(jsBk[0],jsBk[0])
    elif cType == "ST":
        bus.write_byte(pdBk[0],pdBk[1])
    else:
        pass

def setFor2600and7800(lType, rType):
    resetControllerChips()

    set2600and7800Type(0,lType)
    set2600and7800Type(1,rType)
    
    
def setScanOff():
    stdDump = subprocess.check_output("ps -ef | grep 'bluetoothctl scan on' | grep -v grep", shell=True).decode('utf-8')
    btcscans = stdDump.splitlines()
    for line in btcscans:
        lparts = line.strip().split()
        print("LPARTS:",lparts[1])
        killpid = "kill " + lparts[1]
        subprocess.call(killpid, shell=True)

#    subprocess.call("bluetoothctl pairable off", shell=True)
    subprocess.call("bluetoothctl discoverable off", shell=True)

def setScanOn():
    subprocess.call("bluetoothctl discoverable on", shell=True)
    subprocess.call("bluetoothctl pairable on", shell=True)
    subprocess.call("bluetoothctl scan on &", shell=True)
    
    #Eventually break this up into multiple 1 sec sleeps
    #with blinky led action
    sleep(5)
    
def disconnectControllers():
    global gameControllers
    global deviceTasks
    
    for t in deviceTasks:
        t.cancel()

    gameControllers.clear()

    #Turn off main activity LED
    ledAct.off()
        
    #Turn off blue controller LEDs
    for led in ledGrp:
        led.off()
        
def controllerSetup():
    global gameControllers
    global devices
    
    disconnectControllers()
    sleep(1)
    
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

    i = 0
    for device in devices:
        if "Xbox Wireless Controller" in device.name:
            print(device.name)
            gameControllers.append(GameController(i, device))
            i += 1
        elif "X-Box One S" in device.name and device.path not in xboxonepads:
            print(device.name)
            gameControllers.append(GameController(i, device))
            i += 1
        elif "Logitech Dual" in device.name and device.path not in logitechdual:
            print(device.name)
            gameControllers.append(GameController(i, device))
            i += 1

#async def pairingControllers():
def pairingControllers():
    global isPairing
    
    ledAct.on()
    ledAct.pulse(0.5,0.5)
    subprocess.call("bluetoothctl show", shell=True)
    
    sleep(2)
    
    for led in ledGrp:
        led.on()
        sleep(2)

    ledAct.pulse(0.1,0.1)
    for led in ledGrp:
        led.off()
    
    deviceString = subprocess.check_output("bluetoothctl devices", shell=True).decode('utf-8')
    print("DString:")
    print(deviceString)

    pDeviceString = subprocess.check_output("bluetoothctl paired-devices", shell=True).decode('utf-8')
    print("PString:")
    print(pDeviceString)
    
    deviceLines = deviceString.splitlines()
    pDeviceLines = pDeviceString.splitlines()
    
    pControllers = ""
    for line in pDeviceLines:
        if "Xbox Wireless Controller" in line:
            line = line.strip()
            lParts = line.split()
            pControllers = pControllers + lParts[1] + " "
    pControllers = pControllers.strip()
            
    wControllers = []
    for line in deviceLines:
        if "Xbox Wireless Controller" in line:
            line = line.strip()
            lParts = line.split()
            if lParts[1] in pControllers:
                try:
                    details = subprocess.check_output("bluetoothctl connect "+ lParts[1], shell=True).decode('utf-8')
                    if "org.bluez.Error.Failed" not in details:
                        print(lParts[1], "is already paired.")
                except:
                    print("Controller does not appear to be on.")
                    pass
            else:
                wControllers.append(lParts[1])
                
    nLed = 1
    for mac in wControllers:
        print("Iter:", nLed)
        try:
            fParts = mac.lower()
            label = fParts.replace(':','')
            if path.exists("/dev/input/boehm_" + label) == False:
                f=open("/etc/udev/rules.d/99-bluetooth.rules", "a+")
                
                #/etc/udev/rules.d/99-bluetooth.rules
                rule = btrules[0] + fParts + btrules[1] + label + btrules[2] + label + btrules[3] + btrules[4] + fParts + btrules[5] + label + btrules[6]
                f.write(rule)
                f.close()
                #sed 's/vermin/pony/g' metamorphosis.txt > ponymorphosis.txt
                tofile = "/home/pi/boehm/controllers/boehm_" + label + ".sh"
                frfile = "/home/pi/boehm/controllers/boehm_default.sh"
                
                subprocess.call("sed 's/default/" + label + "/g' " + frfile + " > " + tofile, shell=True)
#            sleep(1)
#            subprocess.call("bluetoothctl connect "+ mac, shell=True)
#            sleep(1)
            subprocess.call("bluetoothctl trust "+ mac, shell=True)
            sleep(1)
#            subprocess.call("bluetoothctl disconnect "+ mac, shell=True)
#            sleep(2)
            subprocess.call("bluetoothctl connect "+ mac, shell=True)
            sleep(1)

            subprocess.call("bluetoothctl pair "+ mac, shell=True)
            sleep(2)
#            subprocess.call("bluetoothctl trust "+ mac, shell=True)
#            sleep(1)
#            subprocess.call("bluetoothctl connect "+ mac, shell=True)
#            sleep(1)
            nLed += 1
        except Exception as EX:
            print(EX)
            print("Ignore It and Proceed")
            

    ledAct.on()

    sleep(2)
    
    #establishMonitoring()

    isPairing = False


#For testing purposes, this assigns the
#'showLights' function as the pairButton's
#callback function
####### pairButton.when_pressed = showLights

def printme():
    print("Me")

def killprog():
    global remainActive
    remainActive = False
    
def requestPairing():
    global isPairing
    if isPairing == False:
        isPairing = True
        setScanOn()
        print("Initiated Pairing")
#        loop = asyncio.get_event_loop()
#        loop.run_until_complete(pairingControllers())
        pairingControllers()
        setScanOff()

pairButton.when_pressed = requestPairing
killButton.when_pressed = killprog

def monitorGamepads():
    global gameControllers
    global deviceTasks
    global isPairing
    global conSupport
    
    if isPairing == False:

        supported = conSupport["gamepads"]
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        unmonitored = []
        subdevices  = []
        
        for gamepad in supported:
            for device in devices:
                if gamepad["name"] in device.name and gamepad["exclude"] not in device.name:
                    subdevices.append(device)
#                    print(device.name, "found")
#                else:
#                    print(device.name, "not found")
        
        gdpaths = ""
        for gc in gameControllers:
            gdpaths += gc.getDevice().path
        
        for device in subdevices:
            if device.path not in gdpaths:
                unmonitored.append(device)
            
        for device in unmonitored:
            i = len(gameControllers)+1
            gc = GameController(i, device, conSupport, bus)
            gc.setMonitored()
            
            gameControllers.append(gc)
#            deviceTasks.append(asyncio.ensure_future(monitorController(gc)))

def monitorKeyboards():
    global gameControllers
    global deviceTasks
    global isPairing
    
    if isPairing == False:
        unmonitored = []
        subdevices  = []

        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        devices.reverse()
        
        lastName = ""
        for device in devices:
            if "Keyboard" in device.name and device.name != lastName:
                subdevices.append(device)
                lastName = device.name
        
        gdpaths = ""
        for gc in gameControllers:
            gdpaths += gc.getDevice().path
        
        for device in subdevices:
            if device.path not in gdpaths:
                unmonitored.append(device)
            
        for device in unmonitored:
#            gc = GameController(6, device, None, None)
#            gc.setMonitored()
            
#            gameControllers.append(gc)
#            deviceTasks.append(asyncio.ensure_future(monitorController(gc)))
            deviceTasks.append(asyncio.ensure_future(monitorKDevice(device)))

def establishMonitoring():
    global gameControllers
    global deviceTasks
    global isPairing
    
    if isPairing == False:

        unmonitored = []

        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        
        subdevices  = []
        for device in devices:
            if "Logitech Dual" in device.name or ("Xbox Wireless Controller" in device.name and "Consumer" not in device.name) or "Keyboard" in device.name:
                subdevices.append(device)
        
        gdpaths = ""
        for gc in gameControllers:
            gdpaths += gc.getDevice().path
        
        for device in subdevices:
            if device.path not in gdpaths:
                unmonitored.append(device)
            
        for device in unmonitored:
            i = len(gameControllers)-1
            if "Keyboard" in device.name:
                i = 6
            gc = GameController(i, device)
            gc.setMonitored()
            
            gameControllers.append(gc)
#            deviceTasks.append(asyncio.ensure_future(monitorController(gc)))

#async def checkForNewMonitoring():
def checkForNewMonitoring():
#    global remainActive
    global gameControllers
    global deviceTasks
    
    if len(gameControllers) < 4:
        for gc in gameControllers:
            if gc.getMonitored() == False:
                gc.setMonitored()
#                deviceTasks.append(asyncio.ensure_future(monitorController(gc)))
                
#    while remainActive:
#        for gc in gameControllers:
#            if gc.getMonitored() == False:
#                gc.setMonitored()
#                deviceTasks.append(asyncio.ensure_future(monitorController(gc)))
#        await asyncio.sleep(2)

#Just making sure that all paired deviced, don't care what type, are connected.
def attemptStartupPairing():
    global isPairing
    
    if isPairing == False:
        isPairing = True
        #Getting List of Paired and/or Trusted Devices
        deviceString = subprocess.check_output("bluetoothctl devices", shell=True).decode('utf-8')
        
        #Cutting list of devices into string list items
        lines = deviceString.splitlines()
        
        #Making an attempt to connect to each item listed
        for line in lines:
            if "Xbox Wireless Controller" in line:
                lParts = line.split()
                try:
                    details = subprocess.check_output("bluetoothctl connect "+ lParts[1], shell=True).decode('utf-8')
                    if "org.bluez.Error.Failed" not in details:
                        print(lParts[1], "is paired.")
                except:
                    print("Controller does not appear to be on.")
                    pass
        
        sleep(1)
        isPairing = False

async def waitToEnd():
    global remainActive
    
    while remainActive:
#        establishMonitoring()
        pass
        await asyncio.sleep(5)

def setTemplateDefaults():
    global conSupport
#    global lcd
#    i = 0
    for console in conSupport["consoles"]:
        if console["name"] == conSupport["default"]["console"]:
            template = console["templates"][conSupport["default"]["template"]]
#            lcd.write_string(template["name"])
            print(template["name"])
#            for defs in template["defaults"]:
#                bus.write_byte(0x70, defs["bus"])
#                bus.write_byte_data(defs["chip"], defs["addr"], defs["data"])
#                print("Pot Read:", bus.read_byte_data(defs["chip"], defs["addr"]))
#                i += 1
            for defBus in template["defaults"]:
                #Changing multiplexer to console port
                bus.write_byte(0x70, defBus["bus"])
                #Setting the default values for the 2 DAC chips and the GPIO chip
                #
                # GPIO - i2c address - 0x27
                
                ###########################################################
                # DAC Info:
                # dec=199 #set this value between 0 and 255
                # qt=int(hex(dec//16),0) # Requires the Floor Division operator "//"
                # rm=int(hex((dec%16)*16),0)
                # After looking at it closer you can probably just use:
                # qt=dec//16
                # rm=(dec%16)*16
                ###########################################################
                # DAC1 - i2c address - 0x48 - 72 in decimal
                # DAC2 - i2c address - 0x49 - 73 in decimal
                #####################################################
                # JDAC - Joint DAC Address for simultaneous updates #
                #####################################################
                # JDAC - i2c address - 0x47 - 71 in decimal
                
                # Turn off power to all DAC Chips:
                jdac = 71
                # Because we are changing controller types, the first thing we
                # want to do is disenagage power output of the DAC so that we
                # don't damage the console.
                bus.write_i2c_block_data(jdac,0x01,[0xFF,0xFF])
                
                for chip in defBus["chips"]:
                    if chip["type"] == "DAC":
                        #Set the voltage of each pin on this DAC to zero.
                        i=0
                        for pin in dac_pins:
                            qt = chip["volt"][i] // 16
                            rm = (chip["volt"][i] % 16 * 16)
                            bus.write_i2c_block_data(chip["addr"],pin,[qt,rm])
                            i = i+1
                            
                    elif chip["type"] == "GPIO":
                        #GPIO chip
                        #Set Ports 0 (pins 4-11) and 1 (pins 13-20) to 0 voltz
                        gpioc = chip["addr"]
                        bus.write_i2c_block_data(gpioc, 0x02, [0x00,0x00])
#                       bus.write_i2c_block_data(gpioc, 0x03, [0x00,0x00])
                        
                        #Set Ports 0 and 1 to output
                        bus.write_i2c_block_data(gpioc, 0x06, [0x00,0x00])
#                        bus.write_i2c_block_data(gpioc, 0x07, [0x00,0x00])
                        
                #Turn the power output for this dac backon.        
                bus.write_i2c_block_data(jdac,0x01,[0x00,0x00])
                
#################################################################################
#               Old code for first iteration of the project.
#               No longer relevant
#################################################################################
#                bus.write_byte(0x4B, port["bkSwitches"])

def loadGamepadSupport():
    global conSupport
    print("Loading Gamepad Support")
    with open("settings.json","r") as rfile:
        conSupport = json.load(rfile)
        setTemplateDefaults()

#Main Method
def main():
#    global lcd
    print("Main")
#########    setFor2600and7800("JS","JS")
#########    attemptStartupPairing()
#    establishMonitoring()
    
    loadGamepadSupport()
    monitorGamepads()
    monitorKeyboards()
    
    
    #Wait for kill switch to be pressed
    #killButton.wait_for_press()
    
    #Run Loop that checks for new monitoring
    #asyncio.ensure_future(checkForNewMonitoring())
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(waitToEnd())
        
    disconnectControllers()
    bus.write_byte(mplex, 0x00)
    print("Done")
#    lcd.clear()
#    lcd.backlight_enabled = False
    

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        
        #Shutdown and background bluetoothctl threads
        setScanOff()

        #Attempt to exit nicely
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)