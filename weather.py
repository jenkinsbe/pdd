from base64 import b64encode
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import re
import funcs
import logging
logger = logging.getLogger(__name__)


def download_fire_weather_bulletin():
    
    bom_url = 'https://reg.bom.gov.au/products/reg/vicfire/IDV60236.shtml'
    bom_username = 'bomw0026'
    bom_password = 'cfa123'
    
    data = urlencode(dict(Body='This is a test')).encode('ascii')
    headers = {'Authorization': b'Basic ' + b64encode((bom_username + ':' + bom_password).encode('utf-8'))}
    cafile = 'cacert.pem' # http://curl.haxx.se/ca/cacert.pem
    
    try:
        response = urlopen(Request(bom_url, data, headers), cafile=cafile)
        return True, response.read().decode()

    except:
        return False, None

def parse_wx_from_fwb(soup, aws):
    
    logger.debug ('AWS for parsing is %s' % aws)
    b_return = False

    if (soup is not None):
        if (aws is not None):

            # get the FWB time
            aws_time = 'TIME'        
            tags = soup.find_all('h3')
            for x in range (0, len(tags)):
                tag = tags[x].string
                if tag is not None:
                    if 'EDT' in tag:
                        
                        tag = re.sub("\r\n", '', tag)   # remove <CR><LF> from string
                        tag = re.sub("At ", '', tag)    # remove 'At ' from start of string
                        tag = re.sub("  ", ' ', tag)    # remove double spaces
                        aws_time = tag
                        logger.debug(tag)
                        break
                    else:
                        logger.debug ('EDT not found')
                        break
    
    
            # get the FWB wx data for AWS
            ffdi = -1
            gfdi = -1
            
            tags = soup.find_all('td')
            regex = re.compile("[^0-9]")

            
            for x in range (0, len(tags)):
                tag = tags[x].string
                tag = funcs.CleanString(tag)
                
                if tag is not None:
                    if tag in aws:
                        logger.debug ('%s at %d' % (aws, x))
                        
                        ffdi = regex.sub ("", str(tags[x+11]))
                        logger.debug ('FFDI: %s' % ffdi)

                        gfdi = regex.sub ("", str(tags[x+12]))
                        logger.debug ('GFDI: %s' % gfdi)
                        
                        b_return = True
                        break
                    
        else:
            logger.debug ('No AWS selected for parsing')
    else:
        logger.debug ('No soup object available for parsing')

    return b_return, aws_time, int(ffdi), int(gfdi)
