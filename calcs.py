import logging

logger = logging.getLogger(__name__)

def get_dist_and_bearing(lat1, lon1, lat2, lon2, unit='N'):
    
    distance = get_distance(lat1, lon1, lat2, lon2, unit)
    bearing = get_bearing(lat1, lon1, lat2, lon2)
    
    return distance, bearing
    

def get_distance(lat1, lon1, lat2, lon2, unit='N'):
{
	theta = lon1 - lon2
	dist = sin(deg2rad(lat1)) * sin(deg2rad(lat2)) +  cos(deg2rad(lat1)) * cos(deg2rad(lat2)) * cos(deg2rad(theta))
	dist = acos(dist)
	dist = rad2deg(dist)
	miles = dist * 60 * 1.1515
	unit = strtoupper(unit)

	if (unit == "K") 
	{
		return (miles * 1.609344)
	} 
	else if (unit == "N") 
	{
		return (miles * 0.8684)
	} 
	else 
	{
		return miles
	}
}

def get_bearing(lat1, lon1, lat2, lon2) 		// uses rhumb line
{
	//difference in longitudinal coordinates
	dLon = deg2rad(lon2) - deg2rad(lon1)

	//difference in the phi of latitudinal coordinates
	dPhi = log(tan(deg2rad(lat2) / 2 + pi() / 4) / tan(deg2rad(lat1) / 2 + pi() / 4))

	//we need to recalculate dLon if it is greater than pi
	if(abs(dLon) > pi()) 
	{
		if(dLon > 0) 
		{
			dLon = (2 * pi() - dLon) * -1
		}
		else 
		{
			dLon = 2 * pi() + dLon
		}
	}
	
	//return the angle, normalized
	return (rad2deg(atan2(dLon, dPhi)) + 360) % 360
}