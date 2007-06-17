import pygtk
pygtk.require("2.0")
import gtk
from gobject import *

class ToggleComboBox (gtk.ToggleButton):

    __gsignals__ = {'changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_INT,))}

    def __init__ (self):
        gtk.ToggleButton.__init__(self)
        self.set_relief(gtk.RELIEF_NONE)
        
        self.label = label = gtk.Label()
        label.set_alignment(0, 0.5)
        self.hbox = hbox = gtk.HBox()
        self.image = gtk.Image()
        hbox.pack_start(self.image, False, False)
        hbox.pack_start(label)
        arrow = gtk.Arrow (gtk.ARROW_DOWN, gtk.SHADOW_OUT);
        hbox.pack_start(arrow, False, False)
        self.add(hbox)
        self.show_all()
        
        self.connect("button_press_event", self.button_press)
        self.connect("key_press_event", self.key_press)
        self.connect("scroll_event", self.scroll_event)
        
        self.menu = menu = gtk.Menu()
        deactivate = lambda w: self.set_active(False)
        menu.connect("deactivate", deactivate)
        menu.attach_to_widget(self, None)
        
        self.markup = "", ""
        
        self._active = -1
        self._items = []
    
    def _get_active(self):
        return self._active
    
    def _set_active(self, active):
        if active == self._active: return
        oldactive = self._active
        self._active = active
        self.emit("changed", oldactive)
        self.set_sensitive(True)
        text, iconname = self._items[self.active]
        self.label.set_markup (self.markup[0] + text + self.markup[1])
        if iconname != None:
            self.hbox.set_spacing(6)
            self.image.set_from_pixbuf(gtk.icon_theme_get_default().load_icon (
                            iconname, 12, gtk.ICON_LOOKUP_USE_BUILTIN))
        else:
            self.hbox.set_spacing(0)
            self.image.clear()
    active = property(_get_active, _set_active)
    
    def setMarkup(self, start, end):
        self.markup = (start, end)
        text = self._items[self.active][0]
        self.label.set_markup (self.markup[0] + text + self.markup[1])
        
    def getMarkup(self):
        return self.markup
    
    def addItem (self, text, stock=None):
        if stock == None:
            item = gtk.MenuItem(text)
        else:
            item = gtk.MenuItem()
            label = gtk.Label(text)
            label.props.xalign = 0
            pix = gtk.icon_theme_get_default().load_icon(
                    stock, 12, gtk.ICON_LOOKUP_USE_BUILTIN)
            image = gtk.Image()
            image.set_from_pixbuf(pix)
            hbox = gtk.HBox()
            hbox.set_spacing(6)
            hbox.pack_start(image, expand=False, fill=False)
            hbox.add(label)
            item.add(hbox)
            hbox.show_all()
        
        item.connect("activate", self.menu_item_activate, len(self._items))
        self.menu.append(item)
        self._items += [(text, stock)]
        item.show()
        if self.active < 0: self.active = 0
    
    def menuPos (self, menu):
        x, y = self.window.get_origin()
        x += self.get_allocation().x
        y += self.get_allocation().y + self.get_allocation().height
        return (x,y,False)
    
    def scroll_event (self, widget, event):
        if event.direction == gtk.gdk.SCROLL_UP:
            if self.active > 0:
                self.active -= 1
        else:
            if self.active < len(self._items)-1:
                self.active += 1
    
    def button_press (self, widget, event):
        width = self.allocation.width
        self.menu.set_size_request(-1,-1)
        ownWidth = self.menu.size_request()[0]
        self.menu.set_size_request(max(width,ownWidth),-1)
        self.set_active(True)
        self.menu.popup(None,None, self.menuPos, 1, event.time)
    
    from gtk.gdk import keyval_from_name
    keys = map(keyval_from_name,("space", "KP_Space", "Return", "KP_Enter"))
    def key_press (self, widget, event):
        if not event.keyval in self.keys: return
        self.set_active(True)
        self.menu.popup(None,None, self.menuPos, 1, event.time)
        return True
    
    def menu_item_activate (self, widget, index):
        self.active = index
