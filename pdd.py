#!/usr/bin/env python

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

import time
from threading import Thread
import re
import serial
import sys
from time import localtime, strftime
from collections import deque
import logging
from logging.handlers import TimedRotatingFileHandler

import database
import calcs


if sys.version_info<(3,4,2):
  sys.stderr.write("You need python 3.4.2 or later to run this script\n")
  exit(1)

log_file_name = '/home/pi/pdd/logs/pdd.log'
logging_level = logging.DEBUG
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s', "%Y-%m-%d %H:%M:%S")
handler = logging.handlers.TimedRotatingFileHandler(log_file_name,  when='midnight')
handler.suffix = '%Y_%m_%d.log'
handler.setFormatter(formatter)
logger = logging.getLogger() # or pass string to give it a name
logger.addHandler(handler)
logger.setLevel(logging_level)

# setup logging to echo .INFO and above to the stderr
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', "%Y-%m-%d %H:%M:%S")
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def CleanString (str):
    str = str.replace ("  ", " ")
    str = str.lstrip()
    return str

class InterFace(Gtk.Window):

    def on_window_destroy(self, object, data=None):
        print ("Quiting")
        Gtk.main_quit()
    
    def btnNextJob(self, object, data=None):
        print ("Next job")

    def btnPreviousJob(self, object, data=None):
        print ("Previous job")
        
    def airfield_changed(self, object, data=None):
        print ("Airfield changed")
        
        text = object.get_active_text()
        if text is not None:
            print ("Airfield selected is: %s" % text)

    def btnSendTestPage(self, object, data=None):
        
        __ser = self.InitSerialPort()        
        __message = (b'\r\nM 000000002 @@ALERT F123456789 INVL2 G&SC1 SMALL GRADD FIRE EMMA LANE INVERLOCHSVC 6962 D7 (123456) LAT/LON:-38.6313124, 145.6566964 DISP509 AIRLTV BDG374 CINVL CWOGI HEL337\r\n')
        __ser.write (__message)
        __ser.close()
        
        
    def InitSerialPort(self):
        while True:
            try:
                port = serial.Serial(
                    port='/dev/serial0',
                    baudrate = 57600,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=0.5
                )
                logging.info("Serial port initialised")
                break
            except serial.SerialException as e:
                logging.error ("Could not open /dev/serial0 yet...trying again in 5 seconds")
                time.sleep(5)       # wait 5 seconds before trying so we dont "smash" the server
        
        return port
    
    
    def process_serial(self):
        # replace this with your thread to update the text
        self.ser = self.InitSerialPort()
        parse_msg = ''
        message = ''
        while True:
            try:
                bytesToRead = self.ser.inWaiting()

                if bytesToRead > 0:
                    try:
                        ch = self.ser.read(1)
                    except serial.SerialException as e:
                        logging.error ("Failed to read from serial port")
                        pass
                    
                    #only allow printable characters
                    if (ord(ch) < 32 or ord(ch) > 126):
                       if (ord(ch) != 10 and ord(ch) != 13):
                           continue
                    
                    parse_msg += ch.decode()
                            
                    # parse message for end sequence (\r\n)
                    length = len(parse_msg)
                    if (length > 1):
                        if (parse_msg[length-2] == '\r'):
                            if (parse_msg[length-1] == '\n'):
                                # message found
                                # anything up to the \r\n is considered a valid message
                                # extract and print this message
                                message = parse_msg[:length-2]  # only keep the message, not the \r\n
                                parse_msg = ''

                                message = message.replace ('\r','')     # strip out any other \r
                                message = message.replace ('\n','')     # strip out any other \n
                                message = message[2:] #remove the "M " from the start

                                if (len(message) > 11):                  # at least the capcode and priority
                                    
                                    print ("original message is %s" % message)
                                    
                                    capcode = message[0:9]
                                    message = message[9:].lstrip()                                
                                    #print ("capcode is %s" % capcode)
                                    #print ("message is %s" % message)
                                    
                                    
                                    # is the capcode a PDD response.
                                    # if not then bug out.
                                    b_return, airfield, count = database.select ("SELECT * FROM `airfields` WHERE capcode = '%s';" % capcode)
                                    airfield = airfield[0]
                                    logger.debug ("b_return: %s" % b_return)
                                    logger.debug ("row     : %s" % airfield)
                                    logger.debug ("count   : %s" % count)
                                    
                                    if (not b_return):
                                        logger.error ('Error when trying to search for airfield')
                                    
                                    if (count > 0):
                                        b_pdd_response = True
                                    else:
                                        b_pdd_response = False
                                    
                                    if (b_pdd_response):
                                        
                                        # extract the page prority (EMERG, NON EMERG or ADMIN)
                                        priority = message[0:2]
                                        message = message[2:].lstrip()
                                        if (priority == '@@'):
                                            priority = 'EMERGENCY'
                                        if (priority == 'HB'):
                                            priority = 'NON EMERGENCY'
                                        if (priority == 'QD'):
                                            priority = 'ADMIN'
                                        
                                        print ("priority is %s" % priority)                                    
                                        print ("message is %s" % message)
                                        
                                        # show the message in the textbox
                                        GObject.idle_add(
                                            self.tbPagerMessage.set_text, message,
                                            priority=GObject.PRIORITY_DEFAULT
                                        )
                                        
                                        parseOK = True
                                        firecall = True
                                    
                                        if ((re.search("ALERT.{1,}", message) != None) and (re.search("F[0-9]{1,}", message) != None)):
                                            #logging.debug ("FIRECALL page received")
                                            #logging.info (raw)
                                            
                                            # ALERT
                                            expression = "ALERT"
                                            search_response = re.search(expression, message)      # extract ALERT
                                            if (search_response != None):
                                                alert = search_response.group(0)
                                                message = re.sub(expression, '', message)   # remove ALERT
                                                message = CleanString (message)
                                                logging.debug("Alert           :" + alert)
                                            else:
                                                logging.debug("No match for ALERT")
                                                parseOK = False
                                                firecall = False                                            
                                        
                                            # Fnumber
                                            #expression = "^F[0-9]{1,}"
                                            expression = "F[0-9]{1,9}"
                                            search_response = re.search(expression, message)      # extract Fxxxxxxxxx
                                            if (search_response != None):
                                                Fnumber = search_response.group(0)
                                                message = re.sub(expression, '', message)   # remove Fxxxxxxxxx
                                                message = CleanString (message)
                                                logging.debug("Fnumber         :" + Fnumber)
                                            else:
                                                logging.debug("No match for Fnumber")
                                                parseOK = False
                                                firecall = False


                                            # Incident type and response code
                                            expression = "\\b(ALARC1|ALARC3|STRUC1|STRUC3|INCIC1|INCIC3|NOSTC1|NOSTC3|G&SC1|G&SC3|NS&RC1|NS&RC3|RESCC1|RESCC3|CONFC1|CONFC3|HIARC1|HIARC3|STCOC1|STCOC3|TRCHC1|TRCHC3|AFEMR|AFPEMR|STRIKE)\\b"
                                            search_response = re.search(expression, message)      # extract IncidentType
                                            if (search_response != None):
                                                IncidentType = search_response.group(0)
                                                message = re.sub(expression, '', message)   # remove IncidentType
                                                message = CleanString (message)
                                                logging.debug("IncidentType    :" + IncidentType)
                                            else:
                                                logging.debug("No match for IncidentType")
                                                parseOK = False
                                                firecall = False                                        
                                        
                                                                                
                                            # Assignment Area
                                            #expression = "(^(\w+\s){1})"
                                            expression = "^(\w{1,})"
                                            search_response = re.search(expression, message)      # extract AssignmentArea
                                            if (search_response != None):
                                                AssignmentArea = search_response.group(0)
                                                message = re.sub(expression, '', message)         # remove AssignmentArea
                                                message = CleanString (message)
                                                logging.debug("AssignmentArea  :" + AssignmentArea)
                                            else:
                                                logging.debug("No match for Assignment Area")
                                                parseOK = False
                                                firecall = False
                                                
                                            # Melways
                                            expression = "M[ ]\\d{1,4}[A-Z]?[ ]\\w{1}\\d{1,2}"
                                            Map_Melways = None
                                            search_response = re.search(expression, message)      # extract Map_Melways
                                            if (search_response != None):
                                                Map_Melways = search_response.group(0)
                                                message = re.sub(expression, '', message)         # remove Map_Melways
                                                message = CleanString (message)

                                            # Map_SV
                                            expression = "SV(\w{0,})[ 0-9]{0,}\w{0,}"
                                            Map_SV = None
                                            search_response = re.search(expression, message)      # extract Map_SV
                                            if (search_response != None):
                                                Map_SV = search_response.group(0)
                                                message = re.sub(expression, '', message)         # remove Map_SV
                                                message = CleanString (message)

                                            # check the mapping
                                            MapRef = None
                                            if (Map_Melways == None and Map_SV == None):
                                                logging.debug("No match for Map ref")
                                            else:
                                                if (Map_Melways != None):
                                                    MapRef = Map_Melways
                                                else:
                                                    MapRef = Map_SV
                                                logging.debug("Map ref         :" + MapRef)
                                            
                                            expression = '(-?[0-9]{2,}.[0-9]{3,}),?\s([0-9]{2,}.[0-9]{3,})'
                                            Latitude = None
                                            Longitude = None
                                            search_response = re.search (expression, message)  # extract lat/lon
                                            if (search_response != None):
                                                LatLon = search_response.group(0)
                                                message = re.sub(expression, '', message)
                                                message = re.sub('LAT/LON:', '', message)
                                                message = CleanString (message)
                                                latitude, longitude = LatLon.split(',')
                                                latitude = latitude.strip()
                                                longitude = longitude.strip()
                                                logging.debug("Latitude        :" + latitude)
                                                logging.debug("Longitude       :" + longitude)
                                            else:
                                                logging.debug("No match for Lat/Long")
                                                parseOK = False
                                                firecall = False
                                            
                                            
                                            logging.debug ("Remaining msg   :" + message)
                                        else:
                                            logging.debug ("Not a FIRECALL")
                                            firecall = False
                                            
                                        logging.debug ("parseOK         :" + str(parseOK))
                                        logging.debug ("firecall        :" + str(firecall))
                                        
                                        if (parseOK):
                                            
                                            # populate the flight info textbox
                                            distance, bearing = calcs.get_distance_and_bearing (airfield['lat'], airfield['lng'], latitude, longitude, 'N')
                                            buffer = ("Distance : %s\nBearing : %s" % (str(distance), str(bearing)))
                                            GObject.idle_add(
                                                self.tbFlightPath.set_text, buffer,
                                                priority=GObject.PRIORITY_DEFAULT
                                            )
                                        
                                                
                                    else:
                                        print ('Not a PDD response')
                                        
                                    
                                    
                
            except serial.SerialException as e:
                pass

            
    def __init__(self):
        self.gladefile = "pdd_main.glade"
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("mainwindow")
        self.window.show()

        self.tbPagerMessage = self.builder.get_object("tbPagerMessage")
        self.tbWeather = self.builder.get_object("tbWeather")
        self.tbFlightPath = self.builder.get_object("tbFlightPath")
        self.tbClosestAirbase = self.builder.get_object("tbClosestAirbase")

        # 1. define the tread, updating your text
        self.update = Thread(target=self.process_serial)
        # 2. Deamonize the thread to make it stop with the GUI
        self.update.setDaemon(True)
        # 3. Start the thread
        self.update.start()
        
        
        self.window.queue_draw()
  

  
def run_gui():
    main = InterFace()
    # 4. this is where we call GObject.threads_init()
    GObject.threads_init()
    main.show_all()
    Gtk.main()

if __name__ == "__main__":
    run_gui()  