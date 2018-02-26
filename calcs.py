import logging
import math

logger = logging.getLogger(__name__)

def get_distance_and_bearing(lat1, lon1, lat2, lon2, unit='Nm'):
    
    lat1 = float(lat1)
    lat2 = float(lat2)
    lon1 = float(lon1)
    lon2 = float(lon2)
    
    distance = get_distance(lat1, lon1, lat2, lon2, unit)
    distance = math.ceil(float(distance))    
    distance = "%.0f %s" % (distance, unit)
    
    bearing = get_bearing(lat1, lon1, lat2, lon2)
    bearing = (int(bearing))
    bearing = "%.0f Mag" % (bearing)
    
    return distance, bearing
    

def get_distance(lat1, lon1, lat2, lon2, unit='Nm'):
    theta = lon1 - lon2
    dist = math.sin(math.radians(lat1)) * math.sin(math.radians(lat2)) +  math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(theta))
    dist = math.acos(dist)
    dist = math.degrees(dist)
    miles = dist * 60 * 1.1515
    unit = unit.upper()

    if (unit == "K"):
        return (miles * 1.609344)
    elif (unit == "Nm"):
        return (miles * 0.8684)
    else:
        return miles

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
