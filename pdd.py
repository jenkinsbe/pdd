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
from timeit import default_timer as timer

import database
import calcs
import weather
import funcs

widgets = dict()
jobs = []


# if there is no directory called 'logs', then generate it.
if (not os.path.isdir("./logs/")):
    os.mkdir("./logs")

# if there is no directory called 'maps', then generate it.
if (not os.path.isdir("./maps/")):
    os.mkdir("./maps")

    
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
    jobs_index = 0
    

    def on_window_destroy(self, object, data=None):
        print ("Quiting")
        Gtk.main_quit()
    
    def btnNextJob(self, object, data=None):
        print ("Next job")

        if (len(jobs) > 0):
            #logging.debug ("len(jobs)  : %d" % len(jobs))
            #logging.debug ("jobs_index : %d" % self.jobs_index)

            self.jobs_index += 1
            if ((self.jobs_index) >= len(jobs)):
                self.jobs_index = len(jobs) - 1

            #logging.debug ("jobs_index : %d" % self.jobs_index)
            self.update_screen(jobs[self.jobs_index])

    def btnPreviousJob(self, object, data=None):
        print ("Previous job")

        if (len(jobs) > 0):
            #logging.debug ("len(jobs)  : %d" % len(jobs))
            #logging.debug ("jobs_index : %d" % self.jobs_index)

            self.jobs_index -= 1
            if ((self.jobs_index) < 0):
                self.jobs_index = 0

            #logging.debug ("jobs_index : %d" % self.jobs_index)
            self.update_screen(jobs[self.jobs_index])
        
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

        except (urllib.HTTPError, urllib.URLError) as error:
            logging.error('Image data did not download because %s\nURL: %s', error, url)
            return False
        except timeout:
            logging.error('Image data did not download because the socket timed out\nURL: %s', url)
            return False
        else:
            return True

    def downloadImage (self, url, filename):
        try:
            with urllib.request.urlopen(url, timeout=15) as response, open(filename, 'wb') as out_file:
                data = response.read()
                out_file.write(data)
                
        except (urllib.HTTPError, urllib.URLError) as error:
            logging.error('Image data did not download because %s\nURL: %s', error, url)
            return False
        except timeout:
            logging.error('Image data did not download because the socket timed out\nURL: %s', url)
            return False
        else:
            return True
    
    
    def populateMapRoute(self, image, job):

        filename = ("./maps/%s_route.png" % job['Fnumber'])
        
        if (job.get('route_map_downloaded', False)):
            GObject.idle_add(image.set_from_file, filename, priority=GObject.PRIORITY_DEFAULT)
        else:

            url = 'https://maps.googleapis.com/maps/api/staticmap'
            url += '?size=640x640'
            url += '&maptype=terrain'
            url += '&markers=color:blue|label:H|%s,%s' % (job['airfield']['lat'], job['airfield']['lng'])
            url += '&markers=color:red|label:F|%s,%s' % (job['latitude'], job['longitude'])
            url += '&path=color:0xff0000ff|weight:5|%s,%s|%s,%s' % (job['airfield']['lat'], job['airfield']['lng'], job['latitude'], job['longitude'])
            url += '&key=AIzaSyCLUBXHPmb5uCNcjAgr4T-PVMII2IoHmD8'
        
            if (self.downloadImage (url, filename)):
                GObject.idle_add(image.set_from_file, filename, priority=GObject.PRIORITY_DEFAULT)
                job['route_map_downloaded'] = True
            
    def populateMapDestination(self, image, job):
        
        filename = ("./maps/%s_destination.png" % job['Fnumber'])
        
        if (job.get('destination_map_downloaded', False)):
            GObject.idle_add(image.set_from_file, filename, priority=GObject.PRIORITY_DEFAULT)
        else:

            url = 'https://maps.googleapis.com/maps/api/staticmap'
            url += '?center=%s,%s' % (job['latitude'], job['longitude'])
            url += '&size=640x640'
            url += '&zoom=16'
            url += '&maptype=satellite'
            url += '&markers=color:red|label:F|%s,%s' % (job['latitude'], job['longitude'])
            url += '&key=AIzaSyCLUBXHPmb5uCNcjAgr4T-PVMII2IoHmD8'
        
            if (self.downloadImage (url, filename)):
                GObject.idle_add(image.set_from_file, filename, priority=GObject.PRIORITY_DEFAULT)
                job['destination_map_downloaded'] = True
   
   
    def FindClosestAirfields(self, latitude, longitude, sql):

        logging.debug ("  sql        : %s" % sql)
        try:
            b_return, airfields, count = database.select (sql)
            logging.debug ("  b_return  : %s" % b_return)
            logging.debug ("  airfields : %s" % airfields)
            logging.debug ("  count     : %s" % count)

            if (b_return):
                
                return True, calcs.find_closest_airbases (latitude, longitude, airfields)
        except:
            logging.error ("Error when finding closest airfield")
        
        return False, None

    def updateNearestBomberReloadingAirfields(self, tbClosestAirbase, job):

        # if we haven't calculated it before, do it now.
        if (not job.get('nearest_bombers_calculated', False)):
            
            b_return, airfields = self.FindClosestAirfields (job['latitude'], job['longitude'], "SELECT name, lat, lng  FROM `airfield_bomber_reloading` ORDER BY `name`;")
            if (b_return):
                job['nearest_bombers_sorted_list'] = airfields
                job['nearest_bombers_calculated'] = True
            else:
                job['nearest_bombers_calculated'] = False
        else:
            job['nearest_bombers_calculated'] = False
            
        # now we know its been calculated, show it
        if (job.get('nearest_bombers_calculated', False)):
            buffer = "** CLOSEST BOMBER RELOADING AIRBASES **\n%s: %.0f Nm\n%s: %.0f Nm" % (job['nearest_bombers_sorted_list'][0]['name'], math.ceil(float(job['nearest_bombers_sorted_list'][0]['distance'])), job['nearest_bombers_sorted_list'][1]['name'], math.ceil(float(job['nearest_bombers_sorted_list'][1]['distance'])))
            GObject.idle_add(tbClosestAirbase.set_text, buffer, priority=GObject.PRIORITY_DEFAULT)
            job['nearest_bombers_calculated'] = True
        else:
            logging.error ("Could not find closest bomber reloading airbases")
    
    def updateNearestPDDAirfields(self, tbClosestPDD, job):

        # if we haven't calculated it before, do it now.
        if (not job.get('nearest_pdd_calculated', False)):
            
            b_return, airfields = self.FindClosestAirfields (job['latitude'], job['longitude'], "SELECT name, lat, lng FROM `airfields` ORDER BY `name`;")
            if (b_return):
                job['nearest_pdd_sorted_list'] = airfields
                job['nearest_pdd_calculated'] = True
            else:
                job['nearest_pdd_calculated'] = False
        else:
            job['nearest_pdd_calculated'] = False
        
        # now we know its been calculated, show it
        if (job.get('nearest_pdd_calculated', False)):
            buffer = "** CLOSEST NOMINATED OPERATING AIRBASES **\n%s: %.0f Nm\n%s: %.0f Nm" % (job['nearest_pdd_sorted_list'][0]['name'], math.ceil(float(job['nearest_pdd_sorted_list'][0]['distance'])), job['nearest_pdd_sorted_list'][1]['name'], math.ceil(float(job['nearest_pdd_sorted_list'][1]['distance'])))
            GObject.idle_add(tbClosestPDD.set_text, buffer, priority=GObject.PRIORITY_DEFAULT)
            job['nearest_pdd_calculated'] = True
        else:
            logging.error ("Could not find closest nominated operating airbases")


    def updateAWS(self, tbWeather, job):
        
        start = timer()
        self.update_text_buffer(self.tbWeather, 'Downloading weather data...', clear_buffer_first=True)
        
        aws_short_name = job['airfield']['short_name']
        
        # what is the AWS for this airfield
        b_return, airfields_aws_dict, count = database.select ("SELECT * FROM `airfield_aws` WHERE short_name = '%s';" % aws_short_name)
        #logging.debug ("%.5fs:%s" %(timer()-start, "Database transaction complete"))
        if (b_return):
            if (count > 0):
                if (job.get('soup', None) is None):
                    b_dfwb, fwb = weather.download_fire_weather_bulletin()
                    #logging.debug ("%.5fs:%s" %(timer()-start, "FWB download complete"))

                    job['soup'] = BeautifulSoup(fwb, 'html.parser')
                    #logging.debug ("%.5fs:%s" %(timer()-start, "html.parser complete"))
                
                if (job.get('soup', None) is not None):
