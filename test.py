import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject
import time
from threading import Thread

class InterFace(Gtk.Window):

    def __init__(self):

        Gtk.Window.__init__(self, title="Test 123")

        maingrid = Gtk.Grid()
        maingrid.set_border_width(10)
        self.add(maingrid)

        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.set_hexpand(True)
        scrolledwindow.set_vexpand(True)
        scrolledwindow.set_min_content_height(50)
        scrolledwindow.set_min_content_width(150)
        maingrid.attach(scrolledwindow, 0,0,1,1)

        self.textfield = Gtk.TextView()
        self.textbuffer = self.textfield.get_buffer()
        self.textbuffer.set_text("Let's count monkeys")
        self.textfield.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolledwindow.add(self.textfield)

        # 1. define the tread, updating your text
        self.update = Thread(target=self.counting_monkeys)
        # 2. Deamonize the thread to make it stop with the GUI
        self.update.setDaemon(True)
        # 3. Start the thread
        self.update.start()

    def counting_monkeys(self):
        # replace this with your thread to update the text
        n = 1
        while True:
            time.sleep(2)
            newtext = str(n)+" monkey" if n == 1 else str(n)+" monkeys"
            GObject.idle_add(
                self.textbuffer.set_text, newtext,
                priority=GObject.PRIORITY_DEFAULT
                )
            n += 1

def run_gui():
    window = InterFace()
    # 4. this is where we call GObject.threads_init()
    GObject.threads_init()
    window.show_all()
    Gtk.main()

run_gui()