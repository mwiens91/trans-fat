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
    restart script as root but don't update user credentials.
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
        return

def findDeviceLocation(destinationLoc, noninteractive, verbose, quiet):
    """
    Find device and mount location of destination drive given a string
    containing the destination location. Will prompt with list of possible
    devices if it cannot find device and mount location automatically (provided
    quiet option is not enabled).

    Inputs:
    destinationLoc: string containing path to destination file or directory.
    noninteractive: boolean toggling whether to omit interactive error resolution
    verbose: boolean toggling whether to give small amount of extra output
    quiet: boolean toggling whether to omit small amount of error output

    Returns a tuple containing device location and mount location as strings or
    a tuple of 2 empty strings if no device could be found.
    """
    # Make sure destinationLoc is absolute path
    destinationLoc = os.path.abspath(destinationLoc)


    # Get list of FAT devices

    bashListCmd = "mount -t vfat | cut -f 1,3 -d ' '"
    deviceListProcess = subprocess.Popen(["bash", "-c", bashListCmd],
                        stdout=subprocess.PIPE)

    # Get the raw byte string of the stdout from the above process and decode
    # it according to the ASCII character set
    deviceString = deviceListProcess.communicate()[0].decode('ascii')
    deviceString = deviceString.strip()

    # Check if any FAT devices were found
    if deviceString == '':
        # No FAT devices found, return empty string
        return ('','')

    # Split deviceString so we get a separate string for each device
    deviceList = deviceString.split('\n')

    # For each device, split into device location and mount location.
    # So in deviceListSep, deviceListSep[i][0] gives the device location of the
    # ith device and deviceListSep[i][1] gives the mount location of the ith
    # device
    deviceListSep = [deviceList[i].split() for i in range(len(deviceList))]


    # Test if destinationLoc matches any mount locations

    for i in range(len(deviceList)):
        # Find common path of destination location and mount location of the
        # ith device
        commonpath_ = os.path.commonpath([deviceListSep[i][1], destinationLoc])

        if commonpath_ == deviceListSep[i][1]:
            # Found a match! Return device and mount location
            return (deviceListSep[i][0], deviceListSep[i][1])
    else:
        if not noninteractive:
            # Something went wrong with the automation: if not set to
            # non-interactive mode, ask user if any of the FAT devices found
            # match the target

            # Enumerate each device
            deviceListEnum = ["[%d] %s" % (i, deviceList[i-1])
                                     for i in range(1,len(deviceList)+1)]
            # Add option to abort
            deviceListEnum.insert(0, "[0] abort!")

            # Prompt user for which device to use
            if verbose:
                print("Failed to find device automatically!", end='\n\n')
            print("Mounted FAT devices:", end='\n\n')
            print(*deviceListEnum, sep='\n', end='\n\n')

            ans = int(input("Drive to transfer to or abort [0-%d]: " %
                                                (len(deviceListEnum)-1)))
            print()


            # Return appropriate device and mount strings
            if ans == 0:
                # User selected abort, so return empty strings
                return ('','')
            elif ans > len(deviceListEnum)-1:
                if not quiet:
                    print("ERROR: invalid index", file=sys.stderr)
                return ('','')
            else:
                # Return requested device and mount location strings
                return (deviceListSep[ans - 1][0], deviceListSep[ans - 1][1])
        else:
            # Non-interactive mode is on, just return an empty string
            return ('','')


if __name__ == '__main__':

    # Parse input arguments
    parser = argparse.ArgumentParser(
            prog=NAME__,
            description="<program description goes here>")
    parser.add_argument("source",
            type=str,
            help="Relative path to source directory or file")
    parser.add_argument("destination",
            type=str,
            help="Relative path to destination directory or file")
    parser.add_argument("-f", "--no-fatsort",
            help="Do not unmount, fatsort, and remount",
            action="store_true")
    parser.add_argument("-n", "--non-interactive",
            help="Abort instead of interactively resolving errors",
            action="store_true")
    parser.add_argument("--version",
            action='version',
            version="%(prog)s 0.0.1")
    parser.add_argument("--config-file",
            help="Use specified config file",
            type=str,
            default="config.ini")
    parser.add_argument("--default",
            help="Use default settings from config file",
            action="store_true")
    parser.add_argument("--armin",
            help="Use 'ARMIN' settings from config file",
            action="store_true")
    parser.add_argument("--verbose",
            help="Give maximal output",
            action="store_true")
    parser.add_argument("--quiet", "--silent",
            help="Give minimal output",
            action="store_true")
    args = parser.parse_args()

    # Unpack some arguments
    noninteractive = args.non_interactive
    verbose = args.verbose
    quiet = args.quiet


    # Get root access if we don't have it already, but don't update user's
    # cached credentials
    if verbose:
        print("Checking root access . . .")

    requestRootAccess(verbose, quiet)

    if verbose:
        print("Running as root", end='\n\n')


    # Confirm that fatsort is installed
    if verbose:
        print("Checking if fatsort is available . . .")

    if fatsortAvailable(verbose, quiet):
        # fatsort available
        if verbose:
            print("fatsort is available", end='\n\n')
    else:
        # fatsort unavailable
        print("ERROR: fatsort not found!", file=sys.stderr)
        print("Aborting %s" % NAME__)
        sys.exit(1)


    # Find device and mount location corresponding to provided destination
    if verbose:
        print("Finding device and mount location containing %s . . ." %
                   args.destination, end='\n')

    deviceLoc, mountLoc = findDeviceLocation(args.destination,
                                    noninteractive, verbose, quiet)

    if deviceLoc == '':
        print("ERROR: no FAT device found!", file=sys.stderr)
        print("Aborting %s" % NAME__)
        sys.exit(1)
    else:
        if verbose:
            print("Found device and mount locations:\ndevice: %s\nmount: %s" %
                    (deviceLoc, mountLoc), end='\n\n')
