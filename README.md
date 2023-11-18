- Copy _Framework in local path:

```shell
# cp -R /Applications/Ableton\ Live\ 11.2\ Beta.app/Contents/App-Resources/MIDI\ Remote\ Scripts/_Framework .
cp -R /Applications/Ableton\ Live\ 11.2\ Beta.app/Contents/App-Resources/MIDI\ Remote\ Scripts/ableton .
```

- Uncompile files: `uncompyle6 -o . *.pyc`
- Watch the log `tail -f /Users/mgharbi/Library/Preferences/Ableton/Live\ 11.2b10/Log.txt`