#                    try:
                        
                        self.update_text_buffer(self.tbWeather, '*** WEATHER ***', "tag_Bold", clear_buffer_first=True)

                        for airfield in airfields_aws_dict:
                            
                            b_success, aws_time, ffdi, gfdi = weather.parse_wx_from_fwb (job['soup'], airfield['aws'])
                            if (b_success):

                                message = "\n\n%s(%s): " % (airfield['name'], airfield['fdi_trigger'])
                                self.update_text_buffer(self.tbWeather, message)
                            
                                if (int(max(gfdi, ffdi)) > int(airfield['fdi_trigger'])):
                                    self.update_text_buffer(self.tbWeather, "GO", "tag_Go")
                                else:
                                    self.update_text_buffer(self.tbWeather, "NO GO", "tag_NoGo")
                                    
                                message = "\nFFDI is %d, GFDI is %d." % (ffdi, gfdi)
                                self.update_text_buffer(self.tbWeather, message)
                                
                                #logging.debug ("%.5fs:Found weather for %s AWS" %(timer()-start, airfield['aws']))

                            else:
                                logger.error ('Could not parse weather data')
                            
                        #logging.debug ("%.5fs:%s" %(timer()-start, "Parsing of FWB complete"))
                        message = "\n\nCorrect as at %s" % aws_time
                        self.update_text_buffer(self.tbWeather, message)
                        #logging.debug ("%.5fs:%s" %(timer()-start, "Screen update complete"))
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
        __pdd_test_list.append(b'\r\nM 001817568 @@ALERT F123456789 INVL2 G&SC1 SMALL GRASS FIRE EMMA LANE INVERLOCH SVC 6962 D7 (123456) LAT/LON:-38.6313124, 145.6566964 DISP509 AIRLTV BDG374 CINVL CWOGI HEL337 RSSI: 80\r\n')
        __pdd_test_list.append(b'\r\nM 001814336 @@ALERT F180300594 JUNO3 G&SC1 SMOKE SIGHTING FROM FIRETOWER CNR BENNETTS RD/MELALEUCA AV LONGLEA SVNW 8285 F9 (673248) LAT/LON:-36.7938187, 144.3928462 DISP502 AIRBEN CAXEC CBENDS CJUNO FBD305 HEL335 [AIRBEN] RSSI: 81\r\n')
        __pdd_test_list.append(b'\r\nM 001876600 @@ALERT F180300904 TOOL2 G&SC1 GRASS FIRE SPREADING CNR COIMADAI-DIGGERS REST RD/HOLDEN RD TOOLERN VALE M 332 F5 (921328) LAT/LON:-37.6281814, 144.6449890 DISP61 AIRBAC CMTON CTOOL HEL345 RSSI: 82\r\n')
        __pdd_test_list.append(b'\r\nM 001816088 @@ALERT F180300913 MTEL1 G&SC1 UNDEFINED FIRE IN BACKYARD 125 BELLBIRD RD MOUNT ELIZA /FREELANDS DR //HUMPHRIES RD M 106 C3 (354711) LAT/LON:-38.1926135, 145.1209718 DISP27 AIRMMB CFTONS CMTEL FBD302 HEL338 RSSI: 83\r\n')
        __pdd_test_list.append(b'\r\nM 001816184 @@ALERT F180301004 KYAB4 G&SC1 TREE FIRE BEHIND CALLERS ADDRESS 12 CROW CR KYABRAM /MELLIS ST SVNE 8362 E5 (243803) LAT/LON:-36.3059159, 145.0437140 DISP520 AIRSHP CKYAB CMGUM CTGAL HEL331 RSSI: 84\r\n')
        
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
    
    def update_screen(self, job=None):

        if job is not None:
            start = timer()
            
            # let the pilots know that the screen is updating
            logging.debug ("Updating screen")
            GObject.idle_add(self.tbWeather.set_text, "Downloading weather from BOM...", priority=GObject.PRIORITY_DEFAULT)
            GObject.idle_add(self.tbFlightPath.set_text, "Calculating flight details...", priority=GObject.PRIORITY_DEFAULT)
            GObject.idle_add(self.tbClosestAirbase.set_text, "Finding closest bomber reloading airbases...", priority=GObject.PRIORITY_DEFAULT)
            GObject.idle_add(self.tbClosestPDD.set_text, "Finding closest nominated operating airbases...", priority=GObject.PRIORITY_DEFAULT)
            GObject.idle_add(self.imageMapRoute.clear, priority=GObject.PRIORITY_DEFAULT)
            GObject.idle_add(self.imageMapDestination.clear, priority=GObject.PRIORITY_DEFAULT)
            logging.debug ("%.5fs:%s" %(timer()-start, "Updating screen"))
            
            # show the message in the textbox
            logging.debug ("Update message textbox")
            widgets['tbPagerMessage'].set_text('')
            iter = widgets['tbPagerMessage'].get_iter_at_offset(0)
            GObject.idle_add(widgets['tbPagerMessage'].insert_with_tags_by_name, iter, job['message'], "tag_Large", priority=GObject.PRIORITY_DEFAULT)
            logging.debug ("%.5fs:%s" %(timer()-start, "Update message textbox"))

            
            # update the timer
            logging.debug ("Update time of page")
            self.TimeOfPage = job['TimeOfPage']
            logging.debug ("%.5fs:%s" %(timer()-start, "Update timer"))
            
            # update the clock
            logging.debug ("Update clock")
            buffer = str(job['TimeOfPage'].strftime("%H:%M:%S"))
            GObject.idle_add(self.tbTimeOfPage.set_text, buffer, len(buffer), priority=GObject.PRIORITY_DEFAULT)
            logging.debug ("%.5fs:%s" %(timer()-start, "Update clock"))
            
            # populate the flight info text box
            logging.debug ("Update flight info textbox")
            GObject.idle_add(self.tbFlightPath.set_text, job['buffer_flight_info'], priority=GObject.PRIORITY_DEFAULT)
            logging.debug ("%.5fs:%s" %(timer()-start, "Update flight info textbox"))
            
            # update closest airfields
            logging.debug ("Update closest airfields")
            if (job['parse_lat_long']):
                self.updateNearestBomberReloadingAirfields(self.tbClosestAirbase, job)
                self.updateNearestPDDAirfields(self.tbClosestPDD, job)
            else:
                GObject.idle_add(self.tbClosestAirbase.set_text, 'Error finding nearest bomber reloading airbase.\n\nPossible causes;\n-Not an ALERT page\n-Problem with Lat/Long', priority=GObject.PRIORITY_DEFAULT)
                GObject.idle_add(self.tbClosestPDD.set_text, 'Error finding nearest nominated operating airbase.\n\nPossible causes;\n-Not an ALERT page\n-Problem with Lat/Long', priority=GObject.PRIORITY_DEFAULT)
            logging.debug ("%.5fs:%s" %(timer()-start, "Update closest airfields"))
                
            # update weather information
            logging.debug ("Update weather information")
            if (job['parse_alert']):
                self.updateAWS(self.tbWeather, job)
                #self.updateAWS(self.tbWeather, job['airfield']['short_name'])
            else:
                GObject.idle_add(self.tbWeather.set_text, 'Error with weather.\n\nPossible causes;\n-Not an ALERT page', priority=GObject.PRIORITY_DEFAULT)
            logging.debug ("%.5fs:%s" %(timer()-start, "Update weather information"))

            # update image
            logging.debug ("Update maps")
            if (job['parse_lat_long']):
                self.populateMapRoute(self.imageMapRoute, job)
                self.populateMapDestination(self.imageMapDestination, job)
            else:
                pass
            logging.debug ("%.5fs:%s" %(timer()-start, "Update maps"))
    
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
                                    
                                    # print raw pager message to log
                                    logging.debug(message)
                                    
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
                                    
                                    
                                    # job is a pdd job
                                    if (b_pdd_response):
                                    
                                        # process the job
                                        job = dict()
                                        job['airfield'] = airfield
                                        job['capcode'] = capcode
                                        job['TimeOfPage'] = datetime.now()
                                                                            
                                    
                                        # extract the page priority (EMERG, NON EMERG or ADMIN)
                                        priority = message[0:2]
                                        message = message[2:].lstrip()
                                        job['message'] = message
                                        
                                        if (priority == '@@'):
                                            priority = 'EMERGENCY'
                                        if (priority == 'HB'):
                                            priority = 'NON EMERGENCY'
                                        if (priority == 'QD'):
                                            priority = 'ADMIN'
                                        job['priority'] = priority
                                        logging.debug("Priority        :" + priority)
                                        logging.debug("Message         :" + message)
                                        
                                        
                                        job['parse_alert'] = False
                                        job['parse_f_number'] = False
                                        job['parse_incident_type'] = False
                                        job['parse_assignment_area'] = False
                                        job['parse_dispatch_channel'] = False
                                        job['parse_mapbook'] = False
                                        job['parse_lat_long'] = False
                                    
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
                                                job['parse_alert'] = True
                                            else:
                                                logging.debug("No match for ALERT")
                                                
                                        
                                            # job['Fnumber']
                                            #expression = "^F[0-9]{1,}"
                                            expression = "F[0-9]{1,9}"
                                            search_response = re.search(expression, message)      # extract Fxxxxxxxxx
                                            if (search_response != None):
                                                job['Fnumber'] = search_response.group(0)
                                                message = re.sub(expression, '', message)   # remove Fxxxxxxxxx
                                                message = funcs.CleanString (message)
                                                logging.debug("Fnumber         :" + job['Fnumber'])
                                                job['parse_f_number'] = True
                                            else:
                                                logging.debug("No match for Fnumber")                                                

                                            # Incident type and response code
                                            expression = "\\b(ALARC1|ALARC3|STRUC1|STRUC3|INCIC1|INCIC3|NOSTC1|NOSTC3|G&SC1|G&SC3|NS&RC1|NS&RC3|RESCC1|RESCC3|CONFC1|CONFC3|HIARC1|HIARC3|STCOC1|STCOC3|TRCHC1|TRCHC3|AFEMR|AFPEMR|STRIKE)\\b"
                                            search_response = re.search(expression, message)      # extract IncidentType
                                            if (search_response != None):
                                                job['IncidentType'] = search_response.group(0)
                                                message = re.sub(expression, '', message)   # remove IncidentType
                                                message = funcs.CleanString (message)
                                                logging.debug("IncidentType    :" + job['IncidentType'])
                                                job['parse_incident_type'] = True
                                            else:
                                                logging.debug("No match for IncidentType")                                                
                                                                                
                                            # Assignment Area
                                            #expression = "(^(\w+\s){1})"
                                            expression = "^(\w{1,})"
                                            search_response = re.search(expression, message)      # extract AssignmentArea
                                            if (search_response != None):
                                                job['AssignmentArea'] = search_response.group(0)
                                                message = re.sub(expression, '', message)         # remove AssignmentArea
                                                message = funcs.CleanString (message)
                                                logging.debug("AssignmentArea  :" + job['AssignmentArea'])
                                                job['parse_assignment_area'] = True
                                            else:
                                                logging.debug("No match for Assignment Area")
                                                                                                                                                                            
                                            # Dispatch channel
                                            expression = "DISP[0-9]{1,} "
                                            search_response = re.search(expression, message)      # extract DispatchChannel
                                            if (search_response != None):
                                                job['DispatchChannel'] = search_response.group(0)
                                                message = re.sub(expression, '', message)         # remove DispatchChannel
                                                message = funcs.CleanString (message)
                                                job['DispatchChannel'] = job['DispatchChannel'].replace ("DISP", "")
                                                logging.debug("Dispatch channel:" + job['DispatchChannel'])
                                                job['parse_dispatch_channel'] = True
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
                                            job['MapRef'] = None
                                            if (Map_Melways == None and Map_SV == None):
                                                logging.debug("No match for Map ref")                                                
                                            else:
                                                job['parse_mapbook'] = True
                                                if (Map_Melways != None):
                                                    job['MapRef'] = Map_Melways
                                                else:
                                                    job['MapRef'] = Map_SV
                                                logging.debug("Map ref         :" + job['MapRef'])
                                            
                                            # parse lat/long
                                            expression = '(-?[0-9]{2,}[.]{1,}[0-9]{3,}),?\s([0-9]{2,}[.]{1,}[0-9]{3,})'
                                            job['latitude'] = None
                                            job['longitude'] = None
                                            search_response = re.search (expression, message)  # extract lat/lon
                                            if (search_response != None):
                                                LatLon = search_response.group(0)
                                                message = re.sub(expression, '', message)
                                                message = re.sub('LAT/LON:', '', message)
                                                message = funcs.CleanString (message)
                                                job['latitude'], job['longitude'] = LatLon.split(',')
                                                job['latitude'] = job['latitude'].strip()
                                                job['longitude'] = job['longitude'].strip()
                                                logging.debug("Latitude        :" + job['latitude'])
                                                logging.debug("Longitude       :" + job['longitude'])
                                                job['parse_lat_long'] = True
                                            else:
                                                logging.debug("No match for Lat/Long")
                                                                                            
                                            
                                            logging.debug ("Remaining msg   :" + message)
                                        else:
                                            logging.debug ("Not a FIRECALL")
                                            
                                        logging.debug ("job['parse_alert']            :" + str(job['parse_alert']))
                                        logging.debug ("job['parse_f_number']         :" + str(job['parse_f_number']))
                                        logging.debug ("job['parse_incident_type']    :" + str(job['parse_incident_type']))
                                        logging.debug ("job['parse_assignment_area']  :" + str(job['parse_assignment_area']))
                                        logging.debug ("job['parse_dispatch_channel'] :" + str(job['parse_dispatch_channel']))
                                        logging.debug ("job['parse_mapbook']          :" + str(job['parse_mapbook']))
                                        logging.debug ("job['parse_lat_long']         :" + str(job['parse_lat_long']))
                                        
                                        for keys,values in job.items():
                                            logging.debug("%s:%s" % (keys, values))
                                        
                                        # process the job
                                        # populate the flight info text box
                                        if (job['parse_lat_long'] and job['parse_dispatch_channel']):
                                            job['distance'], job['bearing'] = calcs.get_distance_and_bearing (job['airfield']['lat'], job['airfield']['lng'], job['latitude'], job['longitude'])
                                            job['buffer_flight_info'] = ("** FLIGHT DATA**\nDistance : %s\nBearing : %s\nDispatch: %s" % (str(job['distance']), str(job['bearing']), job['DispatchChannel']))
                                        else:
                                            job['buffer_flight_info'] = 'Error extracting flight details.\n\nPossible causes;\n-Not an ALERT page\n-Problem with Lat/Long\n-Problem with dispatch channel'
                                        
                                        
                                        # update weather information
                                        if (job['parse_alert']):
                                            job['b_dfwb'], job['fwb'] = weather.download_fire_weather_bulletin()

                                        # update image
                                        #if (job['parse_lat_long']):
                                        #    self.populateMapRoute(self.imageMapRoute, job['airfield']['lat'], job['airfield']['lng'], job['latitude'], job['longitude'])
                                        #    self.populateMapDestination(self.imageMapDestination, job['airfield']['lat'], job['airfield']['lng'], job['latitude'], job['longitude'])
                                        #else:
                                        #    pass

                                        
                                        
                                        
                                        # add it to the list
                                        jobs.append(job)
                                        
                                        
                                        self.update_screen(job)
                                        
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
        self.tbClosestPDD = self.builder.get_object("tbClosestPDD")
        self.tbTimeSincePage = self.builder.get_object("tbTimeSincePage")
        self.tbTimeOfPage = self.builder.get_object("tbTimeOfPage")
        self.comboAirfield = self.builder.get_object("comboAirfield")
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