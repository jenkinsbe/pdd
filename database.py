import logging
from threading import Lock
import sqlite3 as lite

logger = logging.getLogger(__name__)
db_lock = Lock()

def db_connect():
    conn_handle = None
    conn_handle = lite.connect('./db/pdd.db')
    if (conn_handle == None):
        logger.error ('Could not connect to database')
    #else:
        #logger.debug ('Connected to database')
    return conn_handle
    
def select (sql):
    
    logger.debug (sql)
    
    db_lock.acquire()
    b_return = False
    return_list = None
    return_size = 0
    
    db = db_connect()
    if (db ==  None):
        db_lock.release()
        return False, None, 0
    else:
        return_list = list()
        
        try:
            cursor = db.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                return_list.append(FetchOneRowAssoc(row, cursor))
            b_return = True
            return_size = len(return_list)
        except lite.Error as e:
            logger.error ("%s", e.args[0])
        finally:
            if db:
                db.close()
    db_lock.release()
    return b_return, return_list, return_size

def FetchOneRowAssoc(data, cursor):
    if data == None:
        return None
    desc = cursor.description
    
    dict = {}
    
    for (name, value) in zip(desc, data):
        dict[name[0]] = value
        
    return dict       
    