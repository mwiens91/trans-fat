#!/usr/bin/env python3
# coding: utf-8
"""Copy files to a device and fatsort that device.

Run this on the command line like so:

    $ trans-fat source1 source2 pathOnDrive

or do

    $ trans-fat -h

to see how to be fancier. Or read the README.md. Anyway, 2 things not
explained in either the help or the readme are as follows:

1. Armin mode:
    Armin mode is used to transfer episodes of the radio show "A State
    of Trance". It differs from non-Armin mode in that it has its own
    settings group in the config.ini, and that it calls a function that
    renames certain directory names on the root of the destination
    device.
2. PROMPT vs --non-interactive:
    In the config.ini file there are options to prompt for various
    actions; however you can also run the program with a
    --non-interactive flag. The two are mutually exclusive, and in such
    cases where they fight, the non-interactive flag always wins.
"""

import argparse
import configparser
import os
import sys
from transfat import talk
from transfat import transfer
from transfat import fatsort
from transfat import root
from transfat import armin


# Name of the program
NAME__ = "trans-fat"


if __name__ == '__main__':
    # Parse input arguments
    parser = argparse.ArgumentParser(
            prog=NAME__,
            description="%(prog)s"
                        " - transfer audio files to a FAT device,"
                        " convert them to mp3 along the way,"
                        " leave behind unwanted files,"
                        " and sort everything into alphabetic order"
                        " - all in one command!")
    parser.add_argument(
            "sources",
            nargs='+',
            type=str,
            help="path to source directories or files")
    parser.add_argument(
            "destination",
            type=str,
            help="path to destination directory or file")
    parser.add_argument(
            "-f", "--no-fatsort",
            help="do not unmount, fatsort, and remount",
            action="store_true")
    parser.add_argument(
            "-n", "--non-interactive",
            help="never prompt user for input",
            action="store_true")
    parser.add_argument(
            "--version",
            action='version',
            version="%(prog)s 0.1.0")
    parser.add_argument(
            "--config-file",
            help="use specified config file",
            type=str,
            default="config.ini")
    parser.add_argument(
            "--default",
            help="use default settings from config file",
            action="store_true")
    parser.add_argument(
            "--armin",
            help="use Armin mode",
            action="store_true")
    parser.add_argument(
            "--verbose",
            help="give maximal output",
            action="store_true")
    parser.add_argument(
            "--quiet", "--silent",
            help="give minimal output",
            action="store_true")
    args = parser.parse_args()



    # Parse config file
    config = configparser.ConfigParser()

    talk.status("Reading config file '%s'" % args.config_file, args.verbose)

    # Try reading config file specified, and exit if failure. If config
    # can't read successfully, it returns an empty list.
    if config.read(args.config_file) == []:
        talk.error("'%s' is not a valid config file!" % args.config_file,
                   args.quiet)
        talk.aborting()
        sys.exit(1)

    # Select which section of settings to use. The resulting
    # 'configparser.SectionProxy' behaves quite similarly to a
    # dictionary. See the config .ini file specified by the runtime
    # argument --config-file to see config options available
    if args.default:
        # Use DEFAULT section of config file
        cfgSettings = config['DEFAULT']
    elif args.armin:
        # Use ARMIN section of config file
        cfgSettings = config['ARMIN']
    else:
        # Use user section of config file
        cfgSettings = config['user']

    talk.success("'%s' read" % args.config_file, args.verbose)



    # Do a quick sanity check: if we have multiples sources, make sure
    # we're not being asked to move multiple files into anything that
    # isn't a directory
    talk.status("Making sure we aren't writing multiple files to a single"
                " file", args.verbose)

    if os.path.isfile(args.destination) and len(args.sources) > 1:
        talk.error("cannot write multiple files to a single file!", args.quiet)
        talk.aborting()
        sys.exit(1)

    talk.success("looks okay", args.verbose)



    # Get root access if we don't have it already, and update user's
    # cached credentials according to the config file. Skip this if
    # we're not fatsorting (since in this case we won't need root
    # access)
    if not args.no_fatsort:
        talk.status("Checking root access", args.verbose)

        rootAccess = root.requestRootAccess(cfgSettings, args.non_interactive,
                                            args.verbose)

        if not rootAccess:
            # Failed to run as root
            talk.error("failed to run as root!", args.quiet)
            talk.aborting()
            sys.exit(1)
        else:
            talk.success("running as root", args.verbose)



    # Confirm that fatsort is installed
    if not args.no_fatsort:
        talk.status("Checking if fatsort is available", args.verbose)

        if fatsort.fatsortAvailable():
            # fatsort available
            talk.success("fatsort is available", args.verbose)
        else:
            # fatsort unavailable
            talk.error("fatsort not found!", args.quiet)
            talk.aborting()
            sys.exit(1)



    # Find device and mount location corresponding to provided
    # destination
    talk.status("Finding device and mount locations containing '%s'"
                % args.destination, args.verbose)

    # This function returns empty strings if it failed
    devLoc, mntLoc = fatsort.findDeviceLocations(args.destination,
                                                 args.non_interactive,
                                                 args.verbose,
                                                 args.quiet)

    # Test for failure
    if devLoc == '':
        talk.error("no FAT device found!", args.quiet)

        talk.aborting()
        sys.exit(1)
    else:
        if args.verbose:
            print("Success\n\nFound device and mount locations:"
                  "\ndevice: %s\nmount: %s" % (devLoc, mntLoc),
                  end='\n\n')



    # Get source and destination locations
    talk.status("Getting lists of source and destination locations",
                args.verbose)

    fromDirs, fromFiles, toDirs, toFiles = (
        transfer.getCorrespondingPathsLists(args.sources, args.destination,
                                            args.verbose, args.quiet))

    talk.success("source and destination locations found", args.verbose)



    # Filter out certain file types based on settings in config file
    talk.status("Filtering out unwanted file types", args.verbose)

    transfer.filterOutExtensions(fromFiles, toFiles, cfgSettings,
                                 args.non_interactive)

    talk.success("filtering complete", args.verbose)



    # Perform necessary audio file conversions as specified in config
    # file
    talk.status("Checking whether to convert any audio files", args.verbose)

    # Returns a list of temporary source files to remove later
    tmpFiles = transfer.convertAudioFiles(fromFiles, toFiles, cfgSettings,
                                          args.non_interactive, args.verbose,
                                          args.quiet)

    talk.success("conversions finished", args.verbose)



    # Create necessary directories to transfer to
    talk.status("Creating destination directories", args.verbose)

    transfer.createDirectories(toDirs, args.non_interactive, args.verbose,
                               args.quiet)

    talk.success("destination directories created", args.verbose)



    # Copy source files to destination
    talk.status("Copying files", args.verbose)

    transfer.copyFiles(fromFiles, toFiles, cfgSettings, args.non_interactive,
                       args.verbose, args.quiet)

    talk.success("files copied", args.verbose)



    # If in armin mode, rename destination directories
    if args.armin:

        talk.status("Renaming A State of Trance directories", args.verbose)

        armin.rename(mntLoc, args.quiet)

        talk.success("A State of Trance directories renamed", args.verbose)



    # Delete temporary files
    talk.status("Removing any temp files", args.verbose)

    for tempFile in tmpFiles:
        try:
            os.remove(tempFile)
        except OSError:
            talk.error("failed to remove %s!" % tempFile, args.quiet)

    talk.success("temp files removed", args.verbose)



    # Delete source directories if asked we're asked to. Note that
    # deleteSourceSetting - 1 is equivalent to a prompt flag, given the
    # config setting constant definitions at the top of the file.
    deleteSourceSetting = cfgSettings.getint("DeleteSources")
    promptFlag = deleteSourceSetting - 1

    if (deleteSourceSetting
       and not (args.non_interactive and promptFlag)):
        # Remove sources
        talk.status("Removing source files and directories", args.verbose)

        transfer.deletePaths(args.sources, promptFlag, args.verbose,
                             args.quiet)

        talk.success("source files and directories removed", args.verbose)



    # Unmount, fatsort, and remount if we're asked to
    if not args.no_fatsort:
        # Unmount
        talk.status("Unmounting %s" % mntLoc, args.verbose)

        if not fatsort.unmount(devLoc, args.verbose):
            talk.error("failed to unmount %s!" % mntLoc, args.quiet)

            talk.aborting()
            sys.exit(1)
        else:
            talk.success("%s unmounted" % mntLoc, args.verbose)

        # Fatsort
        talk.status("fatsorting %s" % mntLoc, args.verbose)

        if not fatsort.fatsort(devLoc, args.verbose):
            talk.error("failed to fatsort %s!" % mntLoc, args.quiet)

            talk.aborting()
            sys.exit(1)
        else:
            talk.success("%s fatsorted" % mntLoc, args.verbose)

        # Remount
        talk.status("Remounting %s" % mntLoc, args.verbose)

        if not fatsort.mount(devLoc, args.verbose):
            talk.error("failed to remount %s!" % mntLoc, args.quiet)

            talk.aborting()
            sys.exit(1)
        else:
            talk.success("%s remounted" % mntLoc, args.verbose)

    # Successful run
    talk.success("All done", args.verbose)
