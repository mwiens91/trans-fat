"""Contains functions for processing "A State of Trance" episodes."""

import os
from . import talk


def rename(targetDirectory, quiet=False):
    """Rename A State of Trance directories according to episode number.

    [*] The episode directory name structure expected follows the form
    of baby967's rips of Armin van Buuren's "A State Of Trance"
    radioshow (a webshow as of 2017), as they've been named from
    ~2014–2017, and likely the way they will continue to be named in the
    future.

    Args:
        targetDirectory: A string containing the path to the directory
            containing the directories to be renamed. See [*] above
        quiet: A boolean toggling whether to supress error output.
    """
    # It's easiest if we move to the target directory, and move back
    # later
    oldCwd = os.getcwd()
    os.chdir(targetDirectory)

    # Get a list of directories and files in the target directory
    items = os.listdir()

    # Filter out all non-Armin directories and files
    dirs = [i for i in items if os.path.isdir(i) and i.startswith('Armin')]

    # Rename episode directories to be only episode number
    for episode in dirs:
        # TODO(mwiens91): Use regexp to capture special episode of form
        # xxx.y; e.g., ASOT 800.1
        epnum = episode[37:40]

        try:
            os.rename(episode, epnum)
        except OSError:
            talk.error("Failed to rename" % episode, quiet)

    # Clean up: move back to old cwd
    os.chdir(oldCwd)

    return
