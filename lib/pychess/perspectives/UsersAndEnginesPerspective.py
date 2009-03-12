import gtk

from pychess.System import uistuff
from pychess.System import prefix
from pychess.Players import HumanPrototype

from Perspective import Perspective

class UsersAndEnginesPerspective (Perspective):
    
    def __init__(self):
        Perspective.__init__(self)
        self.setName(_("Users and Engines"))
        self.setDescription("...")
        self.setIconImage(gtk.image_new_from_pixbuf(
                          gtk.icon_theme_get_default().load_icon(
                          "stock_people", 32, gtk.ICON_LOOKUP_USE_BUILTIN)))
        
        tree = self.getBrowseTree()
        tree.append_column(gtk.TreeViewColumn('', gtk.CellRendererText(), text=0))
        self.__model = gtk.ListStore(str)
        tree.set_model(self.__model)
        
        self.__notebook = gtk.Notebook()
        self.__notebook.props.show_tabs = False
        self.__notebook.props.show_border = False
        self.__mainWidgets = {}
        
        self.getWindow().add(self.__notebook)
        
        self.addHumanProfile(HumanPrototype.HumanPrototype())
        
        #for prototype in Users.getUsers():
        #    if prototype.__type__ == LOCAL:
        #        self.addHumanProfile(prototype)
        #    else: self.addEngineProfile(prototype)
    
    def show (self):
        pass
    
    def hide (self):
        pass
    
    def createToolbuttons(self):
        newhuman = gtk.ToolButton(label="New Human")
        newhuman.set_icon_name("gtk-add")
        newhuman.connect("clicked", self.__newHumanClicked)
        
        newengine = gtk.ToolButton(label="New Engine")
        newengine.set_icon_name("gtk-add")
        newengine.connect("clicked", lambda b: None)
        
        duplicate = gtk.ToolButton(label="Duplicate")
        duplicate.set_icon_name("gtk-copy")
        duplicate.connect("clicked", lambda b: None)
        
        sep1 = gtk.SeparatorToolItem()
        
        favorite = gtk.ToggleToolButton()
        favorite.props.label = "Favorite"
        favorite.set_icon_name("gtk-about")
        favorite.connect("clicked", lambda b: None)
        
        moveup = gtk.ToolButton(label="Move up")
        moveup.set_icon_name("gtk-go-up")
        moveup.connect("clicked", lambda b: None)
        
        movedown = gtk.ToolButton(label="Move down")
        movedown.set_icon_name("gtk-go-down")
        movedown.connect("clicked", lambda b: None)
        
        sep2 = gtk.SeparatorToolItem()
        
        delete = gtk.ToolButton(label="Delete")
        delete.set_icon_name("gtk-delete")
        delete.connect("clicked", lambda b: None)
        
        return (newhuman, newengine, duplicate, sep1,
                favorite, moveup, movedown, sep2,
                delete)
    
    def __newHumanClicked (self, button):
        pass
    
    def addHumanProfile (self, prototype):
        widgets = uistuff.GladeWidgets("humanProfile.glade")
        self.__addProfileHelper(widgets)
        widgets["nameEntry"].set_text(prototype.getName())
        self.__model.append([prototype.getName()])
        global imagebutton
        imagebutton = widgets["imageButton"]
        
        tree = widgets["accountsTreeview"]
        
        r = gtk.CellRendererPixbuf()
        col = gtk.TreeViewColumn()
        col.pack_start(r, expand=False)
        col.add_attribute(r, "pixbuf", 0)
        r = gtk.CellRendererText()
        r.connect_after("editing-started", self.__onNewProfile, tree)
        col.pack_start(r, expand=True)
        col.add_attribute(r, "markup", 1)
        col.add_attribute(r, "editable", 6)
        tree.append_column(col)
        col.set_expand(True)
        
        r = CellRendererButton()
        r.connect("clicked", self.__onEditClicked)
        col = gtk.TreeViewColumn()
        col.pack_start(r, expand=False)
        col.add_attribute(r, "stock-id", 2)
        col.add_attribute(r, "text", 3)
        tree.append_column(col)
        
        r = CellRendererButton()
        r.connect("clicked", self.__onDeleteClicked)
        col = gtk.TreeViewColumn()
        col.pack_start(r, expand=False)
        col.add_attribute(r, "stock-id", 4)
        col.add_attribute(r, "text", 5)
        tree.append_column(col)
        
        tree.set_model(gtk.ListStore(gtk.gdk.Pixbuf,str,str,str,str,str,bool))
        #tree.get_selection().set_mode(gtk.SELECTION_NONE)
        #tree.props.can_focus = False
        
        for identity in prototype.getOnlineIdentities():
            tree.get_model().append([gtk.gdk.pixbuf_new_from_file(prefix.addDataPrefix("glade/fics.png")),
                                     identity.getHandle()+"@"+identity.getServer(),
                                     "gtk-edit",
                                     "Edit",
                                     "gtk-delete",
                                     "Delete",
                                     False])
        
        tree.get_model().append([tree.render_icon("gtk-new", gtk.ICON_SIZE_BUTTON),
                                 "<u>Click to add new</u>",
                                 "", "",
                                 "", "",
                                 True])
    
    def addEngineProfile (self, prototype):
        widgets = uistuff.GladeWidgets("engineProfile.glade")
        self.__addProfileHelper(widgets)
    
    def __addProfileHelper (self, widgets):
        widget = widgets["main"]
        widget.unparent()
        self.__notebook.add(widget)
        self.__mainWidgets[widget] = widgets
    
    def __onNewProfile (self, celltext, editable, path, tree):
        iter = tree.get_model().get_iter(path)
        tree.get_model().remove(iter)
        tree.get_model().append([gtk.gdk.pixbuf_new_from_file(prefix.addDataPrefix("glade/fics.png")),
                                     "thomas"+"@"+"yahoo.com",
                                     "gtk-edit",
                                     "Edit",
                                     "gtk-delete",
                                     "Delete",
                                     False])
        tree.get_model().append([tree.render_icon("gtk-new", gtk.ICON_SIZE_BUTTON),
                                 "Click to add new",
                                 "", "",
                                 "", "",
                                 True])
        
        # A small hack to remove that editing box
        event = gtk.gdk.Event(gtk.gdk.BUTTON_PRESS)
        event.window = tree.window
        source = gobject.timeout_add(0, lambda: gtk.main_do_event(event) or gobject.source_remove(source))
    
    def __onEditClicked (self, cellbutton, path):
        print "edit", path
    
    def __onDeleteClicked (self, cellbutton, path):
        print "delete", path

