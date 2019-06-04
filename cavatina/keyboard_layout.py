import os

keyLayouts = {
    "US"  : r"""`1234567890-=qwertyuiop[]\asdfghjkl;'zxcvbnm,./~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:"ZXCVBNM<>?""", # US (International)
    "DE"  : r"""^1234567890'#qwertzuiopöü*asdfghjkl;äyxcvbnm,.-°!"§$%&/()=?ßQWERTZUIOPÖÜ+ASDFGHJKL:ÄYXCVBNM<>_""", # DE
    "SPh" : r"""|1234567890'¿qwertyuiop{}*asdfghjkl;ñzxcvbnm,.-°!"#$%&/()=?¡QWERTYUIOP[]+ASDFGHJKL:ÑZXCVBNM<>_""", # SP (ISO)
    "FR"  : r"""!&é"'(-è_çà)=azertyuiopmù°qsdfghjkl;*wxcvbn,/.³§1234567890£$AZERTYUIOPM%+QSDFGHJKL:μWXCVBN?<>²""", # FR
    "IT"  : r"""\1234567890*+qwertyuiopùòlasdfghjk<;'zxcvbnm,.-|!"£$%&/()=èéQWERTYUIOP§çLASDFGHJK>:?ZXCVBNM°à_""", # IT
    "PTb" : r"""'1234567890-=qwertyuiop[]lasdfghjkÇ;´zxcvbnm,./"!@#$%¨&*()_+QWERTYUIOP{}LASDFGHJKç:`ZXCVBNM<>?""", # Brazil, Win.
    "PTp" : r"""\1234567890*+qwertyuiop«çlasdfghjk<;´zxcvbnm,.-|!"#$%&/()=?'QWERTYUIOP»ÇLASDFGHJK>:`ZXCVBNMºª_""", # Port, Win.
    "PTa" : r"""§1234567890*+qwertyuiop~çªasdfghjkl;´zxcvbnm,.-±!"#$%&/()=?'QWERTYUIOP^ÇºASDFGHJKL:`ZXCVBNM<>_""", # Apple
    "SPi" : r"""º1234567890'¡qwertyuiopñç*asdfghjkl;´zxcvbnm,.-ª!"·$%&/()=?¿QWERTYUIOPÑÇ+ASDFGHJKL:¨ZXCVBNM<>_""", # SP (Apple: SPI)
    "BRw" : r"""`1234567890~#qwertyuiop[]_asdfghjkl;'zxcvbnm,./¬!"£$%^&*()-=QWERTYUIOP{}+ASDFGHJKL:@ZXCVBNM<>?""", # Win.
    "BRa" : r"""§1234567890-=qwertyuiop[]\asdfghjkl;'zxcvbnm,./±!@£$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:"ZXCVBNM<>?""", # Apple
}

def inputTranslate(code, langFrom=None, langTo="US"):
    """
    code: unicode String
    """
    if not langFrom:
        langFrom = getLayout()
    if langFrom == langTo:
        return code
    out = ""
    for c in code:
        try:
            if c == " " or c == "\n":
                out += c
            else:   
                i = keyLayouts[langFrom].index(c)
                out += keyLayouts[langTo][i]
        except:
            raise KeyError("Wrong keyboard layout. Trying to decode character '%s' with the layout '%s'" % (c, langFrom))
    return out

def getLayout():
    import sys
    __location__ = os.path.dirname(os.path.realpath(sys.argv[0]))
    settingsFile = os.path.join(__location__, 'settings.ini')
    
    try:
        with open(settingsFile, 'r') as f:
            try:
                lang = f.readline().split("=")[1].strip()
            except IndexError:
                lang = ""
    except:
        # settings file not present
        lang = ""

    # Detect keyboard layout if not set
    if lang not in ["US", "DE", "IT", "PTa", "PTb", "PTp", "BRa", "BRw", "SPh", "SPi"]:
        try:
            lang = parse_locale(get_locale())
        except:
            lang = "US"
    return lang

def get_locale():
    if os.name == 'posix':
        from subprocess import check_output
        kl = check_output(["osascript", "-e", 'tell application "System Events" to tell process "SystemUIServer" to get the value of the first menu bar item of menu bar 1 whose description is "text input"'])
        return kl
        
    elif os.name == 'nt':
        import win32api, win32con, win32process
        from ctypes import windll
        user32 = windll.user32
        w = user32.GetForegroundWindow() 
        tid = user32.GetWindowThreadProcessId(w, 0)
        hkl = hex(user32.GetKeyboardLayout(tid))
        return hkl

def parse_locale(kl):
    if os.name == 'posix':
        unixLang = {
           "U.S.": "US",
           "German": "DE",
           "Italian": "IT",
           "Spanish": "SPh",
           "Spanish - ISO": "SPi",
           "British": "BRa",
           "Brazilian": "PTb",
           "Portuguese": "PTa",
        }
        kl = kl.strip("\n")
        return unixLang[kl]
        
    elif os.name == 'nt':
        winLang = {
           "-0xffefbf7": "US",
           "0x4090409": "US",
           "0x4070407": "DE",
           "0x4100410": "IT",
           "0x40a040a": "SPh",
           "0x40a0c0a": "SPh",
           "0x80a080a": "SPi",
           "0x8090809": "BRw",
           "0x8160816": "PTp",
           "0x4160416": "PTb",
        }
        return winLang[kl]
    else:
        raise OSError
