"""Contains functions related to interfacing with the parent shell.

Most of these functions are specific to transfat, but a few aren't. The
ones that are specific will be marked so.
"""

import argparse
import configparser
import os
import subprocess
import sys
import transfat.config.constants
from . import talk
from .version import NAME, VERSION


def getRuntimeArguments():
    """Return command line arguments as attributes of an object.

    Specific to running transfat.

    Returns:
        An object of type 'argparse.Namespace' containing the runtime
        arguments as attributes. See argparse documentation for more
        details.
    """
    CONFIGPATH = getConfigurationFilePath()

    parser = argparse.ArgumentParser(
            prog=NAME,
            description="%(prog)s"
                        " - transfer audio files to a FAT device"
                        " and sort into natural order")
    parser.add_argument(
            "sources",
            nargs='*',
            type=str,
            help="path to source directories or files")
    parser.add_argument(
            "destination",
            type=str,
            help="path to destination directory or file")
    parser.add_argument(
            "--config-file",
            help="use specified config file",
            type=str,
            default=CONFIGPATH)
    parser.add_argument(
            "--default",
            help="use default settings from config file",
            action="store_true")
    parser.add_argument(
            "--no-sort",
            help="do not unmount and fatsort",
            action="store_true")
    parser.add_argument(
            "--print-config",
            nargs=0,
            help='print example transfatrc and exit',
            action=ConfigPrintAction)
    parser.add_argument(
            "--rename",
            help="rename name-pattern matched directories",
            action="store_true")
    parser.add_argument(
            "--version",
            action='version',
            version="%(prog)s " + VERSION)
    noiseoptions = parser.add_mutually_exclusive_group()
    noiseoptions.add_argument(
            "--verbose",
            help="give maximal output",
            action="store_true")
    noiseoptions.add_argument(
            "--quiet", "--silent",
            help="give minimal output",
            action="store_true")
    parser.add_argument(
            "-n", "--non-interactive",
            help="never prompt user for input",
            action="store_true")

    arguments = parser.parse_args()

    return arguments


def getConfigurationFilePath():
    """Return a string containing the path of the configuration file.

    Looks in ~/ and the config directory from the XDG spec (defaults to ~/.config)
    first for a .transfatrc configuration file. If it can't find that,
    then this returns the default config file.

    Credit goes to Scott Stevenson (srstevenson on Github) for the XDG logic.
    """
    configdir = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    homedir = os.path.expanduser("~")

    configdirRC = configdir + "/transfat.conf"
    homedirRC = homedir + "/.transfatrc"

    if os.path.isfile(configdirRC):
        return configdirRC
    elif os.path.isfile(homedirRC):
        return homedirRC

    return os.path.dirname(transfat.config.constants.__file__) + "/config.ini"


def getExampleRCPath():
    """Return a string with the path of an example transfatrc file."""
    return os.path.dirname(transfat.config.constants.__file__) + '/transfatrc'


class ConfigPrintAction(argparse.Action):
    """Custom argparse action to print example transfatrc file."""
    def __call__(self, parser, namespace, values, option_string=None):
        with open(getExampleRCPath(), 'r') as transfatrc:
            print(transfatrc.read())
        sys.exit(0)


def dependenciesAvailable(no_fatsort=False, quiet=False, verbose=False):
    """Return true if dependencies are installed and false otherwise.

    Checks if fatsort and ffmpeg are installed.

    Args:
        no_fatsort: An optional boolean toggling whether to check if
            fatsort is installed. fatsort isn't necessary for the
            program if you aren't sorting.
        quiet: An optional boolean toggling whether to omit error
            output.
        verbose: An optional boolean toggling whether to give extra
            output.
    Returns:
        A boolean signaling whether dependicies are installed.
    """
    # Check if ffmpeg is installed
    ffmpegCheck = subprocess.Popen(["bash", "-c", "type ffmpeg"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    ffmpegAvailable = not ffmpegCheck.wait()

    if ffmpegAvailable:
        talk.status("ffmpeg available", verbose)
    else:
        # ffmpeg not available!
        talk.error("ffmpeg not installed!", quiet)

    # Check if fatsort is installed, if necessary
    if not no_fatsort:
        fatCheck = subprocess.Popen(["bash", "-c", "type fatsort"],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        fatsortAvailable = not fatCheck.wait()

        if fatsortAvailable:
            talk.status("fatsort available", verbose)
        else:
            # fatsort not available!
            talk.error("fatsort not installed!", quiet)

        return ffmpegAvailable and fatsortAvailable
    else:
        return ffmpegAvailable


def getConfigurationSettings(configPath, default=False, quiet=False):
    """Read settings from a config file and return settings.

    Reads configuration settings from a file with the configparser
    module, choosing between three sections of settings depending on the
    flags given when calling this function. Specific to transfat.

    Args:
        configPath: A string containing the path to the configuration
            file.
        default: An optional boolean toggling whether to read the
            'default' section of the config file.
        quiet: An optional boolean toggling whether to omit error
            output.

    Returns:
        A dictionary-like 'configparser.sectionproxy' object containing
        the settings loaded from the configuration file in the case of
        sucess; otherwise returns None.
    """
    # Instantiate the parser
    config = configparser.ConfigParser()

    # If the method read is unsuccessful it returns an empty list.
    if config.read(configPath) == []:
        # No good!
        talk.error("'%s' is not a valid configuration file!" % configPath,
                   quiet)
        return None
    else:
        # Read successful. Select which section of config file to use
        if default:
            # Use default section of config file
            configDict = config['DEFAULT']
        else:
            # Use user section of config file
            configDict = config['user']

        return configDict


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
        cache = configsettings.getint('UpdateUserCredentials')

        # Prompt whether to cache root credentials if necessary
        if cache == transfat.config.constants.PROMPT:
            # and store the answer in cache
            cache = talk.prompt("Remember root access passphrase?")

        # Run 'sudo -k' if we aren't caching credentials
        if cache == transfat.config.constants.NO:
            cacheOption = ['-k']

    # Replace currently-running process with root-access process
    talk.status("Prompting for passphrase to restart as root", verbose)

    sudoCmd = (['sudo']
               + cacheOption
               + [sys.executable]
               + sys.argv
               + [os.environ])
    os.execlpe('sudo', *sudoCmd)


def abort(code):
    """Exit program with an exit code."""
    talk.aborting()
    sys.exit(code)
