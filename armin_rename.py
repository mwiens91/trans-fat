"""Descriptive thing here

usb-fatmove - armin_rename
~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: year by my name, see AUTHORS for more details
:license: license_name, see LICENSE for more details
ocstring goes here
"""

import os
import sys


def arminRename(targetDirectory, quiet):
    """does things and stuff"""
    # Easiest if we move to targetDirectory, and move back later
    oldCwd = os.getcwd()
    os.chdir(targetDirectory)

    # Get a list of directories and files in the target directory
    items = os.listdir()

    # Filter out all non-Armin directories and files
    dirs = [i for i in items if os.path.isdir(i) and i.startswith('Armin')]

    # Rename episode directories to be only episode number
    for episode in dirs:
        epnum = episode[37:40]

        try:
            os.rename(episode, epnum)
        except OSError:
            if not quiet:
                print("ERROR: failed to rename" % episode, file=sys.stderr)

    # Clean up: move back to old cwd
    os.chdir(oldCwd)

    return


if __name__ == '__main__':
    # Self-test code
    arminRename('/home/matt/Downloads/sample_armin', False)
