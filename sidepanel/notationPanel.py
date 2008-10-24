import gtk
import pango

from pychess.System.prefix import addDataPrefix

__title__ = _("Annotation")
__active__ = True
__icon__ = addDataPrefix("glade/panel_moves.svg")
__desc__ = _("Annotated game")

RIGHT_MARGIN = 2        # Textview margin for our custom line wrapping


class Sidepanel(gtk.TextView):
    def __init__(self):
        gtk.TextView.__init__(self)
        
        self.set_editable(False)
        self.set_cursor_visible(False)
        self.set_wrap_mode(gtk.WRAP_NONE)

        self.cursor_standard = gtk.gdk.Cursor(gtk.gdk.LEFT_PTR)
        self.cursor_hand = gtk.gdk.Cursor(gtk.gdk.HAND2)
        
        self.textview = self
        
###        self.board = board.Board()
        self.nodeIters = []
        self.oldWidth = 0
        
        self.connect("motion-notify-event", self.motion_notify_event)
        self.connect("button-press-event", self.button_press_event)
        self.connect("expose-event", self.on_expose)
        
        self.textbuffer = self.get_buffer()
        
        self.textbuffer.create_tag("node", weight=pango.WEIGHT_BOLD)
        self.textbuffer.create_tag("comment", foreground="darkred")
        self.textbuffer.create_tag("variation-toplevel")
        self.textbuffer.create_tag("variation-even", foreground="darkblue", style="italic")
        self.textbuffer.create_tag("variation-uneven", foreground="darkgreen")
        self.textbuffer.create_tag("selected", background_full_height=True, background="black", foreground="white")
        self.textbuffer.create_tag("margin", left_margin=20)

    def load (self, gmwidg):
        __widget__ = gtk.ScrolledWindow()
        __widget__.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        __widget__.add(self.textview)

        self.boardview = gmwidg.board.view
        self.boardview.connect("shown_changed", self.shown_changed)

        self.gamemodel = gmwidg.board.view.model

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
###                self.board.load_node(ni["node"])
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
        newLine = True
        lineInterrupted = False
        n = ply+1 / 2       # move number
        t = ""
        end_iter = buf.get_end_iter # Convenience shortcut to the function
        
        # if it's whites turn
        if ply % 2 == 0:
            c = True
        else:
            c = False
        
        while (1): 
            start = end_iter().get_offset()
            
            if not node:
                break
            
            if not node.move:
                node = node.next
                continue
                
            buf.insert(end_iter(), " ")
            
            dotsAdded = False   
            ply += 1
            if c:
                t = `(ply+1)/2` + "." + node.move
            else:
                if newLine:
                    t = `(ply+1)/2` + "..." + node.move
                elif lineInterrupted:
                    t = "..." + node.move
                    dotsAdded = True
                else:
                    t = node.move
                n += 1
                
            for annotation in node.annotations:
                # hack to support NAGs, which should be part of the move notation
                if annotation in ("", "!", "?", "!?", "?!", "!!", "??"):
                    t = t + annotation
                else:
                    t = t + " " + annotation
                
            newLine = False
            lineInterrupted = False
            
            buf.insert(end_iter(), t + " ")
            
            startIter = buf.get_iter_at_offset(start)
            endIter = buf.get_iter_at_offset(end_iter().get_offset())
            
            if level == 0:
                buf.apply_tag_by_name("node", startIter, endIter)
                tag = "node"
            elif level == 1:
                buf.apply_tag_by_name("variation-toplevel", startIter, endIter)
                tag = "variation-toplevel"
            elif level % 2 == 0:
                buf.apply_tag_by_name("variation-even", startIter, endIter)
                tag = "variation-even"
            else:
                buf.apply_tag_by_name("variation-uneven", startIter, endIter)
                tag = "variation-uneven"
            if level > 0:
                buf.apply_tag_by_name("margin", startIter, endIter)
# TODO      
#            if node == self.board.node:
            if node == self.gamemodel.nodes[self.boardview.shown]:
                buf.apply_tag_by_name("selected", startIter, endIter)
            
            # Custom wrapping hack
            width = self.textview.get_visible_rect().width
            startX = self.textview.get_iter_location(startIter).x
            endX = self.textview.get_iter_location(end_iter()).x
            if startX and (endX + RIGHT_MARGIN) > width:
                buf.insert(startIter, "\n")
                # Ugh...! "Necessary Evil"
                if not c:
                    startIter.forward_char()
                    if dotsAdded:
                        buf.insert_with_tags_by_name(startIter, `(ply+1)/2`, tag)
                    else:
                        buf.insert_with_tags_by_name(startIter, `(ply+1)/2`+"...", tag)
                    
                startIter = buf.get_iter_at_offset(start+1)
                
            ni = {}
            ni["node"] = node
            ni["start"] = startIter.get_offset()        
            ni["end"] = end_iter().get_offset()
            self.nodeIters.append(ni)
            
            # Comments
            if node.comment:
                lineInterrupted = True
                # For our custom wrapping hack, we split the line into words
                words = node.comment.split()
                for word in words:
                    start = end_iter().get_offset()
                    
                    cstr = " " + word
                    if level > 0:
                        buf.insert_with_tags_by_name(end_iter(), cstr, "comment", "margin")
                    else:
                        buf.insert_with_tags_by_name(end_iter(), cstr, "comment")
                    
                    startIter = buf.get_iter_at_offset(start)
                    
                    width = self.textview.get_visible_rect().width
                    endX = self.textview.get_iter_location(end_iter()).x
                    if (endX + RIGHT_MARGIN) > width:
                        buf.insert(startIter, "\n")
                buf.insert(end_iter(), " ")
                
            # Variations
            if level == 0 and len(node.variations):
                buf.insert(end_iter(), "\n")
                newLine = True
            elif len(node.variations):
                lineInterrupted = True
            
            for var in node.variations:
                if level == 0:
                    buf.insert_with_tags_by_name(end_iter(), " [", "variation-toplevel", "margin")
                elif (level+1) % 2 == 0:
                    buf.insert_with_tags_by_name(end_iter(), " (", "variation-even", "margin")
                else:
                    buf.insert_with_tags_by_name(end_iter(), " (", "variation-uneven", "margin")
                
                self.insert_nodes(var[0], level+1, ply-1)

                if level == 0:
                    buf.insert(end_iter(), "]\n")
                elif (level+1) % 2 == 0:
                    buf.insert_with_tags_by_name(end_iter(), ") ", "variation-even", "margin")
                else:
                    buf.insert_with_tags_by_name(end_iter(), ") ", "variation-uneven", "margin")
            
            if node.next:
                c = not c
                node = node.next
            else:
                break
        if result:
            buf.insert_with_tags_by_name(end_iter(), " "+result, tag)
        
    def on_expose(self, widget, data):
        w = self.textview.get_allocation().width
        if not w == self.oldWidth:
            self.update()
            self.oldWidth = w
    
    # Update the entire notation tree
    def update(self):
        self.textbuffer.set_text('')
        self.nodeIters = []
        if len(self.gamemodel.nodes) > 0:
            self.insert_nodes(self.gamemodel.nodes[0], result=self.gamemodel.result)
            
    def shown_changed (self, board, shown):
        self.update_selected_node()
