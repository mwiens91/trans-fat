# transfat

## Purpose
transfat's purpose is to make playing music files on your car stereo over USB not a total nightmare. Some car stereos play audio files from a (FAT-only) USB device in the order that the files were transfered to the device—which is in general not alphanumeric order. This means that when you put on an album, it might start from track 6, then go to track 9 or something. To make things worse, many of these stereos demand that your audio files be either MP3s or WMAs; so say good-bye to your FLACs and Oggs.

Ideally, car stereos should not depend on these small details, but unfortunately, many do. That's where **transfat** comes in:

**transfat** transfers audio files to FAT devices and worries about the annoying details of your car stereo so that you don't have to.

## What exactly does this do?

Say we run

```
$ transfat source drive/destination
```

then **transfat** does some/all of the following:

1. Filters out any unwanted .logs, .cues, etc. in `source`
2. Converts non-MP3s from `source` to temporary MP3s
3. Transfers files to  `destination`
4. Unmounts `drive` and sorts into alphanumeric order
5. Cleans up intermediate files

## Great, how do I install this?

First you need to get some dependencies. Assuming you're on Ubuntu (or similar) run
```
sudo apt-get install fatsort ffmpeg
```
then to install transfat run
```
sudo pip3 install transfat
```
Giving root privileges to the last command isn't strictly necessary, but if you provide them, you'll get a useful `man` page for the program.
