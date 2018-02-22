#!/usr/bin/env python3

import serial
import sys
import re
import requests # pip install requests
from time import localtime, strftime
import time
from collections import deque
import logging
from logging.handlers import TimedRotatingFileHandler


FirecallList = deque([])



log_file_name = '/home/pi/eas/logs/eas.log'
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
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', "%Y-%m-%d %H:%M:%S")
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)



if sys.version_info<(3,4,2):
  sys.stderr.write("You need python 3.4.2 or later to run this script\n")
  exit(1)



def InitSerialPort():
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


def ProcessMessages():    
    
    logging.debug ("Processing messages for upload")
    
    url = 'http://www.inthehills.com.au/fdi/dbinterface2.php'

    # len(filter(lambda x: x == 1, d))
    l = list(FirecallList).count(1)
    logging.debug ("Queue length is " + str(l))
    while (l > 0):
        JobToProcess = FirecallList.popleft()
        while True:
            r = requests.post(url, JobToProcess)
            if (r.status_code == requests.codes.ok):
                logging.info ("Job was successfully uploaded")
                break
            else:
                logging.error ("Upload failed...trying again in 5 seconds")
                logging.error ("Response code was : " + str(r.status_code))
                time.sleep(5)       # wait 5 seconds before trying so we dont "smash" the server

    
def QueueMessageToUpload (capcode, priority, Fnumber, AssignmentArea, IncidentType, MapRef, message, raw):
    JobToProcess = dict(
        time=strftime("%Y-%m-%d %H:%M:%S", localtime()),
        capcode=capcode,
        capcodetext='',
        priority=priority,
        jobnumber=Fnumber,
        brigadearea=AssignmentArea,
        calltype=IncidentType,
        details=message,
        mapref=MapRef,
        raw=raw)
    
    url = 'http://www.inthehills.com.au/fdi/dbinterface2.php'
    while True:
        r_stat_code = 0
        try:
            r = requests.post(url, JobToProcess, timeout=5)
            r_stat_code = r.status_code
            if (r.status_code == requests.codes.ok):
                logging.debug ("Job was successfully uploaded")
                break
            else:
                logging.error ("Upload failed...Return code: " + str(r_stat_code))
        except requests.exceptions.Timeout:
            logging.error ("Upload failed...Timeout error")
        except requests.exceptions.TooManyRedirects:
            logging.error ("Upload failed...TooManyRedirects error")
        except requests.exceptions.RequestException as e:
            logging.error ("Upload failed...trying again in 5 seconds")

        logging.info ("Response code was : " + str(r_stat_code))
        time.sleep(5)       # wait 5 seconds before trying so we dont "smash" the server


def CleanString (str):
    str = str.replace ("  ", " ")
    str = str.lstrip()
    return str


    
logging.info('')
logging.info('-----------------------------------------------')
logging.info('Application started')

ser = InitSerialPort()

parse_msg = ''
message = ''

try:

    while True:
        # read any new incoming bytes and append them to the message
        try:
            bytesToRead = ser.inWaiting()

            if bytesToRead > 0:
                try:
                    ch = ser.read(1)
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
                            message = parse_msg[:length-2]      # only keep the message, not the \r\n
                            parse_msg = ''

                            message = message.replace ('\r','')     # strip out any other \r
                            message = message.replace ('\n','')     # strip out any other \n
                            
                            if (len(message) > 11):                  # at least the capcode and priority
        
                                priority = message[9:11]
                                if (priority == "@@"):
                                    
                                    # log the message
                                    logging.debug (message)

                                    # extract the capcode
                                    capcode = message[0:9]
                                    message = message[9:]
                                    logging.debug("Capcode         :" + capcode)
                                    
                                    # extract the priority
                                    priority = "EMERG"
                                    message = message[2:]
                                    raw = message       # keep copy of stripped message
                                    logging.debug("Priority        :" + priority)
                                    
                                    firecall = True             # true by default
                                    parseOK = True
                                    
                                    if ((re.search("ALERT.{1,}", message) != None) and (re.search("F[0-9]{1,}", message) != None)):
                                        logging.debug ("FIRECALL page received")
                                        logging.info (raw)
                                        
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
                                        expression = "\\b(ALARC1|ALARC3|STRUC1|STRUC3|INCIC1|INCIC3|NOSTC1|NOSTC3|G&SC1|G&SC3|NS&RC1|NS&RC3|RESCC1|RESCC3|CONFC1|CONFC3|HIARC1|HIARC3|STCOC1|STCOC3|AFEMR|AFPEMR|STRIKE)\\b"
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
                                            logging.debug("No match for AssignmentArea")
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
                                        
                                    else:
                                        logging.debug ("Not a FIRECALL")
                                        firecall = False
                                        
                                        
                                    logging.debug("parseOK  :" + str(parseOK))

                                    if (parseOK == True and firecall == True):
                                        QueueMessageToUpload (capcode, priority, Fnumber, AssignmentArea, IncidentType, MapRef, message, raw)
        except serial.SerialException as e:
            pass
                                
except KeyboardInterrupt:
    pass

ser.close()

# Steps to commission new RPI3 to make EAS work
# - turn off serial terminal in raspi-config
# - update hostname via raspi-config
# - /boot/config.txt set enable_uart=1
# - pip3 install update pyserial (to 3.4)
# - make autorun.sh batch file
# - (sudo nano /home/pi/.config/lxsession/LXDE-pi/autostart) and add (@lxterminal -e "/home/pi/eas/autorun.sh") to the bottom
