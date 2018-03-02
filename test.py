from bs4 import BeautifulSoup
import re
import weather

fwb = weather.download_fire_weather_bulletin()
soup = BeautifulSoup (fwb, 'html.parser')

aws = 'Bendigo'
 
tags = soup.find_all('td')

regex = re.compile("[^0-9]")

for x in range (0, len(tags)):
    tag = tags[x].string.strip()
    
    #print (tag)
    
    if (tag == aws):
        print ('%s at %d' % (aws, x))
        
        ffdi = regex.sub ("", str(tags[x+11]))
        print ('FFDI: %s' % ffdi)

        gfdi = regex.sub ("", str(tags[x+12]))
        print ('GFDI: %s' % gfdi)
