#!/usr/bin/env python3
# coding: utf-8
"""Copy files to a device and fatsort that device.

trans-fat - main script
~~~~~~~~~~~~~~~~~~~~~~~

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
import subprocess
import distutils.util
import shutil
import armin

# Name of the program
NAME__ = "trans-fat"

# Constants mirrored in the config file
NO = 0
YES = 1
PROMPT = 2


def prompt(query):
    """Prompt a yes/no question and get an answer.

    A simple function to ask yes/no questions on the command line.
    Credit goes to Matt Stevenson. See:
    http://mattoc.com/python-yes-no-prompt-cli.html

    Args:
        query: A string containing a question.

    Returns:
        A boolean corresponding to the answer to the question asked.
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
    """Return true if fatsort is available and false otherwise.

    Checks if fatsort is available to the user.

    Returns:
        A boolean signaling whether fatsort is available.
    """
    fatCheck = subprocess.Popen(["bash", "-c", "type fatsort"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    exitCode = fatCheck.wait()
    return bool(exitCode)


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
            cache_ = prompt("Remember root access passphrase?")

        # Run 'sudo -k' if we aren't caching credentials
        if cache_ == NO:
            cacheOption = ['-k']

    # Replace currently-running process with root-access process
    if verbose:
        print("Restarting as root . . .")

    sudoCmd = (['sudo']
               + cacheOption
               + [sys.executable]
               + sys.argv
               + [os.environ])
    os.execlpe('sudo', *sudoCmd)


def findDeviceLocation(destinationPath, noninteractive=False, verbose=False,
                       quiet=False):
    """Return device and mount locations of a FAT drive.

    Find device and mount locations of the FAT device corresponding to
    the supplied destination path. If these locations can't be found
    automatically, find them interactively. If all of this fails, return
    a 2-tuple of empty strings.

    Args:
        destinationPath: A string containing a path somewhere on the
            mounted device.
        noninteractive: An optional boolean toggling whether to omit
            interactively finding device and mount locations if doing so
            automatically fails.
        verbose: An optional boolean toggling whether to give extra
            output.
        quiet: An optional boolean toggling whether to omit error
            output.

    Returns:
        A 2-tuple containing device location and mount location strings;
        or, if these locations can't be found, a 2-tuple of empty
        strings.
    """
    # Make sure destination is an absolute path
    destination = os.path.abspath(destinationPath)

    # Get list of FAT devices
    bashListCmd = "mount -t vfat | cut -f 1,3 -d ' '"
    deviceListProcess = subprocess.Popen(["bash", "-c", bashListCmd],
                                         stdout=subprocess.PIPE)

    # Read the devices list from Popen
    deviceString = deviceListProcess.communicate()[0].decode('ascii')
    deviceString = deviceString.rstrip()

    # Check if any FAT devices were found
    if deviceString == '':
        # No FAT devices found, return empty string
        return ('', '')

    # Split deviceString so we get a separate string for each device
    deviceList = deviceString.split('\n')

    # For each device, split into device location and mount location.
    # So in deviceListSep, deviceListSep[i][0] gives the device location
    # and deviceListSep[i][1] gives the mount location of the ith device
    deviceListSep = [deviceList[i].split() for i in range(len(deviceList))]

    # Test if destination path matches any mount locations
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
        # Non-interactive mode is on, just return empty strings
        return ('', '')


def getCorrespondingPathsLists(sourcePaths, destinationPath, verbose=False,
                               quiet=False):
    """Return lists of corresponding source and destination paths.

    Generate corresponding lists of paths for source and destination
    files and source and destination directories. The indices of the two
    file lists will correspond to each other, and similarly, the indices
    of the two directory lists will correspond to each other.

    Args:
        sourcePaths: A list of strings containing source paths.
        destinationPath: A string containing a destination path.
        verbose: An optional boolean toggling whether to give extra
            output.
        quiet: An optional boolean toggling whether to omit error
            output.

    Returns:
        A 4-tuple containing (sourceDirs, sourceFiles, destinationDirs,
        destinationFiles) where ...

        sourceDirs: A list of strings containing absolute paths to
            source directories.
        sourceFiles: A list of strings containing absolute paths to
            source files.
        destinationDirs: A list of strings containing absolute paths to
            destination directories.
        destinationFiles: A list of strings containing absolute paths to
            destination files.

        and where the indices of sourceDirs and destinationDirs
        correspond to each other, and, similarly, where the indices of
        sourceFiles and destinationFiles correspond to each other.
    """
    # Make sure source and destination paths are absolute paths
    sourcePaths_ = [os.path.abspath(source) for source in sourcePaths]
    destinationPath_ = os.path.abspath(destinationPath)

    # Generate lists of source and destination paths
    sourceDirs = []
    sourceFiles = []
    destinationDirs = []
    destinationFiles = []

    # Go through each source
    for source in sourcePaths_:
        # Get the parent directory of the source so we can generate the
        # destination path
        parent = os.path.dirname(source)
        parentlen = len(parent)

        # Determine whether the source is a file or directory
        if os.path.isfile(source):
            # The source is a file, so add it to the file lists
            sourceFiles += [source]
            destinationFiles += [destinationPath_ + source[parentlen:]]
        elif os.path.isdir(source):
            # The source is a directory, so add itself and everything
            # inside of it to the appropriate lists
            for root, _, files in os.walk(source):
                sourceDirs += [root]
                sourceFiles += [root + '/' + file for file in files]
                destinationDirs += [destinationPath_ + root[parentlen:]]
                destinationFiles += [destinationPath_
                                     + root[parentlen:]
                                     + '/'
                                     + file
                                     for file in files]
        else:
            # The source is neither a file nor directory. Give a
            # warning.
            if not quiet:
                print("ERROR: '%s' does not exist!" % source,
                      file=sys.stderr)
            if verbose:
                print("Proceeding anyway. . .")

    return (sourceDirs, sourceFiles, destinationDirs, destinationFiles)


def filterOutExtensions(sourceFiles, destinationFiles, configsettings,
                        noninteractive=False):
    """Remove indices corresponding to unwanted files from lists.

    Filter out files of unwanted extensions from the list of source
    files and destination files.

    [*] The indices of the source file list and destination file list
    inputs must correspond to each other.

    Args:
        sourceFiles: A list of strings of absolute paths to source
            files. See [*] above.
        destinationFiles: A list of strings of absolute paths to
            destination files. See [*] above.
        configsettings: A dictionary-like 'configparser.SectionProxy'
            object containing configuration settings from config.ini.
        noninteractive: An optional boolean toggling whether to suppress
            prompts to remove files that may have been requested in the
            configuration file config.ini.

    Returns:
        Nothing. The work performed on the file lists is done in place.
    """
    # Load settings from config file
    imageOption = configsettings.getint('RemoveCue')
    logOption = configsettings.getint('RemoveLog')
    cueOption = configsettings.getint('RemoveCue')
    m3uOption = configsettings.getint('RemoveM3U')
    otherOption = configsettings.getint('RemoveOtherFiletypes')

    # Tuples of file extension types we care about
    audioExt = ('.flac', '.alac', '.aac', '.m4a', '.mp4', '.ogg', '.mp3')
    imageExt = ('.jpg', '.jpeg', '.bmp', '.png', '.gif')
    logExt = ('.log',)
    cueExt = ('.cue',)
    m3uExt = ('.m3u',)

    # Pair each file extension with its corresponding config setting
    extensionList = [[imageExt, imageOption],
                     [logExt, logOption],
                     [cueExt, cueOption],
                     [m3uExt, m3uOption]]

    # Gather all of the non-audio file extensions into one tuple
    nonAudioExt = ()
    for ext in extensionList:
        nonAudioExt += ext[0]

    # Initialize a list of indices corresponding to files to remove
    indexList = []

    # Find which files have extensions that we don't want and mark their
    # indices
    for file_ in sourceFiles:
        if file_.lower().endswith(audioExt):
            # This is an audio file; keep this file for sure
            pass
        elif file_.lower().endswith(nonAudioExt):
            # This matches one of the non-audio extensions. Find which
            # extension it is and remove the file from the file list as
            # instructed to by the config settings.
            for ext, removeOption in extensionList:
                if file_.lower().endswith(ext):
                    # Extension matched! Remove the file according to
                    # the config settings, prompting if necessary.

                    if ((removeOption == PROMPT
                         and (noninteractive or prompt("Move '%s'?" % file_)))
                            or removeOption == NO):
                        # Keep the file in the file list
                        break
                    else:
                        # Add index to list of indices to remove
                        indexList += [sourceFiles.index(file_)]
        else:
            # This is some other kind of file. Remove the file according
            # to the config settings, prompting if necessary.
            if ((otherOption == PROMPT
                 and (noninteractive or prompt("Move '%s'?" % file_)))
                    or otherOption == NO):
                # Keep the file in the file list
                pass
            else:
                # Add index to list of indices to remove
                indexList += [sourceFiles.index(file_)]

    # Remove files we don't want from the file lists, going through the
    # indices in reverse order
    for index in indexList[::-1]:
        sourceFiles.pop(index)
        destinationFiles.pop(index)

    return


def createDirectories(directoriesList, noninteractive=False, verbose=False,
                      quiet=False):
    """Create directories specified by a list.

    Create all of the directories specified in a list, asking whether to
    overwrite any files blocking the way as necessary.

    Args:
        directoriesList: A list of strings containing absolute paths to
            directories to be created.
        noninteractive: An optional boolean signaling not to overwrite
            files with directories, and not to prompt for this.
        verbose: An optional boolean toggling whether to give extra
            output.
        quiet: An optional boolean toggling whether to omit error
            output.
    """
    # Determine whether to prompt to overwrite files
    if noninteractive:
        doprompt = False
    else:
        doprompt = True

    # Create each directory
    for targetDir in directoriesList:
        try:
            # Check if the directory already exists; if it does, move on
            # to the next directory.
            if verbose:
                print("Checking %s . . ." % targetDir)

            if os.path.isdir(targetDir):
                # Already a directory
                if verbose:
                    print("%s already exists" % targetDir)

                continue

            # Check if we're attempting to overwrite a file
            if os.path.isfile(targetDir):
                # Prompt to overwrite if necessary
                if doprompt and prompt("%s is a file. Overwrite?" % targetDir):
                    # Overwrite - remove the file that's in the way
                    os.remove(targetDir)
                else:
                    # Don't overwrite file with directory.
                    if not quiet:
                        print("ERROR: attempting to overwrite a file with a "
                              "directory!",
                              file=sys.stderr)

                    raise OSError("Cannot overwrite a file with a directory!")

            # Create directory
            if verbose:
                print("Creating %s" % targetDir)

            os.makedirs(targetDir)
        except OSError:
            if not quiet:
                print("ERROR: Failed to create %s!" % targetDir,
                      file=sys.stderr)

    return


def convertAudioFiles(sourceFiles, destinationFiles, configsettings,
                      noninteractive=False, verbose=False, quiet=False):
    """Convert non-mp3 audio files to mp3.

    Uses FFmpeg to convert audio files with non-mp3 extensions (as
    specified in the config settings) to mp3s. Returns a list of paths
    to the mp3 files created, and updates the source and destination
    file lists in place, replacing the original files with the newly
    converted files.

    The input arguments for the source and destination files are
    expected to be in terms of absolute paths; [*] furthermore, their
    indices are expected to correspond to each other.

    If the user has an old version of FFmpeg, it's quite possible that
    metadata will fail to transfer to the converted file. On later
    versions this is done by default, so I haven't specified that option
    here.

    TODO(mwiens91): Implement the "prompt for convert" setting more
    intelligently.  Right now it asks to convert every single file it
    has been instructed to prompt for. Probably what would be better is
    to assume that a 'yes' to convert means a 'yes' for every other file
    to convert in that same directory.

    TODO(mwiens91): When a file is overwritten it has the potential to
    be double-counted on the file transfer lists.

    Args:
        sourceFiles: A list of strings of absolute paths to source
            files. See [*] above.
        destinationFiles: A list of strings of absolute paths to
            destination files. See [*] above.
        configsettings: A dictionary-like 'configparser.SectionProxy'
            object containing configuration settings from config.ini.
        noninteractive: An optional boolean signalling to never ask to
            convert files that it would otherwise prompt for, and
            furthermore, to not do such conversions.
        verbose: An optional boolean toggling whether to give extra
            output.
        quiet: An optional boolean toggling whether to omit both error
            output and output to signal that the non-interactive flag
            has prevented a conversion from taking place.

    Returns:
        A list of strings containing the absolute paths of the files
        created by conversion. Also modifies the source and destination
        file lists in place such that the original files are replaced by
        the newly converted files.
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
        for extension, doprompt in extensionList:
            # If we match an extention, prompt if necessary
            extensionMatch = oldFile.lower().endswith(extension)

            if (extensionMatch and (not doprompt
               or (not noninteractive and prompt("Convert %s?" % oldFile)))):
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
            elif extensionMatch and (doprompt and noninteractive):
                # Non-interactive wins over prompt setting - so don't
                # convert
                if not quiet:
                    print("Not converting %s" % oldFile)

    return convertedFiles


def copyFiles(sourceFiles, destinationFiles, configsettings,
              noninteractive=False, verbose=False, quiet=False):
    """Copy files from a source to a destination.

    Use cp with options specified in config settings to copy each source
    file into a destination file.

    [*] The indices of the source file list and destination file list
    inputs must correspond to each other.

    Args:
        sourceFiles: A list of strings of absolute paths to source
            files. See [*] above.
        destinationFiles: A list of strings of absolute paths to
            destination files. See [*] above.
        configsettings: A dictionary-like 'configparser.SectionProxy'
            object containing configuration settings from config.ini.
        noninteractive: An optional boolean signalling to never run cp
            with its interactive flag.
        verbose: An optional boolean toggling whether to run cp with its
            verbose flag.
        quiet: An optional boolean toggling whether to omit error
            output.
    """
    # Initialize list of options to run cp with
    cpOptions = []

    # Determine whether to overwrite destination files if there's a
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


def unmount(deviceLocation, verbose=False):
    """Unmount a device and return an exit code."""
    noiseLevel = []
    if verbose:
        noiseLevel += ['-v']

    exitCode = subprocess.Popen(['sudo', 'umount', deviceLocation]
                                + noiseLevel).wait()
    return exitCode


def mount(deviceLocation, verbose=False):
    """Mount a device and return an exit code."""
    noiseLevel = []
    if verbose:
        noiseLevel += ['-v']

    exitCode = subprocess.Popen(['sudo', 'mount', deviceLocation]
                                + noiseLevel).wait()
    return exitCode


def fatsort(deviceLocation, verbose=False):
    """fatsort a device and return an exit code."""
    noiseLevel = []
    if not verbose:
        noiseLevel += ['-q']

    exitCode = subprocess.Popen(['sudo', 'fatsort', deviceLocation]
                                + noiseLevel).wait()
    return exitCode


def deletePaths(paths, doprompt=True, verbose=False, quiet=False):
    """Delete a list of files and directories possibly containing files.

    Removes the files and directories (recursively) specified, prompting
    if necessary.

    Args:
        paths: A list of strings containing absolute paths.
        doprompt: An optional boolean signalling to prompt before
            deleting anything.
        verbose: An optional boolean toggling whether to give extra
            output.
        quiet: An optional boolean toggling whether to omit error
            output.
    """
    for thing in paths:
        # Prompt to delete if necessary
        if doprompt:
            if not prompt("Remove %s?" % thing):
                # Don't delete this thing
                break

        if verbose:
            print("Removing %s" % thing)

        # Delete the thing!
        try:
            if os.path.isfile(thing):
                os.remove(thing)
            elif os.path.isdir(thing):
                shutil.rmtree(thing)
            elif not os.path.exists(thing):
                # Nothing here
                raise OSError
            else:
                # Something very strange happened
                raise UserWarning
        except (OSError, shutil.Error):
            # Such error!
            if not quiet:
                print("ERROR: failed to remove %s" % thing, file=sys.stderr)

    return


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
        getCorrespondingPathsLists(args.sources, args.destination,
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

    createDirectories(toDirs, args.non_interactive, args.verbose, args.quiet)

    if args.verbose:
        print("Success: destination directories created")



    # Copy source files to destination
    if args.verbose:
        print("Copying files . . .")

    copyFiles(fromFiles, toFiles, cfgSettings, args.non_interactive,
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

        deletePaths(args.sources, promptFlag, args.verbose, args.quiet)

        if args.verbose:
            print("Success: source files and directories removed")



    # Unmount, fatsort, and remount if we're asked to
    if not args.no_fatsort:
        # Unmount
        if args.verbose:
            print("Unmounting %s . . ." % mntLoc)

        if not unmount(devLoc, args.verbose):
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

        if not fatsort(devLoc, args.verbose):
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

        if not mount(devLoc, args.verbose):
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
