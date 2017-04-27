# trans-fat

## Purpose
trans-fat's purpose is to make playing music files on your car stereo over USB not a total nightmare. Some car stereos play audio files from a USB stick in the order that the files were transfered to the device—which is in general not alphanumeric order. This means that when you put on an album, it might start from track 6, then go to track 9 or something, and, man, is that ever annoying. To make things worse, many of these devices demand that your audio files be either mp3s or wmas; so say good-bye to your FLACs and oggs.

No! I will not say good-bye to sane file ordering and I will not say goodbye to my FLACs and oggs, thank you: I will use <strong>trans-fat</strong> to transfer files to my FAT device! (Oh, did I mention, those car stereos only accept FAT devices.)

## What does this do?

Say we run

```
$ trans-fat source drive/destination
```

then <strong>trans-fat</strong> does some/all of the following:

1. Filter out any unwanted .logs, .cues., etc. in source
2. Convert non-mp3s to temporary mp3
3. Transfer files to the destination
4. Sort the drive into alphanumeric order
5. Unmount & clean-up

## Great, how do I install this?
