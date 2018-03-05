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
aws = 'Shepparton'

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
else:
    logger.debug('weather.download_fire_weather_bulletin() FAILED')