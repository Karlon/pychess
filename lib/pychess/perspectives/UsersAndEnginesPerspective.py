import gtk

from Perspective import Perspective

class UsersAndEnginesPerspective (Perspective):
    
    def __init__(self):
        Perspective.__init__(self)
        self.setName(_("Users and Engines"))
        self.setDescription("...")
        self.setIconImage(gtk.image_new_from_pixbuf(
                          gtk.icon_theme_get_default().load_icon(
                          "stock_people", 32, gtk.ICON_LOOKUP_USE_BUILTIN)))
        
        self.getWindow().add(gtk.Label("test"))
    
    def show (self):
        pass
    
    def hide (self):
        pass
