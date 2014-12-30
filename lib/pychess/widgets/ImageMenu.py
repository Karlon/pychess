from __future__ import print_function
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

class ImageMenu(Gtk.EventBox):
    def __init__ (self, image, child):        
        GObject.GObject.__init__(self)
        self.add(image)
        
        self.subwindow = Gtk.Window()
        self.subwindow.set_decorated(False)
        self.subwindow.set_resizable(False)
        self.subwindow.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.subwindow.add(child)        
        self.subwindow.connect_after("draw", self.__sub_onExpose)
        self.subwindow.connect("button_press_event", self.__sub_onPress)
        self.subwindow.connect("motion_notify_event", self.__sub_onMotion)
        self.subwindow.connect("leave_notify_event", self.__sub_onMotion)
        self.subwindow.connect("delete-event", self.__sub_onDelete)
        self.subwindow.connect("focus-out-event", self.__sub_onFocusOut)
        child.show_all()
        
        self.setOpen(False)
        self.connect("button_press_event", self.__onPress)
    
    def setOpen (self, isopen):
        self.isopen = isopen
        
        if isopen:
            topwindow = self.get_parent()
            while not isinstance(topwindow, Gtk.Window):
                topwindow = topwindow.get_parent()
            x, y = topwindow.get_window().get_position()
            x += self.get_allocation().x + self.get_allocation().width
            y += self.get_allocation().y
            self.subwindow.move(x, y)
        
        self.subwindow.props.visible = isopen
        self.set_state(self.isopen and Gtk.StateType.SELECTED or Gtk.StateType.NORMAL)
    
    def __onPress (self, self_, event):
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            self.setOpen(not self.isopen)
    
    
    def __sub_setGrabbed (self, grabbed):
        if grabbed and not Gdk.pointer_is_grabbed():
            Gdk.pointer_grab(self.subwindow.get_window(), True, 
                                 Gdk.EventMask.LEAVE_NOTIFY_MASK|
                                 Gdk.EventMask.POINTER_MOTION_MASK|
                                 Gdk.EventMask.BUTTON_PRESS_MASK,
                                 None, None, Gdk.CURRENT_TIME)
            Gdk.keyboard_grab(self.subwindow.get_window(), True, Gdk.CURRENT_TIME)
        elif Gdk.pointer_is_grabbed():
            Gdk.pointer_ungrab(Gdk.CURRENT_TIME) 
            Gdk.keyboard_ungrab(Gdk.CURRENT_TIME)
    
    def __sub_onMotion (self, subwindow, event):
        a = subwindow.get_allocation()
        self.__sub_setGrabbed(not (0 <= event.x < a.width and 0 <= event.y < a.height))
    
    def __sub_onPress (self, subwindow, event):
        a = subwindow.get_allocation()
        if not (0 <= event.x < a.width and 0 <= event.y < a.height):
            Gdk.pointer_ungrab(event.time)
            self.setOpen(False)
    
    def __sub_onExpose (self, subwindow, ctx):
        a = subwindow.get_allocation()
        context = subwindow.get_window().cairo_create()
        context.set_line_width(2)
        context.rectangle (a.x, a.y, a.width, a.height)
        sc = self.get_style_context()
        found, color = sc.lookup_color("p_dark_color")
        context.set_source_rgba(*color)
        context.stroke()
        self.__sub_setGrabbed(self.isopen)
    
    def __sub_onDelete (self, subwindow, event):
        self.setOpen(False)
        return True
    
    def __sub_onFocusOut (self, subwindow, event):
        self.setOpen(False)

def switchWithImage (image, dialog):
    parent = image.get_parent()
    parent.remove(image)
    imageMenu = ImageMenu(image, dialog)
    parent.add(imageMenu)
    imageMenu.show()

if __name__ == "__main__":
    win = Gtk.Window()
    vbox = Gtk.VBox()
    vbox.add(Gtk.Label(label="Her er der en kat"))
    image = Gtk.Image.new_from_icon_name("gtk-properties", Gtk.IconSize.BUTTON)
    vbox.add(image)
    vbox.add(Gtk.Label(label="Her er der ikke en kat"))
    win.add(vbox)
    
    table = Gtk.Table(2, 2)
    table.attach(Gtk.Label(label="Minutes:"), 0, 1, 0, 1)
    spin1 = Gtk.SpinButton(Gtk.Adjustment(0,0,100,1))
    table.attach(spin1, 1, 2, 0, 1)
    table.attach(Gtk.Label(label="Gain:"), 0, 1, 1, 2)
    spin2 = Gtk.SpinButton(Gtk.Adjustment(0,0,100,1))
    table.attach(spin2, 1, 2, 1, 2)
    table.set_border_width(6)
    
    switchWithImage(image, table)
    def onValueChanged (spin):
        print(spin.get_value())
    spin1.connect("value-changed", onValueChanged)
    spin2.connect("value-changed", onValueChanged)
    
    win.show_all()
    win.connect("delete-event", Gtk.main_quit)
    Gtk.main()
