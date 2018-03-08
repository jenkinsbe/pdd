from bs4 import BeautifulSoup
import re
import weather


import logging
from logging.handlers import TimedRotatingFileHandler

log_file_name = '/home/pi/pdd/logs/pdd.log'
logging_level = logging.DEBUG
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s', "%Y-%m-%d %H:%M:%S")
handler = logging.handlers.TimedRotatingFileHandler(log_file_name,  when='midnight')
handler.suffix = '%Y_%m_%d.log'
handler.setFormatter(formatter)
logger = logging.getLogger() # or pass string to give it a name
logger.addHandler(handler)
logger.setLevel(logging_level)

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', "%Y-%m-%d %H:%M:%S")
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

success, fwb = weather.download_fire_weather_bulletin()
aws = 'Deniliquin'

def CleanString (str):
    str = str.replace ("  ", " ")
    str = str.lstrip()
    return str

if (success):
    soup = BeautifulSoup (fwb, 'html.parser')
    logger.debug ('AWS for parsing is %s' % aws)

    if (soup is not None):
        if (aws is not None):

            # get the FWB time
            aws_time = 'TIME'        
            tags = soup.find_all('h3')
            for x in range (0, len(tags)):
                
                tag = tags[x].string
                if tag is not None:
                    if 'EDT' in tag:
                        
                        # remove <CR><LF> from string
                        tag = re.sub("\r\n", '', tag)   # remove ALERT
                        aws_time = tag
                        logger.debug(tag)
                        break
                    else:
                        logger.debug ('EDT not found')
                        
            # get the FWB wx data for AWS
            ffdi = -1
            gfdi = -1
            
            tags = soup.find_all('td')
            regex = re.compile("[^0-9]")

            
            for x in range (0, len(tags)):
                logger.debug (tags[x].string)
                tag = tags[x].string
                
                tag = CleanString(tag)
                
                if tag is not None:
                    if tag in aws:
                        logger.debug (tag)
                        logger.debug ('%s at %d' % (aws, x))
                        
                        ffdi = regex.sub ("", str(tags[x+11]))
                        logger.debug ('FFDI: %s' % ffdi)

                        gfdi = regex.sub ("", str(tags[x+12]))
                        logger.debug ('GFDI: %s' % gfdi)
                        break
else:
    logger.debug('weather.download_fire_weather_bulletin() FAILED')