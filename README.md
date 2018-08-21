[![PyPI](https://img.shields.io/pypi/v/transfat.svg)](https://pypi.org/project/transfat/)
![Python version](https://img.shields.io/badge/python-3-blue.svg)


# transfat

## Purpose
transfat's purpose is to make playing music files on your car stereo over USB not a total nightmare. Some car stereos play audio files from a (FAT-only) USB device in the order that the files were transfered to the device. In general, this is not an alphanumeric order. This means that when you put on an album, it might start from track 6, then go to track 9 or something. To make things worse, many of these stereos demand that your audio files be either MP3s or WMAs; so say good-bye to your FLACs and Oggs.

Ideally, car stereos should not depend on these small details, but unfortunately many do. That's where transfat comes in:

transfat transfers audio files to FAT devices and worries about the annoying details of your car stereo so that you don't have to.

## What exactly does this do?

Say we run

```
$ transfat source drive/destination
```

then transfat does some/all of the following:

1. Filters out any unwanted .logs, .cues, etc. in `source`
2. Converts non-MP3s from `source` to temporary MP3s
3. Transfers files to  `destination`
4. Unmounts `drive` and sorts into alphanumeric order
5. Cleans up intermediate files

## Great, how do I install this?

First you need to get some dependencies. Make sure you have `fatsort`
and `ffmpeg`. On Ubuntu you can get them with


```
sudo apt install fatsort ffmpeg
```

Once that's done, install transfat using

```
sudo pip3 install transfat
```

or just run the [`run_transfat.py`](run_transfat.py) script directly.
