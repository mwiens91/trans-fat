# trans-fat

## Purpose
trans-fat's purpose is to make playing music files on your car stereo over USB not a total nightmare. Some car stereos play audio files from a (FAT-only) USB stick in the order that the files were transfered to the device—which is in general not alphanumeric order. This means that when you put on an album, it might start from track 6, then go to track 9 or something. To make things worse, many of these devices demand that your audio files be either MP3s or WMAs; so say good-bye to your FLACs and Oggs.

<strong>trans-fat</strong> transfers audio files to a FAT device and worries about these details so you don't have to.

## What does this do?

Say we run

```
$ trans-fat source drive/destination
```

then <strong>trans-fat</strong> does some/all of the following:

1. Filter out any unwanted .logs, .cues, etc. in source
2. Convert non-MP3s to temporary MP3s
3. Transfer files to the destination
4. Sort the drive into alphanumeric order
5. Unmount & clean-up

## Great, how do I install this?

First you need to get some dependencies. Assuming you're on Debian (or similar) run
```
sudo apt-get install fatsort ffmpeg
```
then to install trans-fat run
```
sudo pip3 install trans-fat
```
