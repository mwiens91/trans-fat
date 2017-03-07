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
import subprocess
import distutils.util

# Name of the program
NAME__ = "usb-fatmove"

def prompt(query):
    """
    A simple function to ask yes/no questions to stdout
    on the command line. Credit goes to Matt Stevenson. See:
    http://mattoc.com/python-yes-no-prompt-cli.html
    """
    sys.stdout.write("%s [y/n]: " % query)
    val = input().lower()
    try:
        result = distutils.util.strtobool(val)
    except ValueError:
        # Result no good! Ask again.
        sys.stdout.write("Please answer with y/n\n")
        return prompt(query)
    return result

def fatsortAvailable(verbose, quiet):
    """
    Check to see if fatsort is available on the system.
    Returns true or false.
    """
    fatCheck = subprocess.Popen(["bash", "-c", "type fatsort"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
    exitCode = fatCheck.wait()

    if exitCode == 0:
        # fatsort successfully found
        return True
    else:
        # fatsort not found
        return False

def requestRootAccess(verbose, quiet):
    """
    Request root access if we don't already have it. If we obtain it,
    restart script as root but don't update user credentials
    """
    # Check if we're root
    euid = os.geteuid()

    if euid != 0:
        # We aren't root. Let's run as root
        args = ['sudo', '-k', sys.executable] + sys.argv + [os.environ]
        # Replace currently-running process with root-access process
        os.execlpe('sudo', *args)
    else:
        # We're already root
        return True



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

    # Unpack some arguments
    verbose = args.verbose
    quiet = args.quiet


    # Get root access if we don't have it already, but don't update user's
    # cached credentials
    if verbose:
        print("Checking root access . . .")

    requestRootAccess(verbose, quiet)

    if verbose:
        print("Running as root")


    # Confirm that fatsort is installed
    if verbose:
        print("Checking if fatsort is available . . .")

    if fatsortAvailable(verbose, quiet):
        # fatsort available
        if verbose:
            print("fatsort is available")
    else:
        # fatsort unavailable
        print("ERROR: fatsort not found!", file=sys.stderr)
        print("Aborting %s" % NAME__)
        sys.exit(1)


    # Find which drive we need to write to
    # lsblk -d -o NAME,MODEL,SIZE,HOTPLUG
    # info lsblk
