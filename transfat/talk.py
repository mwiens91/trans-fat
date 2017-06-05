"""Contains functions for communicating with a user."""

import distutils.util
import sys
from .version import NAME


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


def status(message, verbose=True):
    """Print a status update if a flag is true."""
    if verbose:
        print(message)
    return


def success(message, verbose=True):
    """Print a success message if a flag is true."""
    if verbose:
        print("Success: " + message)
    return


def error(error_message, quiet=False):
    """Print an error message to stderr if a flag is false."""
    if not quiet:
        print("ERROR: " + error_message, file=sys.stderr)
    return


def aborting():
    """Prints that the program is aborting."""
    print("Aborting %s" % NAME)
    return


if __name__ == '__main__':
    # Self-test code
    error("oh mah %s!" % "god")
    aborting()
