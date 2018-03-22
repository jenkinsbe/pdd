import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, Gio, Pango

from gi.repository import GObject
from ..overrides import override

class TextBuffer(Gtk.TextBuffer):
    
    def _get_or_create_tag_table(self):
        table = self.get_tag_table()
        if table is None:
            table = Gtk.TextTagTable()
            self.set_tag_table(table)

        return table
    
    def create_tag(self, tag_name=None, **properties):

        tag = Gtk.TextTag(name=tag_name, **properties)
        self._get_or_create_tag_table().add(tag)
        return tag
    
    def __init__ (self, WidgetInstance):
        self.__instance = WidgetInstance

TextBuffer = override(TextBuffer)
#__all__.append('TextBuffer')        
    
class WidgetControl(Gtk.Widget):
    def __init__(self, WidgetInstance):
        
        self.__instance = WidgetInstance
        
        if isinstance(WidgetInstance, Gtk.TextBuffer):
            self.widget_instance = TextBuffer(WidgetInstance)
        
#    def create_tag(self, name, *tags):
#        self.widget_instance.create_tag (name, tags)
        
#    def set_text(self, text=''):
#        self.widget_instance.set_text(text)
        
#    def get_iter_at_offset(self, offset):
#        return self.widget_instance.get_iter_at_offset(offset)
    
    
        