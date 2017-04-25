"""Contains a function to rename "A State of Trance" directories.

trans-fat - armin
~~~~~~~~~~~~~~~~~

The directory name structure is meant to specifically target standard
baby967 rips of Armin van Buuren's "A State Of Trance" radioshow (a
webshow as of 2017), as they've been named from ~2014–2017, and likely
the way they will continue to be named in the future.
"""

import os
import sys


def rename(targetDirectory, quiet=False):
    """Rename A State of Trance directories according to episode number.

    Args:
        targetDirectory: A string containing the path to the directory
            containing the directories to be renamed.
        quiet: A boolean toggling whether to supress error output.

    Returns:
        Nothing.
    """
    # It's easiest if we move to targetDirectory, and move back later
    oldCwd = os.getcwd()
    os.chdir(targetDirectory)

    # Get a list of directories and files in the target directory
    items = os.listdir()

    # Filter out all non-Armin directories and files
    dirs = [i for i in items if os.path.isdir(i) and i.startswith('Armin')]

    # Rename episode directories to be only episode number
    for episode in dirs:
        #TODO(mwiens91): Use regexp to capture special episode of form
        #                xxx.y; e.g., ASOT 800.1
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
