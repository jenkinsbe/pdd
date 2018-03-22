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

import database
import calcs
import weather
import funcs
from widgetcontrol import WidgetControl, TextBuffer

widgets = dict()

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

    def on_window_destroy(self, object, data=None):
        print ("Quiting")
        Gtk.main_quit()
    
    def btnNextJob(self, object, data=None):
        print ("Next job")

    def btnPreviousJob(self, object, data=None):
        print ("Previous job")
        
    def airfield_changed(self, object, data=None):
        print ("Airfield changed")
        
        text = object.get_active_text()
        if text is not None:
            print ("Airfield selected is: %s" % text)

    def btnSendTestPage(self, object, data=None):
        pass
    
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
        self.comboAirfield = self.builder.get_object("comboAirfield")
        self.tbTimeSincePage = self.builder.get_object("tbTimeSincePage")
        self.imageMapRoute = self.builder.get_object("imageMapRoute")
        self.imageMapDestination = self.builder.get_object("imageMapDestination")
        
        #self.tbPagerMessage.create_tag("tag_Large", weight=Pango.Weight.BOLD, size=30 * Pango.SCALE)
        self.tbWeather.create_tag("tag_Bold", weight=Pango.Weight.BOLD)
        self.tbWeather.create_tag("tag_NoGo", foreground="red")
        self.tbWeather.create_tag("tag_Go", foreground="green")

        tbPagerMessage = self.builder.get_object("tbPagerMessage")
        logging.debug (tbPagerMessage)
        widgets['tbPagerMessage'] = TextBuffer(tbPagerMessage)
        logging.debug (widgets['tbPagerMessage'])
        widgets['tbPagerMessage'].create_tag("tag_Large", weight=Pango.Weight.BOLD, size=30 * Pango.SCALE)
        
        # show the message in the textbox
        widgets['tbPagerMessage'].set_text('')
        iter = widgets['tbPagerMessage'].get_iter_at_offset(0)
        GObject.idle_add(widgets['tbPagerMessage'].insert_with_tags_by_name, iter, message, "tag_Large", priority=GObject.PRIORITY_DEFAULT)

        self.window.queue_draw()
  
def run_gui():
    main = InterFace()
    main.show_all()
    main.startclocktimer()
    Gtk.main()

if __name__ == "__main__":
    run_gui()  