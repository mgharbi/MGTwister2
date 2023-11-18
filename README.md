# MGTwister2

An Ableton Remote Script for the [Midi Fighter Twister](https://store.djtechtools.com/products/midi-fighter-twister).

## Installation

Copy the folder containing `MGTwister2.py` to your Ableton Remote Scripts folder.

## Development

1. Copy and uncompile Ableton's Remote Script framework files in the local path:

```shell
# cp -R /Applications/Ableton\ Live\ 11.2\ Beta.app/Contents/App-Resources/MIDI\ Remote\ Scripts/_Framework .
cp -R /Applications/Ableton\ Live\ 11.2\ Beta.app/Contents/App-Resources/MIDI\ Remote\ Scripts/ableton .
pip install decompyle3
# uncompyle6 -o . *.pyc
decompyle3 -o . -r .   
```

2. As you make adjustments, check the Live logs for prints and errors:

```shell
tail -f /Users/mgharbi/Library/Preferences/Ableton/Live\ 11.2b10/Log.txt`
```