import gobject
import pango
import random

class CellRendererButton(gtk.CellRenderer):
    
    __gsignals__ = {
        "clicked":  (gobject.SIGNAL_RUN_FIRST, None, (object,)),
    }
    
    __gproperties__ = {
        "text": (str, 'text', 'text displayed', '', gobject.PARAM_READWRITE),
        "stock-id": (str, 'text', 'text displayed', '', gobject.PARAM_READWRITE)
    }
    
    def __init__(self):
        gtk.CellRenderer.__init__(self)
        self.props.xalign = 0.5
        self.props.xpad = 6
        self.props.mode = gtk.CELL_RENDERER_MODE_ACTIVATABLE
        
        self._xpad = 6
        self._ypad = 4
        self._spacing = 2
        
        w = gtk.Window()
        b = gtk.Button()
        w.add(b)
        b.ensure_style()
        self.__buttonstyle = b.get_style()
        self.__child_displacement_y = b.style_get_property('child-displacement-y')
        
        self.__toggled = False
    
    def do_set_property(self, pspec, value):
        setattr(self, pspec.name.replace("-","_"), value)
     
    def do_get_property(self, pspec):
        return getattr(self, pspec.name.replace("-","_"))

    def do_get_size (self, widget, cell_area):
        if not self.text and not self.stock_id:
            return (0, 0, 0, 0)
        
        context = widget.get_pango_context()
        metrics = context.get_metrics(widget.style.font_desc,
                                      context.get_language())
        row_height = metrics.get_ascent() + metrics.get_descent()
        text_height = pango.PIXELS(row_height)
        
        pix = widget.render_icon(self.stock_id, gtk.ICON_SIZE_BUTTON)
        if pix:
            pix_height = pix.get_height()
            pix_width = pix.get_width()
        else:
            pix_height = 0
            pix_width = 0
        
        height = max(text_height, pix_height) + self._ypad * 2
        
        layout = widget.create_pango_layout(self.text)
        (row_width, layout_height) = layout.get_pixel_size()
        width = self._xpad + pix_width + self._spacing + row_width + self._xpad 
        
        return (0, 0, width, height)
    
    def do_render(self, window, widget, bg_area, cell_area, expose_area, flags):
        if not window or not self.text and not self.stock_id:
            return
        
        tog = self.__toggled and flags & gtk.CELL_RENDERER_FOCUSED
        
        if tog:
            state = gtk.STATE_ACTIVE
            shadow = gtk.SHADOW_IN
        elif flags & gtk.CELL_RENDERER_PRELIT:
            state = gtk.STATE_PRELIGHT
            shadow = gtk.SHADOW_OUT
        else:
            state = gtk.STATE_NORMAL
            shadow = gtk.SHADOW_OUT
        
        oldstyle = widget.get_style()
        widget.set_style(self.__buttonstyle)
        
        widget.style.paint_box(window, state, shadow, cell_area,
                               widget, "button",
                               cell_area.x, cell_area.y,
                               cell_area.width, cell_area.height)
        
        if tog:
            yextra = self.__child_displacement_y
        else: yextra = 0
        
        pix = widget.render_icon(self.stock_id, gtk.ICON_SIZE_BUTTON)
        if pix:
            pix_height = pix.get_height()
            pix_width = pix.get_width()
            pix_x = cell_area.x + self._xpad
            pix_y = (cell_area.height-pix_height)/2. + cell_area.y + yextra
            context = window.cairo_create()
            context.set_source_pixbuf(pix, pix_x, pix_y)
            context.paint()
        else:
            pix_height = 0
            pix_width = 0
        
        layout = widget.create_pango_layout(self.text)
        (text_width, text_height) = layout.get_pixel_size()
        text_x = (cell_area.width+pix_width+self._spacing-text_width)/2 + cell_area.x
        text_y = (cell_area.height-text_height)/2 + cell_area.y + yextra
        widget.style.paint_layout(window, widget.state, True, expose_area,
                                  widget, "button", text_x, text_y, layout)
    
    def do_activate(self, event, wid, path, bg_area, cell_area, flags):
        self.sig1 = wid.connect('button-release-event', self.on_deactivate, cell_area)
        self.sig2 = wid.connect('key-release-event', self.on_deactivate, cell_area)
        self.__toggled = True
        self.do_render(wid.get_bin_window(), wid, cell_area, cell_area, cell_area, gtk.CELL_RENDERER_FOCUSED)
        self.emit("clicked", path)
        return True
    
    def on_deactivate(self, w, e, cell_area):
        w.disconnect(self.sig1)
        w.disconnect(self.sig2)
        self.__toggled = False
        self.do_render(w.get_bin_window(), w, cell_area, cell_area, cell_area, gtk.CELL_RENDERER_PRELIT)

gobject.type_register(CellRendererButton)

