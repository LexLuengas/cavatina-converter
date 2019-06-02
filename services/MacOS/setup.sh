#! /bin/bash
PYDIR=$(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")
PYCMD=$(which python)
BASEDIR=`pwd`
DIR1="$BASEDIR/Convert to MusicXML.workflow"
DIR2="$BASEDIR/Convert to MIDI.workflow"

cd "$DIR1/Contents"
sed -i.bak -e "s+_PYCMD_+$PYCMD+g" -e "s+_PYPATH_+$PYDIR+g" document.wflow
rm document.wflow.bak
cd "$DIR2/Contents"
sed -i.bak -e "s+_PYCMD_+$PYCMD+g" -e "s+_PYPATH_+$PYDIR+g" document.wflow
rm document.wflow.bak

if [[ ! -d "$HOME/Library/Services/Convert to MusicXML.workflow" ]] ; then sudo mv "$DIR1" "$HOME/Library/Services" ; fi
if [[ ! -d "$HOME/Library/Services/Convert to MIDI.workflow" ]] ; then sudo mv "$DIR2" "$HOME/Library/Services" ; fi
