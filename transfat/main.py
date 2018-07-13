#!/usr/bin/env python3
# coding: utf-8
"""Copy files to a device and fatsort that device.

Run this on the command line like so:

    $ transfat source1 source2 pathOnDrive

or do

    $ transfat -h

to see how to be fancier. Or read the README.md.
"""

from transfat import fatsort
from transfat import rename
from transfat import system
from transfat import talk
from transfat import transfer


def main():
    """The main script of transfat."""
    # Get runtime arguments
    args = system.getRuntimeArguments()

    # Confirm that dependencies are installed
    talk.status("Checking if dependencies are installed", args.verbose)

    if system.dependenciesAvailable(args.no_sort, args.quiet, args.verbose):
        # Depencies available
        talk.success("Dependencies are installed", args.verbose)
    else:
        # Dependencies unavailable. dependenciesAvailable will spit out
        # any necessary error dialogue.
        system.abort(1)

    # Read the configuration file
    talk.status("Reading config file '%s'" % args.config_file, args.verbose)

    # This spits out an error message if there's a problem
    cfgSettings = system.getConfigurationSettings(args.config_file,
                                                  args.default,
                                                  args.quiet)
    if not cfgSettings:
        # Failure
        system.abort(1)
    else:
        # Success
        talk.success("'%s' read" % args.config_file, args.verbose)

    # Get root access if we don't have it already, and restart with it
    # if we don't. No need to do this if we're not fatsorting.
    if not args.no_sort:
        talk.status("Checking root access", args.verbose)

        rootAccess = system.requestRootAccess(cfgSettings,
                                              args.non_interactive,
                                              args.verbose)
        if not rootAccess:
            # Failed to run as root
            talk.error("Failed to run as root!", args.quiet)
            system.abort(1)
        else:
            # Success
            talk.success("Running as root", args.verbose)

    # Warn that this will take a bit of time if we're not fatsorting
    if not args.quiet:
        print("This may take a few minutes . . .")

    # Find device and mount location corresponding to provided
    # destination
    talk.status("Finding device and mount locations containing '%s'"
                % args.destination, args.verbose)

    # This function returns empty strings if it failed
    devLoc, mntLoc = fatsort.findDeviceLocations(args.destination,
                                                 args.non_interactive,
                                                 args.verbose,
                                                 args.quiet)
    if devLoc == '':
        # Failure
        talk.error("no FAT device found!", args.quiet)
        system.abort(1)
    else:
        # Success, print the devices
        if args.verbose:
            print("Success\n\nFound device and mount locations:"
                  "\ndevice: %s\nmount: %s" % (devLoc, mntLoc),
                  end='\n\n')

    # Transfer files
    if args.sources:
        # Get source and destination paths
        talk.status("Getting lists of source and destination paths",
                    args.verbose)

        _, fromFiles, toDirs, toFiles = (
            transfer.getCorrespondingPathsLists(args.sources, args.destination,
                                                args.verbose, args.quiet))

        talk.success("Source and destination locations found", args.verbose)

        # Filter out certain file types based on settings in config file
        talk.status("Filtering out unwanted file types", args.verbose)

        transfer.filterOutExtensions(fromFiles, toFiles, cfgSettings,
                                     args.non_interactive)

        talk.success("Filtering complete", args.verbose)

        # Perform necessary audio file conversions
        talk.status("Starting to convert any audio files that need it",
                    args.verbose)

        # Returns a list of temporary files to remove later
        tmpFiles = transfer.convertAudioFiles(fromFiles, toFiles, cfgSettings,
                                              args.non_interactive,
                                              args.verbose, args.quiet)

        talk.success("Conversions finished", args.verbose)

        # Create necessary directories to transfer to
        talk.status("Creating destination directories", args.verbose)

        transfer.createDirectories(toDirs, args.non_interactive, args.verbose,
                                   args.quiet)

        talk.success("Destination directories created", args.verbose)

        # Copy source files to destination
        talk.status("Copying files", args.verbose)

        transfer.copyFiles(fromFiles, toFiles, cfgSettings, args.non_interactive,
                           args.verbose, args.quiet)

        talk.success("Files copied", args.verbose)

        # Delete temporary files
        talk.status("Removing any temp files", args.verbose)

        transfer.deleteFiles(tmpFiles)

        talk.success("temp files removed", args.verbose)

        # Delete source directories if asked we're asked to. Note that
        # deleteSourceSetting - 1 is equivalent to a prompt flag, given
        # the config setting constant definitions.
        deleteSourceSetting = cfgSettings.getint("DeleteSources")
        promptFlag = deleteSourceSetting - 1

        if (deleteSourceSetting
           and not (args.non_interactive and promptFlag)):
            # Remove sources
            talk.status("Removing source files and directories", args.verbose)

            transfer.deletePaths(args.sources, promptFlag, args.verbose,
                                 args.quiet)

            talk.success("source files and directories removed", args.verbose)

    # If renaming directories, do so
    if args.rename or cfgSettings.getint('RenameByDefault'):
        talk.status("Renaming any matching directories", args.verbose)

        rename.rename(mntLoc, args.quiet)

        talk.success("Matching directories renamed", args.verbose)

    # Unmount and fatsort if we're asked to
    if not args.no_sort:
        # Unmount
        talk.status("Unmounting %s" % mntLoc, args.verbose)

        if not fatsort.unmount(devLoc, args.verbose):
            talk.error("Failed to unmount %s!" % mntLoc, args.quiet)
            system.abort(1)
        else:
            talk.success("%s unmounted" % mntLoc, args.verbose)

        # Fatsort
        talk.status("fatsorting %s" % mntLoc, args.quiet)

        if not fatsort.fatsort(devLoc, args.verbose):
            talk.error("Failed to fatsort %s!" % mntLoc, args.quiet)
            system.abort(1)
        else:
            talk.success("%s fatsorted" % mntLoc, args.verbose)

    # Successful run
    talk.success("All done", args.verbose)

    return
