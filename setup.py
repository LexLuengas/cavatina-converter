# !/usr/local/bin/python
import os
from setuptools import setup, find_packages

versionpath = os.path.join(os.path.dirname(__file__), 'cavatina', '_version.py')
with open(versionpath, 'r') as f:
    lines = f.read()
    exec(lines)

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "Cavatina",
    version = __version__, # pylint: disable=W0631
    author = "Alexis Luengas Zimmer",
    author_email = "lex@cavatinafont.com",
    description = "Musical Notation Parser for Cavatina Synthax.",
    long_description=read("README.md_"),
    long_description_content_type='text/markdown',
    license = "LGPL",
    url = "http://cavatinafont.com",
    keywords = "music notation parser converter musicxml midi",
    packages = ['cavatina'],
    install_requires = "music21",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Multimedia :: Sound/Audio :: Conversion",
        "Topic :: Multimedia :: Sound/Audio :: MIDI",
        "Topic :: Text Processing",
    ],
)
