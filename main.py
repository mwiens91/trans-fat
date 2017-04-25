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

    if args.verbose:
        print("Reading config file '%s'. . ." % args.config_file)

    # Try reading config file specified, and exit if failure. If config
    # can't read successfully, it returns an empty list.
    if config.read(args.config_file) == []:
        if not args.quiet:
            print("ERROR: '"
                  + args.config_file
                  + "' is not a valid config file!",
                  file=sys.stderr)
        print("Aborting %s" % NAME__)
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

    if args.verbose:
        print("Success: '%s' read" % args.config_file)



    # Do a quick sanity check: if we have multiples sources, make sure
    # we're not being asked to move multiple files into anything that
    # isn't a directory
    if args.verbose:
        print("Making sure we aren't writing multiple files to a single "
              "file . . .")

    if os.path.isfile(args.destination) and len(args.sources) > 1:
        if not args.quiet:
            print("ERROR: cannot write multiple files to a single file!",
                  file=sys.stderr)

        print("Aborting %s" % NAME__)
        sys.exit(1)

    if args.verbose:
        print("Success: looks okay")



    # Get root access if we don't have it already, and update user's
    # cached credentials according to the config file. Skip this if
    # we're not fatsorting (since in this case we won't need root
    # access)
    if not args.no_fatsort:
        if args.verbose:
            print("Checking root access . . .")

        rootAccess = root.requestRootAccess(cfgSettings, args.non_interactive,
                                            args.verbose)

        if not rootAccess:
            # Failed to run as root
            if not args.quiet:
                print("ERROR: failed to run as root!", file=sys.stderr)

            print("Aborting %s" % NAME__)
            sys.exit(1)
        else:
            if args.verbose:
                print("Success: running as root")



    # Confirm that fatsort is installed
    if not args.no_fatsort:
        if args.verbose:
            print("Checking if fatsort is available . . .")

        if fatsort.fatsortAvailable():
            # fatsort available
            if args.verbose:
                print("Success: fatsort is available")
        else:
            # fatsort unavailable
            if not args.quiet:
                print("ERROR: fatsort not found!", file=sys.stderr)

            print("Aborting %s" % NAME__)
            sys.exit(1)



    # Find device and mount location corresponding to provided
    # destination
    if args.verbose:
        print("Finding device and mount location containing %s . . ."
              % args.destination)

    # This function returns empty strings if it failed
    devLoc, mntLoc = fatsort.findDeviceLocations(args.destination,
                                                 args.non_interactive,
                                                 args.verbose,
                                                 args.quiet)

    # Test for failure
    if devLoc == '':
        if not args.quiet:
            print("ERROR: no FAT device found!", file=sys.stderr)

        print("Aborting %s" % NAME__)
        sys.exit(1)
    else:
        if args.verbose:
            print("Success\n\nFound device and mount locations:"
                  "\ndevice: %s\nmount: %s" % (devLoc, mntLoc),
                  end='\n\n')



    # Get source and destination locations
    if args.verbose:
        print("Getting lists of source and destination locations . . .")

    fromDirs, fromFiles, toDirs, toFiles = (
        transfer.getCorrespondingPathsLists(args.sources, args.destination,
                                            args.verbose, args.quiet))

    if args.verbose:
        print("Success: source and destination locations found")



    # Filter out certain file types based on settings in config file
    if args.verbose:
        print("Filtering out unwanted file types . . .")

    transfer.filterOutExtensions(fromFiles, toFiles, cfgSettings,
                                 args.non_interactive)

    if args.verbose:
        print("Success: filtering complete")



    # Perform necessary audio file conversions as specified in config
    # file
    if args.verbose:
        print("Checking whether to convert any audio files . . .")

    # Returns a list of temporary source files to remove later
    tmpFiles = transfer.convertAudioFiles(fromFiles, toFiles, cfgSettings,
                                          args.non_interactive, args.verbose,
                                          args.quiet)

    if args.verbose:
        print("Success: conversions finished")



    # Create necessary directories to transfer to
    if args.verbose:
        print("Creating destination directories . . .")

    transfer.createDirectories(toDirs, args.non_interactive, args.verbose,
                               args.quiet)

    if args.verbose:
        print("Success: destination directories created")



    # Copy source files to destination
    if args.verbose:
        print("Copying files . . .")

    transfer.copyFiles(fromFiles, toFiles, cfgSettings, args.non_interactive,
                       args.verbose, args.quiet)

    if args.verbose:
        print("Success: files copied")



    # If in armin mode, rename destination directories
    if args.armin:

        if args.verbose:
            print("Renaming A State of Trance directories . . .")

        armin.rename(mntLoc, args.quiet)

        if args.verbose:
            print("Success: A State of Trance directories renamed")



    # Delete temporary files
    if args.verbose:
        print("Removing any temp files . . .")

    for tempFile in tmpFiles:
        try:
            os.remove(tempFile)
        except OSError:
            if not args.quiet:
                print("ERROR: failed to remove %s!" % tempFile,
                      file=sys.stderr)

    if args.verbose:
        print("Success: temp files removed")



    # Delete source directories if asked we're asked to. Note that
    # deleteSourceSetting - 1 is equivalent to a prompt flag, given the
    # config setting constant definitions at the top of the file.
    deleteSourceSetting = cfgSettings.getint("DeleteSources")
    promptFlag = deleteSourceSetting - 1

    if (deleteSourceSetting
       and not (args.non_interactive and promptFlag)):
        # Remove sources
        if args.verbose:
            print("Removing source files and directories . . .")

        transfer.deletePaths(args.sources, promptFlag, args.verbose,
                             args.quiet)

        if args.verbose:
            print("Success: source files and directories removed")



    # Unmount, fatsort, and remount if we're asked to
    if not args.no_fatsort:
        # Unmount
        if args.verbose:
            print("Unmounting %s . . ." % mntLoc)

        if not fatsort.unmount(devLoc, args.verbose):
            if not args.quiet:
                print("ERROR: failed to unmount %s!" % mntLoc, file=sys.stderr)

            print("Aborting %s" % NAME__)
            sys.exit(1)
        else:
            if args.verbose:
                print("Success: %s unmounted" % mntLoc)

        # Fatsort
        if args.verbose:
            print("fatsorting %s . . ." % mntLoc)

        if not fatsort.fatsort(devLoc, args.verbose):
            if not args.quiet:
                print("ERROR: failed to fatsort %s!" % mntLoc, file=sys.stderr)

            print("Aborting %s" % NAME__)
            sys.exit(1)
        else:
            if args.verbose:
                print("Success: %s fatsorted" % mntLoc)

        # Remount
        if args.verbose:
            print("Remounting %s . . ." % mntLoc)

        if not fatsort.mount(devLoc, args.verbose):
            if not args.quiet:
                print("ERROR: failed to remount %s!" % mntLoc, file=sys.stderr)

            print("Aborting %s" % NAME__)
            sys.exit(1)
        else:
            if args.verbose:
                print("Success: %s remounted" % mntLoc)

    # Successful run
    if args.verbose:
        print("All done")
