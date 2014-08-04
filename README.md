Cavatina
========

Cavatina is a parser and translator for the typeface of the same name. It parses rich text files (.rtf) and plain text files (.txt) and can translate to MusicXML and MIDI output per [music21](https://github.com/cuthbertLab/music21).

For more information about the Cavatina font visit <http://cavatinafont.com>. The [How-To](http://cavatinafont.com/howto#docs) section contains the syntax specification.

Currently supported keyboard layouts are: British, British (Apple), German, Italian, Portugese (Brazil), Portugese, Portugese (Apple), Spanish, Spanish (ISO) and US (International). When in doubt, check the [Keyboard Layouts](http://cavatinafont.com/keyboard) section of the homepage.

Common commands:

    $ python rtf2xml.py [path] [format]

    $ python translateToMusic21.py [string] [format]

### Installation <sub><sup>(desktop / cavatina)</sup><sub>

Double click on ``installer.command`` or do

    $ python setup.py install

You can also install the library with pip via the usual ``pip install cavatina``.

### Dependencies

*  music21

### Services

The *services* folder contains right-click menu shortcuts for the translator.

* To install the MacOS Services run ``./setup.sh`` on the same folder as the workflow folders.
* On Windows just double click on each registry file.

### License

This content is &copy; 2014 Alexis Luengas and released under the GNU LGPL license <https://www.gnu.org/licenses/lgpl.html>.
