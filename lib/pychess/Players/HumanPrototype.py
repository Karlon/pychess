class HumanPrototype:
    def __init__(self):
        self.__rating = {variant: {time:1600}}
        self.__name = "Thomas Dybdahl Ahle"
        self.__title = "GM"
        self.__icon = None
        
        onlineIdentities = []
        self.__alwaysUseProfileName = False
    
    def saveToXml(self):
        pass
    
    def loadFromXml(self):
        pass

class OnlineIdentity:
    def __init__(self):
        self.__protocol = FICS
        self.__handle = "lobais"
        self.__password = ""
        self.__logOnAsGuest = False
        self.__rating = {variant: {time:1600}}
        
        self.__friends = None

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