import gtk
import pango

from pychess.Utils.const import *
from pychess.System.prefix import addDataPrefix
from pychess.System.glock import glock_connect

__title__ = _("Annotation")
__active__ = True
__icon__ = addDataPrefix("glade/panel_moves.svg")
__desc__ = _("Annotated game")


class Sidepanel(gtk.TextView):
    def __init__(self):
        gtk.TextView.__init__(self)
        
        self.set_editable(False)
        self.set_cursor_visible(False)
        self.set_wrap_mode(gtk.WRAP_WORD)

        self.cursor_standard = gtk.gdk.Cursor(gtk.gdk.LEFT_PTR)
        self.cursor_hand = gtk.gdk.Cursor(gtk.gdk.HAND2)
        
        self.textview = self
        
        self.nodeIters = []
        self.oldWidth = 0
        
        self.connect("motion-notify-event", self.motion_notify_event)
        self.connect("button-press-event", self.button_press_event)
        self.connect("expose-event", self.on_expose)
        
        self.textbuffer = self.get_buffer()
        
        self.textbuffer.create_tag("head1")
        self.textbuffer.create_tag("head2", weight=pango.WEIGHT_BOLD)
        self.textbuffer.create_tag("node", weight=pango.WEIGHT_BOLD)
        self.textbuffer.create_tag("comment", foreground="darkblue")
        self.textbuffer.create_tag("variation-toplevel")
        self.textbuffer.create_tag("variation-even", foreground="darkgreen", style="italic")
        self.textbuffer.create_tag("variation-uneven", foreground="darkred", style="italic")
        self.textbuffer.create_tag("selected", background_full_height=True, background="black", foreground="white")
        self.textbuffer.create_tag("margin", left_margin=4)
        self.textbuffer.create_tag("variation-margin", left_margin=20)

    def load (self, gmwidg):
        __widget__ = gtk.ScrolledWindow()
        __widget__.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS) #AUTOMATIC)
        __widget__.add(self.textview)

        self.boardview = gmwidg.board.view
        self.boardview.connect("shown_changed", self.shown_changed)

        self.gamemodel = gmwidg.board.view.model
        glock_connect(self.gamemodel, "game_loaded", self.game_loaded)

        return __widget__

    def motion_notify_event(self, widget, event):
        if (event.is_hint):
            (x, y, state) = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state
            
        if self.textview.get_window_type(event.window) != gtk.TEXT_WINDOW_TEXT:
            event.window.set_cursor(self.cursor_standard)
            return True
            
        (x, y) = self.textview.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET, int(x), int(y))
        it = self.textview.get_iter_at_location(x, y)
        offset = it.get_offset()
        for ni in self.nodeIters:
            if offset >= ni["start"] and offset < ni["end"]:
                event.window.set_cursor(self.cursor_hand)
                return True
        event.window.set_cursor(self.cursor_standard)
        return True

    def button_press_event(self, widget, event):
        (wx, wy) = event.get_coords()
        
        (x, y) = self.textview.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET, int(wx), int(wy))
        it = self.textview.get_iter_at_location(x, y)
        offset = it.get_offset()
        for ni in self.nodeIters:
            if offset >= ni["start"] and offset < ni["end"]:
#                self.board.load_node(ni["node"])
# TODO
                self.boardview.shown = self.gamemodel.nodes.index(ni["node"])
                self.update_selected_node()
                break
        return True

    # Update the selected node highlight
    def update_selected_node(self):
        self.textbuffer.remove_tag_by_name("selected", self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter())
        
        start = None    
        for ni in self.nodeIters:
