#!/usr/bin/env python3
# coding: utf-8
"""Move files to a device and fatsort that device.

usb-fatmove
~~~~~~~~~~~~~

description here

:copyright: year by my name, see AUTHORS for more details
:license: license_name, see LICENSE for more details
"""

import argparse
import configparser
import os
import sys
import subprocess
import distutils.util

# Name of the program
NAME__ = "usb-fatmove"

# Constants mirrored in the config file
NO = 0
YES = 1
PROMPT = 2


def prompt(query):
    """Prompt yes/no and return a boolean answer.

    A simple function to ask yes/no questions on the command line.
    Credit goes to Matt Stevenson. See:
    http://mattoc.com/python-yes-no-prompt-cli.html
    """
    sys.stdout.write("%s [y/n]: " % query)
    val = input().lower()
    try:
        result = distutils.util.strtobool(val)
    except ValueError:
        # Result no good! Ask again.
        sys.stdout.write("Please answer with y/n\n")
        return prompt(query)
    return result


def fatsortAvailable():
    """Return true if fatsort is available and false otherwise."""
    fatCheck = subprocess.Popen(["bash", "-c", "type fatsort"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    exitCode = fatCheck.wait()
    return bool(exitCode)


def requestRootAccess(configsettings, noninteractive, verbose):
    """If not already root, get root access and restart script.

    Request root access if we don't already have it. If we obtain it,
    restart script as root and update user credentials according to
    config settings.

    Inputs:
    configsettings: dictionary-like type 'configparser.SectionProxy'
        containing settings loaded from config file
    noninteractive: boolean toggling whether to exit script if root
        credentials not already cached
    verbose: boolean toggling whether to give extra output

    Returns true if everything went okay, and false otherwise.
    """
    # Check if we're already running as root; return if so
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
    # root credentials, exit program
    if noninteractive and exitCode:
        return False

    # Assume we cache credentials by default (i.e., we run 'sudo'
    # instead of 'sudo -k'); change this below if needed
    cacheOption = []

    # Determine whether to cache credentials in proceeding block if we
    # don't already have access to root credentials. exitCode will
    # contain something non-zero if we don't already have root access.
    if exitCode:
        # Get config settings for caching root credentials
        cache_ = configsettings.getint('UpdateUserCredentials')

        # Prompt whether to cache root credentials in accordance with
        # config file
        if cache_ == PROMPT:
            # Prompt and store the boolean result in cache_, overwriting
            # the the PROMPT value with YES or NO
            cache_ = prompt("Remember root access passphrase?")

        if cache_ == NO:
            # Run below command with 'sudo -k' vs 'sudo'
            cacheOption = ['-k']

    # Let's run as root
    if verbose:
        print("Restarting as root . . .")

    # Replace currently-running process with root-access process
    sudoCmd = (['sudo']
               + cacheOption
               + [sys.executable]
               + sys.argv
               + [os.environ])
    os.execlpe('sudo', *sudoCmd)


def findDeviceLocation(destination, noninteractive, verbose, quiet):
    """Return device and mount locations of destination device.

    Find device and mount location of destination drive given a string
    containing the destination location. Will prompt with list of
    possible devices if it cannot find device and mount location
    automatically (provided quiet option is not enabled).

    Inputs:
    destination: string containing path to destination file or
        directory.
    noninteractive: boolean toggling whether to omit interactive error
        resolution
    verbose: boolean toggling whether to give extra output
    quiet: boolean toggling whether to omit error output

    Returns a tuple containing device location and mount location as
    strings or a tuple of 2 empty strings if no device could be found.
    """
    # Make sure destination is absolute path
    destination = os.path.abspath(destination)

    # Get list of FAT devices
    bashListCmd = "mount -t vfat | cut -f 1,3 -d ' '"
    deviceListProcess = subprocess.Popen(["bash", "-c", bashListCmd],
                                         stdout=subprocess.PIPE)

    # Get the raw byte string of the stdout from the above process and
    # decode it according to the ASCII character set
    deviceString = deviceListProcess.communicate()[0].decode('ascii')
    deviceString = deviceString.strip()

    # Check if any FAT devices were found
    if deviceString == '':
        # No FAT devices found, return empty string
        return ('', '')

    # Split deviceString so we get a separate string for each device
    deviceList = deviceString.split('\n')

    # For each device, split into device location and mount location.
    # So in deviceListSep, deviceListSep[i][0] gives the device location
    # of the ith device and deviceListSep[i][1] gives the mount location
    # of the ith device
    deviceListSep = [deviceList[i].split() for i in range(len(deviceList))]

    # Test if destination matches any mount locations
    for i in range(len(deviceList)):
        deviceLoc = deviceListSep[i][0]
        mountLoc = deviceListSep[i][1]

        if destination.startswith(mountLoc):
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
        if verbose:
            print("Failed to find device automatically!")
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
            if not quiet:
                print("ERROR: invalid index", file=sys.stderr)
            return ('', '')
        else:
            # Return requested device and mount location strings
            return (deviceListSep[ans-1][0], deviceListSep[ans-1][1])
    else:
        # Non-interactive mode is on, just return an empty string
        return ('', '')


def getSourceAndDestinationLists(sourceLocs, destinationLoc, verbose, quiet):
    """Return source and destination locations for files and dirs.

    Return four lists corresponding to where our source and destination
    files and directories are.

    Inputs:
    sourceLocs: a list of source location strings, either corresponding
        to files or directories
    destinationLoc: a string containing the destination file to write to
        or a destination directory to transfer to
    verbose: boolean toggling whether to give extra output
    quiet: boolean toggling whether to omit error output

    Outputs:
    a tuple containing (sourceDirs, sourceFiles, destinationDirs,
        destinationFiles) where ...

    sourceDirs: a list of strings of absolute paths to source
        directories
    sourceFiles: a list of strings of absolute paths to source files
    destinationDirs: a list of strings of absolute paths to destination
        directories
    destinationFiles: a list of strings of absolute paths to destination
        files
    """
    # Get absolute paths of sources and destination
    sourcePaths = [os.path.abspath(source) for source in sourceLocs]
    destinationPath = os.path.abspath(destinationLoc)

    # Initialize list of files and directories to move. The indices of
    # corresponding source and destination lists will always be
    # consistent
    sourceDirs = []
    sourceFiles = []
    destinationDirs = []
    destinationFiles = []

    # Get list of files and directories to move
    for source in sourcePaths:
        # Get the parent directory of this source
        parent = os.path.dirname(source)
        parentlen = len(parent)

        if os.path.isfile(source):
            # Just a file, so add to the file list
            sourceFiles += [source]
            destinationFiles += [destinationPath + source[parentlen:]]
        elif os.path.isdir(source):
            # This is a directory, so let's go on an os.walk
            for root, _, files in os.walk(source):
                # Add root to dir list and files in root to file list
                sourceDirs += [root]
                sourceFiles += [root + '/' + file for file in files]
                destinationDirs += [destinationPath + root[parentlen:]]
                destinationFiles += [destinationPath
                                     + root[parentlen:]
                                     + '/'
                                     + file
                                     for file in files]
        else:
            # Neither a file nor directory. Give a warning, but
            # otherwise let the script proceed
            if not quiet:
                print("ERROR: '%s' does not exist!" % source,
                      file=sys.stderr)
            if verbose:
                print("Proceeding anyway. . .")

    return (sourceDirs, sourceFiles, destinationDirs, destinationFiles)


def filterOutExtensions(sourceFileList, destinationFileList, configsettings,
                        noninteractive):
    """Remove unwanted files from file lists in place.

    Remove specific files from the list of files to move as determined
    by the instructions in the config file 'configsettings'.

    This function returns nothing, but does its work by modifying the
    lists 'sourceFileList' and 'destinationFileList' in place.
    """
    # Load settings from config file
    imageOption = configsettings.getint('RemoveCue')
    logOption = configsettings.getint('RemoveLog')
    cueOption = configsettings.getint('RemoveCue')
    m3uOption = configsettings.getint('RemoveM3U')
    otherOption = configsettings.getint('RemoveOtherFiletypes')

    # What image file extensions we should detect (used in case
    # insensitive comparisons)
    audioExt = ('.flac', '.alac', '.aac', '.m4a', '.mp4', '.ogg', '.mp3')
    imageExt = ('.jpg', '.jpeg', '.bmp', '.png', '.gif')
    logExt = ('.log',)
    cueExt = ('.cue',)
    m3uExt = ('.m3u',)

    # Pair the file extensions with their corresponding config settings
    extensionList = [[imageExt, imageOption],
                     [logExt, logOption],
                     [cueExt, cueOption],
                     [m3uExt, m3uOption]]

    # Make a list of all non-audio extensions
    nonAudioExt = ()
    for ext in extensionList:
        nonAudioExt += ext[0]

    # Initialize a list of indices corresponding to files to remove
    indexList = []

    # Find which files have extensions that we don't want and mark their
    # indices
    for file in sourceFileList:
        if file.lower().endswith(audioExt):
            # This is an audio file; keep this file for sure
            continue
        elif file.lower().endswith(nonAudioExt):
            # This matches one of the non-audio extensions. Find which
            # extension it is and remove the file from the file list as
            # instructed to by the config settings.
            for ext, removeOption in extensionList:
                if file.lower().endswith(ext):
                    # Extension matched! Do what config file says,
                    # prompting if necessary.

                    if ((removeOption == PROMPT
                         and (noninteractive or prompt("Move '%s'?" % file)))
                            or removeOption == NO):
                        # Keep the file in the file list
                        break
                    else:
                        # Add index to list of indices to remove
                        indexList += [sourceFileList.index(file)]
        else:
            # This is some other kind of file. Do what config file says,
            # prompting if necessary.

            if ((otherOption == PROMPT
                 and (noninteractive or prompt("Move '%s'?" % file)))
                    or otherOption == NO):
                # Keep the file in the file list
                continue
            else:
                # Add index to list of indices to remove
                indexList += [sourceFileList.index(file)]

    # Remove files we don't want from the file lists, going through the
    # indices in reverse order
    for index in indexList[::-1]:
        sourceFileList.pop(index)
        destinationFileList.pop(index)

    return


def createDirsAndParents(destinationDirsList, configsettings, noninteractive,
                         verbose, quiet):
    """Create necessary directories in destination device.

    Note that if a directory fails to be created, none of its children
    directories or files will be explicitely removed the directory and
    file lists. Instead, cp will attempt to make them and most likely
    fail.
    """
    # Determine whether to overwrite files with directories or to prompt
    overwrite = configsettings.getint('OverwriteDestinationFiles')

    # But don't prompt if we're in non-interactive mode
    if noninteractive and overwrite == PROMPT:
        overwrite = NO

    # Create each directory in the natural order of os.walk - this is
    # essential to maximize error catching
    for targetDir in destinationDirsList:
        try:

            if verbose:
                print("Checking %s . . ." % targetDir)

            # Check if the directory already exists; move on to the next
            # directory if so
            if os.path.isdir(targetDir):
                # Already a directory
                if verbose:
                    print("%s already exists" % targetDir)

                continue

            # Check if we're attempting to overwrite a file
            if os.path.isfile(targetDir):
                # Determine whether to overwrite or abort
                if (overwrite == YES
                    or (overwrite == PROMPT
                        and prompt("%s is a file. Overwrite?" % targetDir))):
                    # Overwrite - so remove the file that's in the way
                    os.remove(targetDir)
                else:
                    # Don't overwrite file with directory.

                    if not quiet:
                        print("ERROR: attempting to overwrite a file with a "
                              "directory!",
                              file=sys.stderr)

                    raise OSError("Cannot overwrite a file with a directory!")

            # Everything _should_ be okay. Create destination directory
            if verbose:
                print("Creating %s" % targetDir)

            os.makedirs(targetDir)
        except OSError:
            if not quiet:
                print("ERROR: Failed to create %s!" % targetDir,
                      file=sys.stderr)

    return


def convertAudioFiles(sourceFiles, destinationFiles, configsettings,
                      noninteractive, verbose, quiet):
    """Convert audio files of various formats to mp3.

    Uses FFmpeg to convert audio files with non-mp3 extensions (as
    specified in the config settings) to mp3s. Returns a list of paths
    to the mp3 files created.

    The input arguments for the source and destination files are
    expected to be in terms of absolute paths; furthermore, their
    indices are expected to correspond to each other.

    If the user has an old version of FFmpeg, it's quite possible that
    metadata will fail to transfer to the converted file. On later
    versions this is done by default, so I haven't specified that option
    here.

    TODO1: Implement the "prompt for convert" setting more intelligently.
    Right now it asks for every single file it it has been instructed to
    prompt. Probably what would be better is to assume that a 'yes' to
    convert means a 'yes' for every other file to convert in that same
    directory.

    TODO2: When a file is overwritten it has the potential to be
    double-counted on the file transfer lists.
    """
    # Quality setting for conversions. See:
    # https://trac.ffmpeg.org/wiki/Encode/MP3
    QUALITY = '0'

    # Load extensions to convert from config file
    flacConvert = configsettings.getint('ConvertFLACtoMP3')
    alacConvert = configsettings.getint('ConvertALACtoMP3')
    aacConvert = configsettings.getint('ConvertAACtoMP3')
    m4aConvert = configsettings.getint('ConvertM4AtoMP3')
    mp4Convert = configsettings.getint('ConvertMP4toMP3')
    oggConvert = configsettings.getint('ConvertOGGtoMP3')

    # Put these extensions in a list along with the option specifying
    # whether to prompt. Given that PROMPT is 2, YES is 1, and NO is 0,
    # we have that promptOption = convertOption - 1
    extensionList = []

    if flacConvert:
        extensionList += [['.flac', flacConvert - 1]]
    if alacConvert:
        extensionList += [['.alac', alacConvert - 1]]
    if aacConvert:
        extensionList += [['.aac', aacConvert - 1]]
    if m4aConvert:
        extensionList += [['.m4a', m4aConvert - 1]]
    if mp4Convert:
        extensionList += [['.mp4', mp4Convert - 1]]
    if oggConvert:
        extensionList += [['.ogg', oggConvert - 1]]

    # Return an empty list if we don't need to convert anything
    if not extensionList:
        return []

    # We need to look for files to convert. Determine how noisy and how
    # interactive FFmpeg should be.
    logsetting = ['-loglevel']

    if quiet:
        logsetting += ['fatal']
    elif verbose:
        logsetting += ['info']
    else:
        logsetting += ['warning']

    if noninteractive:
        # Don't overwrite already converted files if they exist
        overwritesetting = ['-n']
    else:
        overwritesetting = []

    # List of files converted
    convertedFiles = []

    # Convert each file as necessary
    for oldFile in sourceFiles:
        for extension, promptOption in extensionList:
            # If we match an extention, prompt if necessary
            if (oldFile.lower().endswith(extension)
                and (not promptOption
                     or (not noninteractive
                         and prompt("Convert %s?" % oldFile)))):
                # Convert the file!
                if not quiet:
                    print("Converting %s" % oldFile)

                newFile = oldFile[:-len(extension)] + '.mp3'
                command = (['ffmpeg']
                           + ['-i', oldFile]
                           + overwritesetting
                           + logsetting
                           + ['-hide_banner']
                           + ['-codec:a', 'libmp3lame']
                           + ['-qscale:a', QUALITY]
                           + [newFile])

                # Give stdin and stdout to user and wait for completion
                convertProcess = subprocess.Popen(command)
                exitCode = convertProcess.wait()

                if exitCode:
                    # Failed to convert
                    if not quiet:
                        print("ERROR: failed to convert %s" % oldFile,
                              file=sys.stderr)
                else:
                    # Success. Add to list of converted files
                    convertedFiles += [newFile]

                    # Swap the source and destination files with the new
                    # converted file-name.
                    oldFileIndex = sourceFiles.index(oldFile)
                    oldDestination = destinationFiles[oldFileIndex]
                    newDestination = oldDestination[:-len(extension)] + '.mp3'

                    sourceFiles[oldFileIndex] = newFile
                    destinationFiles[oldFileIndex] = newDestination

                # Move on to next file
                break

    return convertedFiles


def copyFiles(sourceFiles, destinationFiles, configsettings, noninteractive,
              verbose, quiet):
    """Copy files from source to destination.

    Use cp with options specified in config settings to copy each file
    specified in sourceFiles to the corresponding destination specified
    in destinationFiles (the indices of each corresponding pair match).
    """
    # Determines which options to supply with cp given config settings.
    cpOptions = []

    # Determine whether to overwrite destination files in case of
    # conflict
    overwritesetting = configsettings.getint('OverwriteDestinationFiles')

    if overwritesetting == YES:
        # cp --force
        cpOptions += ['-f']
    elif overwritesetting == PROMPT and not noninteractive:
        # cp --interactive
        cpOptions += ['-i']
    else:
        # cp --no-clobber
        cpOptions += ['-n']

    # Determine whether to be verbose
    if verbose:
        cpOptions += ['-v']

    # Copy the files to the destination directory
    for source, destination in zip(sourceFiles, destinationFiles):

        # Give stdin and stdout to user and wait for completion
        copyProcess = subprocess.Popen(["cp", source, destination] + cpOptions)
        exitCode = copyProcess.wait()

        if exitCode:
            # Failed to copy
            if not quiet:
                print("ERROR: failed to copy %s" % source, file=sys.stderr)

    return


def unmount(mountLocation, verbose):
    """Unmount device and return exit code."""
    noiseLevel = []
    if verbose:
        noiseLevel += ['-v']

    exitCode = subprocess.Popen(['sudo', 'umount', mountLocation]
                                + noiseLevel).wait()
    return exitCode


def mount(mountLocation, verbose):
    """Mount device and return exit code."""
    noiseLevel = []
    if verbose:
        noiseLevel += ['-v']

    exitCode = subprocess.Popen(['sudo', 'mount', mountLocation]
                                + noiseLevel).wait()
    return exitCode


def fatsort(mountLocation, verbose):
    """fatsort device and return exit code."""
    noiseLevel = []
    if not verbose:
        noiseLevel += ['-q']

    exitCode = subprocess.Popen(['sudo', 'fatsort', mountLocation]
                                + noiseLevel).wait()
    return exitCode


if __name__ == '__main__':
    # Parse input arguments
    parser = argparse.ArgumentParser(
            prog=NAME__,
            description="<program description goes here>")
    parser.add_argument(
            "sources",
            nargs='+',
            type=str,
            help="Relative path to source directories or files")
    parser.add_argument(
            "destination",
            type=str,
            help="Relative path to destination directory or file")
    parser.add_argument(
            "-f", "--no-fatsort",
            help="Do not unmount, fatsort, and remount",
            action="store_true")
    parser.add_argument(
            "-n", "--non-interactive",
            help="Abort instead of interactively resolving errors",
            action="store_true")
    parser.add_argument(
            "--version",
            action='version',
            version="%(prog)s 0.0.1")
    parser.add_argument(
            "--config-file",
            help="Use specified config file",
            type=str,
            default="config.ini")
    parser.add_argument(
            "--default",
            help="Use default settings from config file",
            action="store_true")
    parser.add_argument(
            "--armin",
            help="Use 'ARMIN' settings from config file",
            action="store_true")
    parser.add_argument(
            "--verbose",
            help="Give maximal output",
            action="store_true")
    parser.add_argument(
            "--quiet", "--silent",
            help="Give minimal output",
            action="store_true")
    args = parser.parse_args()



    # Parse config file
    config = configparser.ConfigParser()

    if args.verbose:
        print("Reading config file '%s'. . ." % args.config_file)

    # Try reading config file specified, and exit if failure. If config
    # can't read successfully it just returns an empty list.
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
    # dictionary.  See the config .ini file specified by the runtime
    # argument '--config-file' to see config options available
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

        rootAccess = requestRootAccess(cfgSettings, args.non_interactive,
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

        if fatsortAvailable():
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
    devLoc, mntLoc = findDeviceLocation(args.destination,
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
        getSourceAndDestinationLists(args.sources, args.destination,
                                     args.verbose, args.quiet))

    if args.verbose:
        print("Success: source and destination locations found")



    # Filter out certain file types based on settings in config file
    if args.verbose:
        print("Filtering out unwanted file types . . .")

    filterOutExtensions(fromFiles, toFiles, cfgSettings, args.non_interactive)

    if args.verbose:
        print("Success: filtering complete")



    # Perform necessary audio file conversions as specified in config
    # file
    if args.verbose:
        print("Checking whether to convert any audio files . . .")

    # Returns a list of temporary source files to remove later
    tmpFiles = convertAudioFiles(fromFiles, toFiles, cfgSettings,
                                 args.non_interactive, args.verbose,
                                 args.quiet)

    if args.verbose:
        print("Success: conversions finished")



    # Create necessary directories to transfer to
    if args.verbose:
        print("Creating destination directories . . .")

    createDirsAndParents(toDirs, cfgSettings, args.non_interactive,
                         args.verbose, args.quiet)

    if args.verbose:
        print("Success: destination directories created")



    # Copy source files to destination
    if args.verbose:
        print("Copying files . . .")

    copyFiles(fromFiles, toFiles, cfgSettings, args.non_interactive,
              args.verbose, args.quiet)

    if args.verbose:
        print("Success: files copied")



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

    # Delete source directory if asked to



    # If in armin mode, rename destination directories




    # Unmount, fatsort, and remount if we're asked to
    if not args.no_fatsort:
        # Unmount
        if args.verbose:
            print("Unmounting %s . . ." % mntLoc)

        if not unmount(mntLoc, args.verbose):
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

        if not fatsort(mntLoc, args.verbose):
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

        if not mount(mntLoc, args.verbose):
            if not args.quiet:
                print("ERROR: failed to remount %s!" % mntLoc, file=sys.stderr)

            print("Aborting %s" % NAME__)
            sys.exit(1)
        else:
            if args.verbose:
                print("Success: %s remounted" % mntLoc)
