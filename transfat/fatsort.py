"""Contains functions useful for fatsorting drives."""

import os
import subprocess
from . import talk


def findDeviceLocations(destinationPath, noninteractive=False, verbose=False,
                        quiet=False):
    """Return device and mount locations of a FAT drive.

    Find device and mount locations of the FAT device corresponding to
    the supplied destination path. If these locations can't be found
    automatically, find them interactively. If all of this fails, return
    a 2-tuple of empty strings.

    Args:
        destinationPath: A string containing a path somewhere on the
            mounted device.
        noninteractive: An optional boolean toggling whether to omit
            interactively finding device and mount locations if doing so
            automatically fails.
        verbose: An optional boolean toggling whether to give extra
            output.
        quiet: An optional boolean toggling whether to omit error
            output.

    Returns:
        A 2-tuple containing device location and mount location strings;
        or, if these locations can't be found, a 2-tuple of empty
        strings.
    """
    # Make sure destination is an absolute path
    destination = os.path.abspath(destinationPath)

    # Get list of FAT devices
    bashListCmd = "mount -t vfat | cut -f 1,3 -d ' '"
    deviceListProcess = subprocess.Popen(["bash", "-c", bashListCmd],
                                         stdout=subprocess.PIPE)

    # Read the devices list from Popen
    deviceString = deviceListProcess.communicate()[0].decode('ascii')
    deviceString = deviceString.rstrip()

    # Check if any FAT devices were found
    if deviceString == '':
        # No FAT devices found, return empty string
        return ('', '')

    # Split deviceString so we get a separate string for each device
    deviceList = deviceString.split('\n')

    # For each device, split into device location and mount location.
    # So in deviceListSep, deviceListSep[i][0] gives the device location
    # and deviceListSep[i][1] gives the mount location of the ith device
    deviceListSep = [deviceList[i].split() for i in range(len(deviceList))]

    # Test if destination path matches any mount locations
    for i in range(len(deviceList)):
        deviceLoc = deviceListSep[i][0]
        mountLoc = deviceListSep[i][1]

        if os.path.commonpath((destination, mountLoc)) == mountLoc:
            # Found a match! Return device and mount location
            return (deviceLoc, mountLoc)

    # Something went wrong with the automation: if not set to
    # non-interactive mode, ask user if any of the FAT devices found
    # earlier match the intended destination; otherwise, just return
    # empty strings
    if not noninteractive:
        # Enumerate each device
        deviceListEnum = ["[%d] %s" % (i, deviceList[i-1])
                          for i in range(1, len(deviceList)+1)]

        # Add option to abort
        deviceListEnum.insert(0, "[0] abort!")

        # Prompt user for which device to use
        talk.status("Failed to find device automatically!", verbose)
        print("Mounted FAT devices:", end='\n\n')
        print(*deviceListEnum, sep='\n', end='\n\n')

        ans = int(
                input("Drive to transfer to or abort [0-%d]: "
                      % (len(deviceListEnum)-1))
                 )

        # Return appropriate device and mount strings
        if ans == 0:
            # User selected abort, so return empty strings
            return ('', '')
        elif ans > len(deviceListEnum)-1:
            talk.error("Invalid index", quiet)
            return ('', '')

        # Return requested device and mount location strings
        return (deviceListSep[ans-1][0], deviceListSep[ans-1][1])

    # Non-interactive mode is on, just return empty strings
    return ('', '')


def unmount(deviceLocation, verbose=False):
    """Unmount a device and return whether it was successful."""
    noiseLevel = []
    if verbose:
        noiseLevel += ['-v']

    exitCode = subprocess.Popen(['sudo', 'umount', deviceLocation]
                                + noiseLevel).wait()
    return bool(not exitCode)


def fatsort(deviceLocation, quiet=False):
    """fatsort a device and return whether it was successful."""
    noiseLevel = []
    if quiet:
        noiseLevel += ['-q']

    exitCode = subprocess.Popen(['sudo', 'fatsort', deviceLocation]
                                + noiseLevel).wait()
    return bool(not exitCode)
