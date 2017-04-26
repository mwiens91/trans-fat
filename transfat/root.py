"""Contains functions related to root access."""

import os
import subprocess
import sys
from . import talk
from .configconstants import NO, PROMPT


def requestRootAccess(configsettings, noninteractive=False, verbose=False):
    """Ensure script is running as root.

    Return true if we're running as root, or false if we can't get root;
    otherwise, obtain root credentials, terminate the program, and
    restart as root.

    Args:
        configsettings: A dictionary-like 'configparser.SectionProxy'
            object containing configuration settings from config.ini.
        noninteractive: An optional boolean toggling whether to ask for
            root if not already a root process.
        verbose: An optional boolean toggling whether to give extra
            output.

    Returns:
        A boolean signaling whether we are root. Another common exit
        from this function is through terminating the program and
        restarting as root.
    """
    # Check if we're already running as root
    euid = os.geteuid()

    if euid == 0:
        # Already running as root
        return True

    # Check if we have root passphrase cached already; exit code of the
    # Popen command will be non-zero if we don't have credentials, and
    # will be zero if we do
    rootCheck = subprocess.Popen(["sudo", "-n", "echo"],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
    exitCode = rootCheck.wait()

    # If we're running non-interactively and we don't have access to
    # root credentials, return false
    if noninteractive and exitCode:
        return False

    # Assume we cache credentials by default (i.e., we run 'sudo'
    # instead of 'sudo -k'); change this below if needed
    cacheOption = []

    # If we don't already have access to root credentials, determine
    # whether to cache root credentials when we ask for them
    if exitCode:
        # Get config settings for caching root credentials
        cache_ = configsettings.getint('UpdateUserCredentials')

        # Prompt whether to cache root credentials if necessary
        if cache_ == PROMPT:
            # Store the answer in cache_
            cache_ = talk.prompt("Remember root access passphrase?")

        # Run 'sudo -k' if we aren't caching credentials
        if cache_ == NO:
            cacheOption = ['-k']

    # Replace currently-running process with root-access process
    talk.status("Restarting as root", verbose)

    sudoCmd = (['sudo']
               + cacheOption
               + [sys.executable]
               + sys.argv
               + [os.environ])
    os.execlpe('sudo', *sudoCmd)
