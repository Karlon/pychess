import sys

import gtk
import gobject
import pango

from gtk.gdk import keyval_from_name

from BorderBox import BorderBox
from pychess.System import glock
from pychess.System import uistuff
from pychess.System.glock import glock_connect


class ConsoleWindow (object):
    def __init__ (self, widgets, connection):
        self.connection = connection

        self.window = gtk.Window()
        self.window.set_border_width(12)
        self.window.set_icon_name("pychess")
        self.window.set_title("FICS Console")
        self.window.connect("delete-event", lambda w,e: w.hide() or True)
        
        uistuff.keepWindowSize("consolewindow", self.window, defaultSize=(700,400))

        self.consoleView = ConsoleView(self.connection)
        self.window.add(self.consoleView)
        
        widgets["show_console_button"].connect("clicked", self.showConsole)
        connection.com.connect("consoleMessage", self.onConsoleMessage)
        glock_connect(connection, "disconnected",
                      lambda c: self.window and self.window.hide())

    def showConsole(self, *widget):
        self.window.show_all()
        self.window.present()
        self.consoleView.writeView.grab_focus()

        # scroll to the bottom
        adj = self.consoleView.sw.get_vadjustment()
        adj.set_value(adj.upper - adj.page_size)
        
    def onConsoleMessage(self, com, lines):
        for line in lines:
            # beep
            if line.line == chr(7):
                sys.stdout.write("\a")
                sys.stdout.flush()
                return
            if line.line and not line.line.startswith('<'):
                self.consoleView.addMessage(line.line)
        

class ConsoleView (gtk.VPaned):
    __gsignals__ = {
        'messageAdded' : (gobject.SIGNAL_RUN_FIRST, None, (str,str,object)),
        'messageTyped' : (gobject.SIGNAL_RUN_FIRST, None, (str,))
    }
    
    def __init__ (self, connection):
        gtk.VPaned.__init__(self)
        self.connection = connection
        
        # Inits the read view
        self.readView = gtk.TextView()
        fontdesc = pango.FontDescription("Monospace 10")
        self.readView.modify_font(fontdesc)
        
        self.textbuffer = self.readView.get_buffer()
        self.textbuffer.create_tag("text", foreground="black")
        self.textbuffer.create_tag("mytext", foreground="darkblue")

        self.sw = sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_NONE)
        uistuff.keepDown(sw)
        sw.add(self.readView)
        self.readView.set_editable(False)
        self.readView.set_cursor_visible(False)
        self.readView.props.wrap_mode = gtk.WRAP_WORD
        self.pack1(sw, resize=True, shrink=True)
        
        # Inits the write view
        self.history = []
        self.pos = 0
        self.writeView = gtk.Entry()
        #self.writeView.set_width_chars(80)
        self.pack2(self.writeView, resize=True, shrink=True)
        
        # Forces are reasonable position for the panner.
        def callback (widget, event):
            widget.disconnect(handle_id)
            allocation = widget.get_allocation()
            self.set_position(int(max(0.79*allocation.height, allocation.height-60)))
        handle_id = self.connect("expose-event", callback)
        
        self.writeView.connect("key-press-event", self.onKeyPress)

    
    def addMessage (self, text, my=False):
        glock.acquire()
        try:
            tb = self.readView.get_buffer()
            iter = tb.get_end_iter()
            # Messages have linebreak before the text. This is opposite to log
            # messages
            if tb.props.text:
                tb.insert(iter, "\n")
            tb = self.readView.get_buffer()
            tag = "mytext" if my else "text"
            tb.insert_with_tags_by_name(iter, text, tag)
        finally:
            glock.release()
   
    def onKeyPress (self, widget, event):
        if event.keyval in map(keyval_from_name,("Return", "KP_Enter")):
            if not event.state & gtk.gdk.CONTROL_MASK:
                buffer = self.writeView.get_buffer()
                self.connection.client.run_command(buffer.props.text)
                self.emit("messageTyped", buffer.props.text)
                self.addMessage(buffer.props.text, my=True)
                adj = self.sw.get_vadjustment()
                adj.set_value(adj.get_upper())
                
                # Maintain variables backup, it will be restored to fics on quit
                for var in self.connection.lvm.variablesBackup:
                    if buffer.props.text == "set %s" % var:
                        if self.connection.lvm.variablesBackup[var] == 0:
                            self.connection.lvm.variablesBackup[var] = 1
                        else:
                            self.connection.lvm.variablesBackup[var] = 0
                    elif buffer.props.text in ("set %s 1" % var, "set %s on" % var, "set %s true" % var):
                        self.connection.lvm.variablesBackup[var] = 1
                    elif buffer.props.text in ("set %s 0" % var, "set %s off" % var, "set %s false" % var):
                        self.connection.lvm.variablesBackup[var] = 0
                    elif buffer.props.text.startswith("set %s " % var):
                        parts = buffer.props.text.split()
                        if len(parts) == 3 and parts[2]:
                            self.connection.lvm.variablesBackup[var] = parts[2]

                # Maintain lists backup, it will be restored to fics on quit
                for list in self.connection.lvm.personalBackup:
                    if buffer.props.text.startswith("addlist %s " % var) or buffer.props.text.startswith("+%s " % var):
                        parts = buffer.props.text.split()
                        if len(parts) == 3 and parts[2]:
                            self.connection.lvm.personalBackup[var].add(parts[2])
                    if buffer.props.text.startswith("sublist %s " % var) or buffer.props.text.startswith("-%s " % var):
                        parts = buffer.props.text.split()
                        if len(parts) == 3 and parts[2]:
                            self.connection.lvm.personalBackup[var].discard(parts[2])

                self.history.append(buffer.props.text)
                buffer.props.text = ""
                self.pos = len(self.history)
                return True

        elif event.keyval == keyval_from_name("Up"):
            if self.pos > 0:
                buffer = self.writeView.get_buffer()
                self.pos -= 1
                buffer.props.text = self.history[self.pos]
            widget.grab_focus()
            return True

        elif event.keyval == keyval_from_name("Down"):
            buffer = self.writeView.get_buffer()
            if self.pos == len(self.history)-1:
                self.pos += 1
                buffer.props.text = ""
            elif self.pos < len(self.history):
                self.pos += 1
                buffer.props.text = self.history[self.pos]
            widget.grab_focus()
            return True
                
