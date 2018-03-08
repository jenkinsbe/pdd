#!/usr/bin/env python

import sys
if sys.version_info<(3,4,2):
  sys.stderr.write("You need python 3.4.2 or later to run this script\n")
  exit(1)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, Gio, Pango

from datetime import datetime
import time
from threading import Thread
import re
import serial
from time import localtime, strftime
from collections import deque
import logging
from logging.handlers import TimedRotatingFileHandler
from urllib.request import urlopen
import urllib
import math
import os
from bs4 import BeautifulSoup
import random
from socket import timeout

import database
import calcs
import weather
import funcs

widgets = dict()

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


                            
    
class InterFace(Gtk.Window):
    
    TimeOfPage = None

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

    def __insert(self, text_buffer, text):
        iter = text_buffer.get_end_iter()
        text_buffer.insert (iter, text)
        
    def __insert_with_tags_by_name(self, text_buffer, text, tag):
        iter = text_buffer.get_end_iter()
        text_buffer.insert_with_tags_by_name (iter, text, tag)

    def update_text_buffer(self, text_buffer, text, tag=None, clear_buffer_first=False):
        
        if clear_buffer_first:
            GObject.idle_add(self.clear_text_buffer, text_buffer, priority=GObject.PRIORITY_DEFAULT)
            
        if tag is None:
            GObject.idle_add(self.__insert, text_buffer, text, priority=GObject.PRIORITY_DEFAULT)
            #text_buffer.insert (iter, text)
        else:
            GObject.idle_add(self.__insert_with_tags_by_name, text_buffer, text, tag, priority=GObject.PRIORITY_DEFAULT)
            #text_buffer.insert_with_tags_by_name (iter, text, tag)

    def clear_text_buffer(self, text_buffer):
        start, end = text_buffer.get_bounds()
        text_buffer.delete (start, end)
        #GObject.idle_add(text_buffer.delete, start, end, priority=GObject.PRIORITY_DEFAULT)


    def populateAirfieldComboBox(self, combo):
        combo.append_text("All airfields")
        
        # extract the airfields from teh DB
        b_return, airfields, count = database.select ("SELECT * FROM `airfields` WHERE 1")
        if (b_return and count > 0):
            for airfield in airfields:
                combo.append_text(airfield['name'])
        else:
            logger.error ('Error when retrieving airfields for dropdown menu')
        
        combo.set_active(0)
        
    def populateImage(self, image, url, filename):
        
        try:
            with urllib.request.urlopen(url, timeout=5) as response, open(filename, 'wb') as out_file:
                data = response.read()
                out_file.write(data)
                #image.set_from_file (filename)
                GObject.idle_add(image.set_from_file, filename, priority=GObject.PRIORITY_DEFAULT)

        except (HTTPError, URLError) as error:
            logging.error('Image data did not download because %s\nURL: %s', error, url)
            return False
        except timeout:
            logging.error('Image data did not download because the socket timed out\nURL: %s', url)
            return False
        else:
            return True

    def populateMapRoute(self, image, airfield_lat, airfield_lng, firecall_lat, firecall_lon):
        
        url = 'https://maps.googleapis.com/maps/api/staticmap'
        url += '?size=640x640'
        url += '&maptype=terrain'
        url += '&markers=color:blue|label:H|%s,%s' % (airfield_lat, airfield_lng)
        url += '&markers=color:red|label:F|%s,%s' % (firecall_lat, firecall_lon)
        url += '&path=color:0xff0000ff|weight:5|%s,%s|%s,%s' % (airfield_lat, airfield_lng, firecall_lat, firecall_lon)
        url += '&key=AIzaSyCLUBXHPmb5uCNcjAgr4T-PVMII2IoHmD8'
        
        return self.populateImage (image, url, './route_map.png')
    
    def populateMapDestination(self, image, airfield_lat, airfield_lng, firecall_lat, firecall_lon):
        
        url = 'https://maps.googleapis.com/maps/api/staticmap'
        url += '?center=%s,%s' % (firecall_lat, firecall_lon)
        url += '&size=640x640'
        url += '&zoom=16'
        url += '&maptype=satellite'
        url += '&markers=color:red|label:F|%s,%s' % (firecall_lat, firecall_lon)
        url += '&key=AIzaSyCLUBXHPmb5uCNcjAgr4T-PVMII2IoHmD8'
        
        return self.populateImage (image, url, './destination_map.png')
   

    def updateNearestBomberReloadingAirfields(self, tbClosestAirbase, latitude, longitude):
        
        # if not then bug out.
        b_return = False
        try:
            b_return, airfields, count = database.select ("SELECT * FROM `airfield_bomber_reloading` ORDER BY `name`")
        except:
            pass
        
        if (not b_return):
            logger.error ("Error when trying to search `airfield_bomber_reloading`")
            logger.debug ("b_return: %s" % b_return)
            logger.debug ("row     : %s" % airfield)
            logger.debug ("count   : %s" % count)
        else:
            #logger.debug ("airfield: %s" % airfields)
            sorted_list = calcs.find_closest_airbases (latitude, longitude, airfields)
            buffer = "** CLOSEST RELOADING AIRBASES **\n%s: %.0f Nm\n%s: %.0f Nm" % (sorted_list[0]['name'], math.ceil(float(sorted_list[0]['distance'])), sorted_list[1]['name'], math.ceil(float(sorted_list[1]['distance'])))
            GObject.idle_add(self.tbClosestAirbase.set_text, buffer, priority=GObject.PRIORITY_DEFAULT)

        return True
    
    def updateAWS(self, tbWeather, aws_short_name):
        
        self.update_text_buffer(self.tbWeather, 'Downloading weather data...', clear_buffer_first=True)
        
        # what is the AWS for this airfield
        b_return, airfields_aws_dict, count = database.select ("SELECT * FROM `airfield_aws` WHERE short_name = '%s';" % aws_short_name)
        if (b_return):
            if (count > 0):
                
                b_dfwb, fwb = weather.download_fire_weather_bulletin()
                if (b_dfwb):
