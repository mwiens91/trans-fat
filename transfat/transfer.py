"""Contains functions used to copy and process (mostly audio) files."""

import os
import shutil
import subprocess
from . import talk
from .config.constants import NO, YES, PROMPT


def getCorrespondingPathsLists(sourcePaths, destinationPath, verbose=False,
                               quiet=False):
    """Return lists of corresponding source and destination paths.

    Generate corresponding lists of paths for source and destination
    files and source and destination directories. The indices of the two
    file lists will correspond to each other, and similarly, the indices
    of the two directory lists will correspond to each other.

    Args:
        sourcePaths: A list of strings containing source paths, which
            can be files or directories.
        destinationPath: A string containing a destination path for
            where the source files/directories should be transfered to.
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
            talk.error("'%s' does not exist!" % source, quiet)
            talk.status("Proceeding anyway", verbose)

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
    imageOption = configsettings.getint('RemoveImages')
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
    for file_ in destinationFiles:
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
                        and (noninteractive
                             or talk.prompt("Move '%s'?" % file_)))
                            or removeOption == NO):
                        # Keep the file in the file list
                        break
                    else:
                        # Add index to list of indices to remove
                        indexList += [destinationFiles.index(file_)]
        else:
            # This is some other kind of file. Remove the file according
            # to the config settings, prompting if necessary.
            if ((otherOption == PROMPT
                 and (noninteractive or talk.prompt("Move '%s'?" % file_)))
                    or otherOption == NO):
                # Keep the file in the file list
                pass
            else:
                # Add index to list of indices to remove
                indexList += [destinationFiles.index(file_)]

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
            talk.status("Checking %s" % targetDir, verbose)

            if os.path.isdir(targetDir):
                # Already a directory
                talk.status("%s already exists" % targetDir, verbose)

                continue

            # Check if we're attempting to overwrite a file
            if os.path.isfile(targetDir):
                # Prompt to overwrite if necessary
                if (doprompt
                   and talk.prompt("%s is a file. Overwrite?" % targetDir)):
                    # Overwrite - remove the file that's in the way
                    os.remove(targetDir)
                else:
                    # Don't overwrite file with directory.
                    talk.error("Attempting to overwrite a file with a"
                               " directory!", quiet)
                    raise OSError("Cannot overwrite a file with a directory!")

            # Create directory
            talk.status("Creating %s" % targetDir, verbose)
            os.makedirs(targetDir)
        except OSError:
            talk.error("Failed to create %s!" % targetDir, quiet)

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

    # Make sure we don't prompt if we're in non-interactive mode
    if noninteractive:
        for pair in extensionList:
            if pair[1] == PROMPT:
                # Don't convert this extension
                pairIndex = extensionList.index(pair)
                extensionList.pop(pairIndex)

    # Return an empty list if we don't need to convert anything
    if not extensionList:
        return []

    # We need to look for files to convert. Determine how noisy FFmpeg
    # should be.
    if quiet:
        logsetting = 'fatal'
    elif verbose:
        logsetting = 'info'
    else:
        logsetting = 'warning'

    # List of files converted
    convertedFiles = []

    # Don't prompt more than once to convert the same file extension in
    # the same directory.  Initialize a whitelist and blacklist for
    # this, [**] which will contain lists of two-tuples of ("dirpath",
    # "extension")
    whitelist = []
    blacklist = []

    # Convert each file as necessary
    for oldFile in sourceFiles:
        for extension, prompt in extensionList:
            # Find if the extensions match
            extensionMatch = oldFile.lower().endswith(extension)

            if extensionMatch:
                # An extension matched!
                if prompt:
                    # Work out whether we're on the whitelist,
                    # blacklist, or whether we should prompt for this
                    # file. See [**] above for more details.
                    container = os.path.dirname(oldFile)

                    if (container, extension) in whitelist:
                        # Convert the file
                        pass
                    elif (container, extension) in blacklist:
                        # Move on to next file
                        break
                    else:
                        # Prompt and modify white/black-lists
                        # accordingly
                        if talk.prompt(
                           "Convert %s and other %s's in the same directory?"
                           % (oldFile, extension)):
                            # Add to whitelist and convert
                            whitelist += [(container, extension)]
                        else:
                            # Add to blacklist and move on to next file
                            blacklist += [(container, extension)]
                            break

                # Convert the file!
                talk.status("Converting %s" % oldFile, verbose)

                newFile = oldFile[:-len(extension)] + '.mp3'
                command = (['ffmpeg']
                           + ['-n']
                           + ['-hide_banner']
                           + ['-loglevel', logsetting]
                           + ['-i', oldFile]
                           + ['-codec:a', 'libmp3lame']
                           + ['-qscale:a', QUALITY]
                           + [newFile])

                # Give stdin and stdout to user and wait for completion
                convertProcess = subprocess.Popen(command)
                exitCode = convertProcess.wait()

                if exitCode:
                    # Failed to convert
                    talk.error("Failed to convert %s" % oldFile, quiet)
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
            talk.error("Failed to copy %s" % source, quiet)

    return


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
            if not talk.prompt("Remove %s?" % thing):
                # Don't delete this thing
                break

        talk.status("Removing %s" % thing, verbose)

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
            talk.error("Failed to remove %s" % thing, quiet)

    return


def deleteFiles(filePaths, quiet=False):
    """Delete a list of files."""
    for path in filePaths:
        try:
            os.remove(path)
        except OSError:
            talk.error("Failed to remove %s!" % path, quiet)
    return
