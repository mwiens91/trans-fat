#!/usr/bin/python3

#state of trance sort
# -> take in arguments of folders
# -> find which drive to use both from /dev/.... and /media/
# -> check if drive mounted, mount if not
# -> rename folder to ASOT number if supplied
# -> remove cover
# 0 > move stuff
# -> fatsort drive
# mount drive back

import argparse
import os
import sys

if __name__ == '__main__':

    # Parse input arguments
    parser = argparse.ArgumentParser(
            description="alkjsdf")
    parser.add_argument("dirs",
            metavar="musicdir",
            nargs='+',
            type=str,
            help="Relative path to music-containing directory (no depth" +
                    " restriction)")
    parser.add_argument("--armin",
            help="Use settings specialized to transfering baby967 rips of" +
                    " Armin Van Buuren's A State Of Trance show",
            action="store_true")
    parser.add_argument("--verbose",
            help="Give maximal output",
            action="store_true")
    parser.add_argument("--quiet",
            help="Give minimal output",
            action="store_true")
    args = parser.parse_args()

    # Get root access if we don't have it already, but don't update user's
    # cached credentials
    euid = os.geteuid()
    if euid != 0:
        args = ['sudo', '-k', sys.executable] + sys.argv + [os.environ]
        # Replace currently-running process with root-access process
        os.execlpe('sudo', *args)

    # Find which drive we need to write to
    # lsblk -d -o NAME,MODEL,SIZE,HOTPLUG
    # info lsblk
