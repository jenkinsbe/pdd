import logging
import math
from operator import itemgetter

logger = logging.getLogger(__name__)

def get_distance_and_bearing(lat1, lon1, lat2, lon2):
    
    lat1 = float(lat1)
    lat2 = float(lat2)
    lon1 = float(lon1)
    lon2 = float(lon2)
    
    distance = get_distance(lat1, lon1, lat2, lon2)
    distance = math.ceil(float(distance))    
    distance = "%.0f Nm" % (distance)
    
    bearing = get_bearing(lat1, lon1, lat2, lon2)
    bearing = (int(bearing))
    bearing = "%.0f Mag" % (bearing)
    
    return distance, bearing
    

def get_distance(lat1, lon1, lat2, lon2):

    lat1 = float(lat1)
    lat2 = float(lat2)
    lon1 = float(lon1)
    lon2 = float(lon2)

    theta = lon1 - lon2
    dist = math.sin(math.radians(lat1)) * math.sin(math.radians(lat2)) +  math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(theta))
    dist = math.acos(dist)
    dist = math.degrees(dist)
    return (dist * 60 * 1.1515 * 0.8684)

def get_bearing(lat1, lon1, lat2, lon2): 		# uses rhumb line
    # difference in longitudinal coordinates
    dLon = math.radians(lon2) - math.radians(lon1)

    # difference in the phi of latitudinal coordinates
    dPhi = math.log(math.tan((math.radians(lat2) / 2) + (math.pi / 4)) / math.tan((math.radians(lat1) / 2) + math.pi / 4))
    
    # we need to recalculate dLon if it is greater than pi
    if(abs(dLon) > math.pi):
        if(dLon > 0):
            dLon = (2 * math.pi - dLon) * -1
        else:
            dLon = 2 * math.pi + dLon
    
    # return the angle, normalized
    return (math.degrees(math.atan2(dLon, dPhi)) + 360) % 360

def hms_string(seconds_elapsed):
    h = int(seconds_elapsed / (60 * 60))
    m = int((seconds_elapsed % (60 * 60)) / 60)
    s = seconds_elapsed % 60
    return "%02d:%02d:%02d" % (h, m, s)

def find_closest_airbases(firecall_lat, firecall_lng, unsorted_list):
  
    for x in range(0, len(unsorted_list)):
        
        if unsorted_list[x]['name'] is not None:
            unsorted_list[x]['distance'] = get_distance (firecall_lat, firecall_lng, float(unsorted_list[x]['lat']), float(unsorted_list[x]['lng']))
        else:
            unsorted_list[x]['distance'] = 9999999999
    
    #logger.debug (unsorted_list)
    
    sorted_list = [(dict_["distance"], dict_) for dict_ in unsorted_list]
    sorted_list.sort()
    result = [dict_ for (key, dict_) in sorted_list]

    #logger.debug (result)
    return result