# TODO
#            if ni["node"] == self.board.node:
            if ni["node"] == self.gamemodel.nodes[self.boardview.shown]:
                start = self.textbuffer.get_iter_at_offset(ni["start"])
                end = self.textbuffer.get_iter_at_offset(ni["end"])
                self.textbuffer.apply_tag_by_name("selected", start, end)
                break
        
        if start:
            self.textview.scroll_to_iter(start, 0, use_align=False, yalign=0.1)
    
    # Recursively insert the node tree
    def insert_nodes(self, node, level=0, ply=0, result=None):
        buf = self.textbuffer
        end_iter = buf.get_end_iter # Convenience shortcut to the function
        new_line = False
        
        while (1): 
            start = end_iter().get_offset()
            
            if not node:
                break
            
            if not node.move:
                node = node.next
                continue
            
            if ply > 0 and not new_line:
                buf.insert(end_iter(), " ")
            
            ply += 1
            buf.insert(end_iter(), node.move + " ")
            
            startIter = buf.get_iter_at_offset(start)
            endIter = buf.get_iter_at_offset(end_iter().get_offset())
            
            if level == 0:
                buf.apply_tag_by_name("node", startIter, endIter)
            elif level == 1:
                buf.apply_tag_by_name("variation-toplevel", startIter, endIter)
            elif level % 2 == 0:
                buf.apply_tag_by_name("variation-even", startIter, endIter)
            else:
                buf.apply_tag_by_name("variation-uneven", startIter, endIter)

            buf.apply_tag_by_name("margin", startIter, endIter)
# TODO      
#            if node == self.board.node:
            if node == self.gamemodel.nodes[self.boardview.shown]:
                buf.apply_tag_by_name("selected", startIter, endIter)
            
            ni = {}
            ni["node"] = node
            ni["start"] = startIter.get_offset()        
            ni["end"] = end_iter().get_offset()
            self.nodeIters.append(ni)
            
            # Comments
            if len(node.comments) > 0:
                for comment in node.comments:
                    self.insert_comment(comment, level)

            new_line = False

            # Variations
            if level == 0 and len(node.variations):
                buf.insert(end_iter(), "\n")
                new_line = True
            
            for var in node.variations:
                if level == 0:
                    buf.insert_with_tags_by_name(end_iter(), "[", "variation-toplevel", "variation-margin")
                elif (level+1) % 2 == 0:
                    buf.insert_with_tags_by_name(end_iter(), " (", "variation-even", "variation-margin")
                else:
                    buf.insert_with_tags_by_name(end_iter(), " (", "variation-uneven", "variation-margin")
                
                self.insert_nodes(var[0], level+1, ply-1)

                if level == 0:
                    buf.insert(end_iter(), "]\n")
                elif (level+1) % 2 == 0:
                    buf.insert_with_tags_by_name(end_iter(), ") ", "variation-even", "variation-margin")
                else:
                    buf.insert_with_tags_by_name(end_iter(), ") ", "variation-uneven", "variation-margin")
            
            if node.next:
                node = node.next
            else:
                break

        if result:
            buf.insert_with_tags_by_name(end_iter(), " "+result, "node")

    def insert_comment(self, comment, level=0):
        buf = self.textbuffer
        end_iter = buf.get_end_iter
        if level > 0:
            buf.insert_with_tags_by_name(end_iter(), comment, "comment", "margin")
        else:
            buf.insert_with_tags_by_name(end_iter(), comment, "comment")
        buf.insert(end_iter(), " ")

    def insert_header(self, gm):
        buf = self.textbuffer
        end_iter = buf.get_end_iter
        buf.insert(end_iter(), "\n")
        text = ""
        event = gm.tags['Event']
        if event:
            text +=  event
        site = gm.tags['Site']
        if site:
            text += ', ' + site
        game_date = gm.tags['Date']
        if game_date:
            text += ', ' + game_date
        buf.insert_with_tags_by_name(end_iter(), text, "head1")
        buf.insert(end_iter(), "\n")
        text = gm.tags['White'] + ' - ' + gm.tags['Black'] + ' ' + gm.tags['Result']
        buf.insert_with_tags_by_name(end_iter(), text, "head2")
        buf.insert(end_iter(), "\n\n")

    def on_expose(self, widget, data):
        w = self.textview.get_allocation().width
        if not w == self.oldWidth:
            self.update()
            self.oldWidth = w
    
    # Update the entire notation tree
    def update(self):
        self.textbuffer.set_text('')
        self.nodeIters = []
        if len(self.gamemodel.nodes) > self.gamemodel.lowply:
            self.insert_header(self.gamemodel)
            if self.gamemodel.comment:
                self.insert_comment(self.gamemodel.comment)
            self.insert_nodes(self.gamemodel.nodes[self.gamemodel.lowply], result=reprResult[self.gamemodel.status])

    def game_loaded(self, model, uri):
        self.update()
            
    def shown_changed (self, board, shown):
        self.update_selected_node()
