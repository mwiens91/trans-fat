"""Contains a function to rename directories according to instructions.
Current use of this function is for radio shows, but can be anything.
"""

import os
import re
from . import talk
from .config.rename_targets import name_patterns


def rename(targetDirectory, quiet=False):
    """Rename directories according to regex patterns.

    All regex patterns are given in list name_patterns, which lives in
    rename_targets.py. This list is a list of lists. Each list element
    contains (1) identifying regex to determine whether to rename a
    given directory according to the list's instructions; (2) regex to
    group items in the original directory name; (3) a string to insert
    the matched groups into.

    Args:
        targetDirectory: A string containing the path to the directory
            containing the directories to be renamed. See [*] above
        quiet: A boolean toggling whether to supress error output.
    """
    # It's easiest if we move to the target directory, and move back
    # later
    oldCwd = os.getcwd()
    os.chdir(targetDirectory)

    # Test each directory name for a pattern match
    for dir_name in os.listdir():
        for pattern in name_patterns:
            if re.search(pattern[0], dir_name):
                # Directory name matched pattern
                new_name = re.sub(pattern[1], pattern[2], dir_name)

                # Check if directory already exists. If it's empty, just
                # copy into it. If non-empty, skip renaming.
                if os.path.exists(new_name):
                    if not (os.path.isdir(new_name) and os.listdir(new_name) == []):
                        # Directory name already taken! Move onto next
                        # directory.
                        talk.error("Failed to rename %s; %s already exists!"
                                % (dir_name, targetDirectory + "/" + dir_name))
                        break

                try:
                    os.rename(dir_name, new_name)
                except OSError:
                    talk.error("Failed to rename %s" % dir_name, quiet)

                # Move onto next directory, success or not.
                break

    # Clean up: move back to old cwd
    os.chdir(oldCwd)

    return
