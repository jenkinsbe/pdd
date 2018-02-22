#!/usr/bin/env python
#
#import gtk
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject
import time
from threading import Thread


class InterFace(Gtk.Window):

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


    def counting_monkeys(self):
        # replace this with your thread to update the text
        n = 1
        while True:
            time.sleep(1)
            newtext = str(n)+" monkey" if n == 1 else str(n)+" monkeys"
            GObject.idle_add(
                self.tbPagerMessage.set_text, newtext,
                priority=GObject.PRIORITY_DEFAULT
                )
            n += 1
            
    def __init__(self):
        self.gladefile = "pdd_main.glade"
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("mainwindow")
        self.window.show()

        self.tbPagerMessage = self.builder.get_object("tbPagerMessage")
        self.tbWeather = self.builder.get_object("tbWeather")
        self.tbFlightPath = self.builder.get_object("tbFlightPath")
        self.tbClosestAirbase = self.builder.get_object("tbClosestAirbase")

        # 1. define the tread, updating your text
        self.update = Thread(target=self.counting_monkeys)
        # 2. Deamonize the thread to make it stop with the GUI
        self.update.setDaemon(True)
        # 3. Start the thread
        self.update.start()

  

  
def run_gui():
    main = InterFace()
    # 4. this is where we call GObject.threads_init()
    GObject.threads_init()
    main.show_all()
    Gtk.main()

if __name__ == "__main__":
    run_gui()  