#                    try:
                        soup = BeautifulSoup(fwb, 'html.parser')
                        
                        self.update_text_buffer(self.tbWeather, '*** WEATHER ***', "tag_Bold", clear_buffer_first=True)

                        for airfield in airfields_aws_dict:
                            
                            b_success, aws_time, ffdi, gfdi = weather.parse_wx_from_fwb (soup, airfield['aws'])
                            if (b_success):

                                message = "\n\n%s(%s): " % (airfield['name'], airfield['fdi_trigger'])
                                self.update_text_buffer(self.tbWeather, message)
                            
                                if (int(max(gfdi, ffdi)) > int(airfield['fdi_trigger'])):
                                    self.update_text_buffer(self.tbWeather, "GO", "tag_Go")
                                else:
                                    self.update_text_buffer(self.tbWeather, "NO GO", "tag_NoGo")
                                    
                                message = "\nFFDI is %d, GFDI is %d." % (ffdi, gfdi)
                                self.update_text_buffer(self.tbWeather, message)
                            else:
                                logger.error ('Could not parse weather data')
                            
                        message = "\n\nCorrect as at %s" % aws_time
                        self.update_text_buffer(self.tbWeather, message)
 #                   except:
 #                       logging.error (sys.exc_info()[0])
                else:
                    logging.error ('Could not download FWB from BOM. Possible internet connection issue.')
                    self.update_text_buffer(self.tbWeather, 'Could not download FWB from BOM. Possible internet connection issue.', "tag_Bold", clear_buffer_first=True)
        else:
            logging.error ('Cant get AWS from short name')
            self.update_text_buffer(self.tbWeather, 'Cant get AWS from short name', "tag_Bold", clear_buffer_first=True)
        
        
    def btnSendTestPage(self, object, data=None):
        
        __ser = self.InitSerialPort()
        
        __pdd_test_list = []
        __pdd_test_list.append(b'\r\nM 001817568 @@ALERT F123456789 INVL2 G&SC1 SMALL GRASS FIRE EMMA LANE INVERLOCH SVC 6962 D7 (123456) LAT/LON:-38.6313124, 145.6566964 DISP509 AIRLTV BDG374 CINVL CWOGI HEL337\r\n')
        __pdd_test_list.append(b'\r\nM 001814336 @@ALERT F180300594 JUNO3 G&SC1 SMOKE SIGHTING FROM FIRETOWER CNR BENNETTS RD/MELALEUCA AV LONGLEA SVNW 8285 F9 (673248) LAT/LON:-36.7938187, 144.3928462 DISP502 AIRBEN CAXEC CBENDS CJUNO FBD305 HEL335 [AIRBEN ]\r\n')
        __pdd_test_list.append(b'\r\nM 001876600 @@ALERT F180300904 TOOL2 G&SC1 GRASS FIRE SPREADING CNR COIMADAI-DIGGERS REST RD/HOLDEN RD TOOLERN VALE M 332 F5 (921328) LAT/LON:-37.6281814, 144.6449890 DISP61 AIRBAC CMTON CTOOL HEL345\r\n')
        __pdd_test_list.append(b'\r\nM 001816088 @@ALERT F180300913 MTEL1 G&SC1 UNDEFINED FIRE IN BACKYARD 125 BELLBIRD RD MOUNT ELIZA /FREELANDS DR //HUMPHRIES RD M 106 C3 (354711) LAT/LON:-38.1926135, 145.1209718 DISP27 AIRMMB CFTONS CMTEL FBD302 HEL338\r\n')
        __pdd_test_list.append(b'\r\nM 001816184 @@ALERT F180301004 KYAB4 G&SC1 TREE FIRE BEHIND CALLERS ADDRESS 12 CROW CR KYABRAM /MELLIS ST SVNE 8362 E5 (243803) LAT/LON:-36.3059159, 145.0437140 DISP520 AIRSHP CKYAB CMGUM CTGAL HEL331\r\n')
        
        __pdd_test_broken_list = []
        __pdd_test_broken_list.append(b'\r\nM 00181768 @@ALERT F123456789 INVL2 G&SC1 SMALL GRASS FIRE EMMA LANE INVERLOCH SVC 6962 D7 (123456) LAT/LON:-38.6313124, 145.6566964 DISP509 AIRLTV BDG374 CINVL CWOGI HEL337\r\n')
        __pdd_test_broken_list.append(b'\r\nM 001814336 @@ALERT F18030594 JUNO3 G&SC1 SMOKE SIGHTING FROM FIRETOWER CNR BENNETTS RD/MELALEUCA AV LONGLEA SVNW 8285 F9 (673248) LAT/LON:-36.7938187, 144.3928462 DISP502 AIRBEN CAXEC CBENDS CJUNO FBD305 HEL335 [AIRBEN ]\r\n')
        __pdd_test_broken_list.append(b'\r\nM 001876600 @@ALER F180300904 TOOL2 G&SC1 GRASS FIRE SPREADING CNR COIMADAI-DIGGERS REST RD/HOLDEN RD TOOLERN VALE M 332 F5 (921328) LAT/LON:-37.6281814, 144.6449890 DISP61 AIRBAC CMTON CTOOL HEL345\r\n')
        __pdd_test_broken_list.append(b'\r\nM 001816088 @@ALERT F180300913 MTEL1 G&SC1 UNDEFINED FIRE IN BACKYARD 125 BELLBIRD RD MOUNT ELIZA /FREELANDS DR //HUMPHRIES RD M 106 C3 (354711) LAT/LN:-38.1926135, 145.1209718 DISP27 AIRMMB CFTONS CMTEL FBD302 HEL338\r\n')
        __pdd_test_broken_list.append(b'\r\nM 001816184 @@ALERT F180301004 KYAB4 G&SC1 TREE FIRE BEHIND CALLERS ADDRESS 12 CROW CR KYABRAM /MELLIS ST SVNE 8362 E5 (243803) LAT/LON:-36.3059159, 140437140 DISP520 AIRSHP CKYAB CMGUM CTGAL HEL331\r\n')

        __message = (random.choice(__pdd_test_list))
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
                        continue
                    
                    #only allow printable characters
                    if len(ch) == 0:
                        continue
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
                                    
                                    logging.debug("Raw             :" + message)
                                    
                                    capcode = message[0:9]
                                    message = message[9:].lstrip()                                
                                    #print ("capcode is %s" % capcode)
                                    #print ("message is %s" % message)
                                    
                                    
                                    # is the capcode a PDD response.
                                    # if not then bug out.
                                    try:
                                        b_return, airfield, count = database.select ("SELECT * FROM `airfields` WHERE capcode = '%s';" % capcode)
                                        airfield = airfield[0]
                                        #logger.debug ("b_return: %s" % b_return)
                                        #logger.debug ("row     : %s" % airfield)
                                        #logger.debug ("count   : %s" % count)
                                    except:
                                        pass
                                    
                                    if (not b_return):
                                        logger.error ('Error when trying to search for airfield')
                                    
                                    if (count > 0):
                                        b_pdd_response = True
                                    else:
                                        b_pdd_response = False
                                    
                                    if (b_pdd_response):
                                    
                                        # start the clock
                                        self.TimeOfPage = datetime.now()

                                        # extract the page priority (EMERG, NON EMERG or ADMIN)
                                        priority = message[0:2]
                                        message = message[2:].lstrip()
                                        if (priority == '@@'):
                                            priority = 'EMERGENCY'
                                        if (priority == 'HB'):
                                            priority = 'NON EMERGENCY'
                                        if (priority == 'QD'):
                                            priority = 'ADMIN'
                                        
                                        logging.debug("Priority        :" + priority)
                                        logging.debug("Message         :" + message)
                                        
                                        # show the message in the textbox
                                        widgets['tbPagerMessage'].set_text('')
                                        iter = widgets['tbPagerMessage'].get_iter_at_offset(0)
                                        GObject.idle_add(widgets['tbPagerMessage'].insert_with_tags_by_name, iter, message, "tag_Large", priority=GObject.PRIORITY_DEFAULT)
                                        
                                        
                                        parse_alert = False
                                        parse_f_number = False
                                        parse_incident_type = False
                                        parse_assignment_area = False
                                        parse_dispatch_channel = False
                                        parse_mapbook = False
                                        parse_lat_long = False
                                    
                                        if ((re.search("ALERT.{1,}", message) != None) and (re.search("F[0-9]{1,}", message) != None)):
                                            #logging.debug ("FIRECALL page received")
                                            #logging.info (raw)
                                            
                                            # ALERT
                                            expression = "ALERT"
                                            search_response = re.search(expression, message)      # extract ALERT
                                            if (search_response != None):
                                                alert = search_response.group(0)
                                                message = re.sub(expression, '', message)   # remove ALERT
                                                message = funcs.CleanString (message)
                                                logging.debug("Alert           :" + alert)
                                                parse_alert = True
                                            else:
                                                logging.debug("No match for ALERT")
                                                
                                        
                                            # Fnumber
                                            #expression = "^F[0-9]{1,}"
                                            expression = "F[0-9]{1,9}"
                                            search_response = re.search(expression, message)      # extract Fxxxxxxxxx
                                            if (search_response != None):
                                                Fnumber = search_response.group(0)
                                                message = re.sub(expression, '', message)   # remove Fxxxxxxxxx
                                                message = funcs.CleanString (message)
                                                logging.debug("Fnumber         :" + Fnumber)
                                                parse_f_number = True
                                            else:
                                                logging.debug("No match for Fnumber")                                                

                                            # Incident type and response code
                                            expression = "\\b(ALARC1|ALARC3|STRUC1|STRUC3|INCIC1|INCIC3|NOSTC1|NOSTC3|G&SC1|G&SC3|NS&RC1|NS&RC3|RESCC1|RESCC3|CONFC1|CONFC3|HIARC1|HIARC3|STCOC1|STCOC3|TRCHC1|TRCHC3|AFEMR|AFPEMR|STRIKE)\\b"
                                            search_response = re.search(expression, message)      # extract IncidentType
                                            if (search_response != None):
                                                IncidentType = search_response.group(0)
                                                message = re.sub(expression, '', message)   # remove IncidentType
                                                message = funcs.CleanString (message)
                                                logging.debug("IncidentType    :" + IncidentType)
                                                parse_incident_type = True
                                            else:
                                                logging.debug("No match for IncidentType")                                                
                                                                                
                                            # Assignment Area
                                            #expression = "(^(\w+\s){1})"
                                            expression = "^(\w{1,})"
                                            search_response = re.search(expression, message)      # extract AssignmentArea
                                            if (search_response != None):
                                                AssignmentArea = search_response.group(0)
                                                message = re.sub(expression, '', message)         # remove AssignmentArea
                                                message = funcs.CleanString (message)
                                                logging.debug("AssignmentArea  :" + AssignmentArea)
                                                parse_assignment_area = True
                                            else:
                                                logging.debug("No match for Assignment Area")
                                                                                                                                                                            
                                            # Dispatch channel
                                            expression = "DISP[0-9]{1,} "
                                            search_response = re.search(expression, message)      # extract DispatchChannel
                                            if (search_response != None):
                                                DispatchChannel = search_response.group(0)
                                                message = re.sub(expression, '', message)         # remove DispatchChannel
                                                message = funcs.CleanString (message)
                                                DispatchChannel = DispatchChannel.replace ("DISP", "")
                                                logging.debug("Dispatch channel:" + DispatchChannel)
                                                parse_dispatch_channel = True
                                            else:
                                                logging.debug("No match for Dispatch Channel")
                                                                                                
                                            # Melways
                                            expression = "M[ ]\\d{1,4}[A-Z]?[ ]\\w{1}\\d{1,2}"
                                            Map_Melways = None
                                            search_response = re.search(expression, message)      # extract Map_Melways
                                            if (search_response != None):
                                                Map_Melways = search_response.group(0)
                                                message = re.sub(expression, '', message)         # remove Map_Melways
                                                message = funcs.CleanString (message)

                                            # Map_SV
                                            expression = "SV(\w{0,})[ 0-9]{0,}\w{0,}"
                                            Map_SV = None
                                            search_response = re.search(expression, message)      # extract Map_SV
                                            if (search_response != None):
                                                Map_SV = search_response.group(0)
                                                message = re.sub(expression, '', message)         # remove Map_SV
                                                message = funcs.CleanString (message)

                                            # check the mapping
                                            MapRef = None
                                            if (Map_Melways == None and Map_SV == None):
                                                logging.debug("No match for Map ref")                                                
                                            else:
                                                parse_mapbook = True
                                                if (Map_Melways != None):
                                                    MapRef = Map_Melways
                                                else:
                                                    MapRef = Map_SV
                                                logging.debug("Map ref         :" + MapRef)
                                            
                                            # parse lat/long
                                            expression = '(-?[0-9]{2,}[.]{1,}[0-9]{3,}),?\s([0-9]{2,}[.]{1,}[0-9]{3,})'
                                            Latitude = None
                                            Longitude = None
                                            search_response = re.search (expression, message)  # extract lat/lon
                                            if (search_response != None):
                                                LatLon = search_response.group(0)
                                                message = re.sub(expression, '', message)
                                                message = re.sub('LAT/LON:', '', message)
                                                message = funcs.CleanString (message)
                                                latitude, longitude = LatLon.split(',')
                                                latitude = latitude.strip()
                                                longitude = longitude.strip()
                                                logging.debug("Latitude        :" + latitude)
                                                logging.debug("Longitude       :" + longitude)
                                                parse_lat_long = True
                                            else:
                                                logging.debug("No match for Lat/Long")
                                                                                            
                                            
                                            logging.debug ("Remaining msg   :" + message)
                                        else:
                                            logging.debug ("Not a FIRECALL")
                                            
                                        logging.debug ("parse_alert            :" + str(parse_alert))
                                        logging.debug ("parse_f_number         :" + str(parse_f_number))
                                        logging.debug ("parse_incident_type    :" + str(parse_incident_type))
                                        logging.debug ("parse_assignment_area  :" + str(parse_assignment_area))
                                        logging.debug ("parse_dispatch_channel :" + str(parse_dispatch_channel))
                                        logging.debug ("parse_mapbook          :" + str(parse_mapbook))
                                        logging.debug ("parse_lat_long         :" + str(parse_lat_long))
                                        
                                        # let the pilots know that the screen is updating
                                        GObject.idle_add(self.tbWeather.set_text, "Downloading weather from BOM...", priority=GObject.PRIORITY_DEFAULT)
                                        GObject.idle_add(self.tbFlightPath.set_text, "Calculating flight details...", priority=GObject.PRIORITY_DEFAULT)
                                        GObject.idle_add(self.tbClosestAirbase.set_text, "Finding nearest reloading bases...", priority=GObject.PRIORITY_DEFAULT)
                                        GObject.idle_add(self.imageMapRoute.clear, priority=GObject.PRIORITY_DEFAULT)
                                        GObject.idle_add(self.imageMapDestination.clear, priority=GObject.PRIORITY_DEFAULT)
                                        
                                        
                                        # populate the flight info text box
                                        if (parse_lat_long and parse_dispatch_channel):
                                            distance, bearing = calcs.get_distance_and_bearing (airfield['lat'], airfield['lng'], latitude, longitude)
                                            buffer = ("** FLIGHT DATA**\nDistance : %s\nBearing : %s\nDispatch: %s" % (str(distance), str(bearing), DispatchChannel))
                                            GObject.idle_add(self.tbFlightPath.set_text, buffer, priority=GObject.PRIORITY_DEFAULT)
                                        else:
                                            GObject.idle_add(self.tbFlightPath.set_text, 'Error extracting flight details.\n\nPossible causes;\n-Not an ALERT page\n-Problem with Lat/Long\n-Problem with dispatch channel', priority=GObject.PRIORITY_DEFAULT)
                                        
                                        # update closest bomber reloading airfields
                                        if (parse_lat_long):
                                            self.updateNearestBomberReloadingAirfields(self.tbClosestAirbase, latitude, longitude)
                                        else:
                                            GObject.idle_add(self.tbClosestAirbase.set_text, 'Error finding nearest reloading base.\n\nPossible causes;\n-Not an ALERT page\n-Problem with Lat/Long', priority=GObject.PRIORITY_DEFAULT)
                                        
                                        # update weather information
                                        if (parse_alert):
                                            self.updateAWS(self.tbWeather, airfield['short_name'])
                                            #pass
                                        else:
                                            GObject.idle_add(self.tbWeather.set_text, 'Error with weather.\n\nPossible causes;\n-Not an ALERT page', priority=GObject.PRIORITY_DEFAULT)

                                        # update image
                                        if (parse_lat_long):
                                            self.populateMapRoute(self.imageMapRoute, airfield['lat'], airfield['lng'], latitude, longitude)
                                            self.populateMapDestination(self.imageMapDestination, airfield['lat'], airfield['lng'], latitude, longitude)
                                        else:
                                            pass
                                                
                                    else:
                                        print ('Not a PDD response')
                                        
                                    
                                    
                
            except serial.SerialException as e:
                pass

            
    def __init__(self):
                    
        logging.debug ('** Executing def __init__(self):')
        self.gladefile = "pdd_main.glade"
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("mainwindow")
        self.window.maximize()
        self.window.show()
        
        #self.tbPagerMessage = self.builder.get_object("tbPagerMessage")
        self.tvPagerMessage = self.builder.get_object("tvPagerMessage")
        self.tbWeather = self.builder.get_object("tbWeather")
        self.tbFlightPath = self.builder.get_object("tbFlightPath")
        self.tbClosestAirbase = self.builder.get_object("tbClosestAirbase")
        self.comboAirfield = self.builder.get_object("comboAirfield")
        self.tbTimeSincePage = self.builder.get_object("tbTimeSincePage")
        self.imageMapRoute = self.builder.get_object("imageMapRoute")
        self.imageMapDestination = self.builder.get_object("imageMapDestination")
        
        #self.tbPagerMessage.create_tag("tag_Large", weight=Pango.Weight.BOLD, size=30 * Pango.SCALE)
        self.tbWeather.create_tag("tag_Bold", weight=Pango.Weight.BOLD)
        self.tbWeather.create_tag("tag_NoGo", foreground="red")
        self.tbWeather.create_tag("tag_Go", foreground="green")
        
        widgets['tbPagerMessage'] = self.builder.get_object("tbPagerMessage")
        widgets['tbPagerMessage'].create_tag("tag_Large", weight=Pango.Weight.BOLD, size=30 * Pango.SCALE)
        
                             
        self.populateAirfieldComboBox(self.comboAirfield)
        
        self.TimeOfPage = None

        # 1. define the tread, updating your text
        self.update = Thread(target=self.process_serial)
        # 2. Deamonize the thread to make it stop with the GUI
        self.update.setDaemon(True)
        # 3. Start the thread
        self.update.start()
        
        
        self.window.queue_draw()
  
    # Displays Timer
    def displayclock(self):
        #  we need to return "True" to ensure the timer continues to run, otherwise it will only run once.
        if (self.TimeOfPage is not None):
            time_elapsed = (datetime.now() - self.TimeOfPage).total_seconds()
            buffer = calcs.hms_string(time_elapsed)
            GObject.idle_add(self.tbTimeSincePage.set_text, buffer, len(buffer), priority=GObject.PRIORITY_DEFAULT)
        return True

        
    # Initialize Timer
    def startclocktimer(self):
            #  this takes 2 args: (how often to update in millisec, the method to run)
            GObject.timeout_add(1000, self.displayclock)
  
def run_gui():
    main = InterFace()
    #exit()
    
    # 4. this is where we call GObject.threads_init()
    GObject.threads_init()
    main.show_all()
    main.startclocktimer()
    Gtk.main()

if __name__ == "__main__":
    run_gui()  