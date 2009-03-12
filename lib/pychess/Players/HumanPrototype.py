class HumanPrototype:
    def __init__(self):
        #self.__rating = {variant: [(time,1600)]}
        self.__name = "Thomas Dybdahl Ahle"
        self.__title = "GM"
        self.__icon = None
        
        self.__onlineIdentities = [OnlineIdentity()]
        self.__alwaysUseProfileName = False
    
    def getName (self):
        return self.__name
    
    def getOnlineIdentities (self):
        return iter(self.__onlineIdentities)
    
    def saveToXml(self):
        pass
    
    def loadFromXml(self):
        pass

class OnlineIdentity:
    def __init__(self):
        #self.__protocol = FICS
        self.__server = "freechess.org"
        self.__ports = (5000,)
        self.__handle = "Lobais"
        self.__password = ""
        self.__logOnAsGuest = False
        #self.__rating = {variant: [(time,1600)]}
        
        self.__friends = None
    
    def getHandle (self):
        return self.__handle
    
    def getServer (self):
        return self.__server
    

class OnlineSlavePrototype:
    def __init__(self):
        self.__name = ""
        self.__rating = 1600
        self.__fingernotes = None

class CECPPrototype:
    def __init__(self):
        self.__name = ""
        self.__callname = ""
        self.__vanillaPrototype = someprototype

class UCIVanillaPrototype:
    def __init__(self):
        self.__ucitags = {}
        self.__binary = ""

class UCIPrototype:
    def __init__(self):
        self.__ucitags = {}
        self.__runFromDirectory = ""
        self.__command = ""
        self.__callname = ""
        self.__vanillaPrototype = someprototype