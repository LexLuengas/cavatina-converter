import os
from setuptools import setup, find_packages

import wx
if "cocoa" in wx.version():
  suffix="-Cocoa"
else:
  suffix="-Carbon"

versionpath = os.path.join(os.path.dirname(__file__), 'cavatina', '_version.py')
with open(versionpath, 'r') as f:
    lines = f.read()
    exec(lines)

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

APP = ['app.py'] #main file of your app
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'site_packages': True,
    # 'arch': 'i386',
	'semi_standalone': 'False',
	'includes': ['wx', 'music21'],
	'packages' : ['wx', 'music21'],
	"compressed" : True,
	"optimize": 2,
    #'iconfile': 'lan.icns', #if you want to add some ico
    'plist': {
        'CFBundleName': 'Cavatina',
        'CFBundleShortVersionString': __version__, # must be in X.X.X format
        'CFBundleVersion': __version__,
        'CFBundleIdentifier':'com.lextype.cavatina', #optional
    }
}

setup(
    app = APP,
    data_files = DATA_FILES,
    options = {'py2app': OPTIONS},
    setup_requires = ['py2app'],
    # name = "Cavatina",
    # version = __version__,
    # author = "Alexis Luengas Zimmer",
    # author_email = "alexis.luengas@gmail.com",
    # description = "Musical Notation Software",
    # license = "LGPL",
    # keywords = "music notation editor text converter musicxml midi",
    # packages = find_packages(exclude=['ez_setup']),
    # install_requires = ["music21", "pygame"],
    # classifiers = [
    #     "Development Status :: 3 - Alpha",
    #     "Intended Audience :: End Users/Desktop",
    #     "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
    #     "Operating System :: OS Independent",
    #     "Programming Language :: Python",
    #     "Programming Language :: Python :: 2",
    #     "Programming Language :: Python :: 2.6",
    #     "Programming Language :: Python :: 2.7",
    #     "Topic :: Multimedia :: Sound/Audio :: Conversion",
    #     "Topic :: Multimedia :: Sound/Audio :: MIDI",
    #     "Topic :: Text Processing",
    # ],
)
