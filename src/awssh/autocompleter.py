"""AWS SSH autocompleter script."""

# Standard Python Libraries
import configparser
import os
from pathlib import Path
import re
import shlex
from typing import Optional, TextIO

# Third-Party Libraries
import boto3

from . import CREDENTIAL_DIR, DEFAULT_CREDENTIAL_FILE

CREDENTIALS_OPTIONS = {"--credentials", "-c"}
HELP_OPTIONS = {"--help", "-h"}
LOG_LEVEL_OPTIONS = {"--log-level"}
LOG_LEVELS = {"debug", "info", "warning", "error", "critical"}
REGION_OPTIONS = {"--region", "-r"}
SSH_ARGS_OPTIONS = {"--ssh-args", "-s"}

if os.environ.get("LC_CTYPE", "") == "UTF-8":
    os.environ["LC_CTYPE"] = "en_US.UTF-8"

# Debugging the completer can be touchy since standard out goes to bash.
# Set the environment below to a filename to enable logging.
LOG_FILE: Optional[TextIO] = None
if filename := os.environ.get("BASH_COMP_DEBUG_FILE"):
    LOG_FILE = open(filename, "a", encoding="utf-8")


def log(message: str) -> None:
    """Log a message to the log file if it is open.

    Args:
        message (str): The message to log.
    """
    if LOG_FILE:
        print(message, file=LOG_FILE)


def get_cred_files() -> set[str]:
    """Return a set of all credential files in the credential directory.

    Returns:
        set[str]: A set of all credential files in the credential directory.
    """
    result: set[str] = set()
    for i in CREDENTIAL_DIR.iterdir():
        if i.is_file():
            result.add(i.name)
    return result


def get_regions() -> set[str]:
    """Return a set of all available AWS regions.

    Returns:
        set[str]: A set of all available AWS regions.
    """
    session = boto3.session.Session(region_name="us-east-1")
    return set(session.get_available_regions("ec2"))


def get_profiles(cred_filename: Path, profile_filter: Optional[str] = None) -> set[str]:
    """Return a set of profiles within a credential file that match the filter.

    Args:
        cred_filename (Path): The path to the credential file.
        profile_filter (Optional[str], optional): Regular expression to match profile names. Defaults to None.

    Returns:
        set[str]: A set of profiles within a credential file that match the filter.
    """
    if profile_filter:
        profile_filter_re: re.Pattern[str] = re.compile(profile_filter)
    config = configparser.ConfigParser()
    config.read(cred_filename)
    result: set[str] = set()
    for section in config.sections():
        if not profile_filter_re or profile_filter_re.search(section):
            result.add(section)
    return result


def get_instances(
    credential_file: Path, profile: str, region: str
) -> set[tuple[str, str]]:
    """Return a set of instances and names that match the profile and region.

    Args:
        credential_file (Path): The path to the credential file.
        profile (str): The profile to use.
        region (str): The AWS region to use.

    Returns:
        set[tuple[str, str]]: A set of instances and names that match the profile and region.
    """
    # Create session
    # boto3 doesn't have a programatic way to set the credential file. yuck.
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(credential_file)
    session = boto3.session.Session(region_name=region, profile_name=profile)
    ec2 = session.resource("ec2")
    instances = {}
    # Loop through instances that are running
    for i in ec2.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    ):
        # convert tags into a proper dictionary
        if i.tags is None:
            # if an instance has no tags use the id as the Name
            log(f"warning: instance does not have tags: {i}")
            i.tag_dict = {"Name": i.id}
        else:
            i.tag_dict = {tag["Key"]: tag["Value"] for tag in i.tags}
        instances[i.tag_dict["Name"]] = i

    result: set[tuple[str, str]] = set()
    for name, instance in instances.items():
        result.add((instance.id, name))
    return result


def build_option_candidates(word_set: set[str]) -> set[str]:
    """Return a set of command line option candidates for the given word set.

    Args:
        word_set (set[str]): The set of words to build option candidates for.

    Returns:
        set[str]: A set of command line option candidates for the given word set.
    """
    candidates: set[str] = set()
    if HELP_OPTIONS & word_set:
        return candidates
    if len(word_set) <= 1:
        candidates |= HELP_OPTIONS
    if not CREDENTIALS_OPTIONS & word_set:
        candidates |= CREDENTIALS_OPTIONS
    if not LOG_LEVEL_OPTIONS & word_set:
        candidates |= LOG_LEVEL_OPTIONS
    if not REGION_OPTIONS & word_set:
        candidates |= REGION_OPTIONS
    if not SSH_ARGS_OPTIONS & word_set:
        candidates |= SSH_ARGS_OPTIONS
    return candidates


class ParsedState(object):
    """A class to hold the state of the command line parser."""

    def __init__(self):
        """Initialize the ParsedState object."""
        self.aws_region: str = os.environ.get("AWS_REGION")
        self.cred_file: Path = Path(
            os.environ.get("AWS_SHARED_CREDENTIALS_FILE", DEFAULT_CREDENTIAL_FILE)
        )
        self.instance: str = None
        self.profile: str = None  # os.environ.get("AWS_PROFILE")
        self.ssh_args: str = None
        self.ssh_command: list[str] = None


def parse_command_line(words: list[str]) -> ParsedState:
    """Parse the command line and return the parsed state.

    Args:
        words (list[str]): The command line words to parse.

    Returns:
        ParsedState: The parsed state.
    """
    state: ParsedState = ParsedState()
    pos_args: list[str] = []
    i = iter(words[:-1])
    try:
        while True:
            word = next(i)
            if word in CREDENTIALS_OPTIONS:
                state.cred_file = Path(CREDENTIAL_DIR) / Path(next(i))
            elif word in REGION_OPTIONS:
                state.aws_region = next(i)
            elif word in LOG_LEVEL_OPTIONS:
                next(i)  # don't care
            elif word in SSH_ARGS_OPTIONS:
                state.ssh_args = next(i)
            elif not word.startswith("-"):
                pos_args.append(word)
    except StopIteration:
        pass
    if pos_args:
        state.profile = pos_args.pop(0)
    if pos_args:
        state.instance = pos_args.pop(0)
    if pos_args:
        state.ssh_command = pos_args
    return state


def process_command_line(
    command_line: str, command_index: int
) -> tuple[list[str], str, str]:
    """Process the command line and return the command line words, the command, and the command index.

    Args:
        command_line (str): The command line to process.
        command_index (int): The index of the current command in the command line.

    Returns:
        tuple[list[str], str, str]: The command line words, the command, and the command index.
    """
    # Chop the command line at the current cursor location
    command_line = command_line[:command_index]
    log(f"chopped command line is: {command_line}")
    words = shlex.split(command_line)
    del words[0]  # delete the command itself
    if command_line[-1].isspace():
        # add a new empty word since we have a trailing space
        words.append("")
    cur_word = words[-1] if len(words) > 0 else ""
    prev_word = words[-2] if len(words) > 1 else ""
    log(f"words is {words}")
    log(f"cur_word is {cur_word}, prev_word is {prev_word}")
    return words, cur_word, prev_word


def autocomplete(command_line: str, command_index: int) -> tuple[set[str], str]:
    """Autocomplete the command line and return the autocomplete set and the current word.

    Args:
        command_line (str): The command line to autocomplete.
        command_index (int): The index of the current command in the command line.

    Returns:
        tuple(set[str], str): The autocomplete set and the current word.
    """
    log("-" * 40)
    log(f"command_line is {command_line}, command_index is {command_index}")
    words: list[str]
    cur_word: str
    prev_word: str
    words, cur_word, prev_word = process_command_line(command_line, command_index)
    word_set: set[str] = set(words)

    # Calculate the state from the current commandline
    state = parse_command_line(words)
    log(f"state is {state.__dict__}")

    # Build a list of candidate completions
    candidates: set[str] = set()

    # If we are working on an option, then suggest parameters for that option.
    if prev_word in CREDENTIALS_OPTIONS:
        candidates |= get_cred_files()
    elif prev_word in LOG_LEVEL_OPTIONS:
        candidates |= LOG_LEVELS
    elif prev_word in REGION_OPTIONS:
        candidates |= get_regions()
    else:
        # Not working on an option parameter
        if not state.profile:
            # If we don't have the positional profile argument, suggest options
            candidates |= build_option_candidates(word_set)

        # If we have enough optional information start suggesting positional parameters
        if state.cred_file.is_file() and state.aws_region:
            profile_filter = os.environ.get("AWSSH_PROFILE_FILTER")
            profiles = get_profiles(state.cred_file, profile_filter)
            if state.profile not in profiles:
                candidates |= profiles

            # If we have enough information suggest instance ids and names
            if not state.instance and state.profile in profiles:
                instances: set[tuple[str, str]] = get_instances(
                    state.cred_file, state.profile, state.aws_region
                )
                # Build sets of id-name pairs, and names alone
                instance_id_and_name: set[str] = {f"{i[0]} {i[1]}" for i in instances}
                instance_names: set[str] = {i[1] for i in instances}

                # Include the names alone.  They will be substituted with an
                # instance id when only one candidate is left.
                candidates |= instance_names

                # Filter instances now so we can strip off the name if there is only one
                filtered_id_and_name = {
                    i for i in instance_id_and_name if cur_word in i
                }
                if len(filtered_id_and_name) == 1:
                    # If there is only one matching instance, remove the Name suffix
                    candidates = {filtered_id_and_name.pop().split()[0]}
                else:
                    candidates |= instance_id_and_name

    return candidates, cur_word


def print_completions(comps: set[str], cur: str) -> None:
    """Output the completions to stdout.

    Args:
        comps (set[str]): The completions to output.
        cur (str): The current word.
    """
    log(f"completions: {sorted(comps)}")
    contains: list[str] = []
    starts: list[str] = []
    for i in sorted(comps):
        if i.startswith(cur):
            starts.append(i)
        if cur in i or cur == "":
            contains.append(i)
    log(f"starts with: {starts}")
    log(f"contains: {contains}")
    # Prefer completions in this order:
    # 1. completions that start with the current word
    # 2. completions that contain the current word
    # 3. other candidates that matched some other way (e.g., by instance name)
    for i in starts or contains or comps:
        print(i)


def main() -> int:
    """Execute main entry point for the awssh autocomplete script.

    Returns:
        int: The exit code.
    """
    # bash exports COMP_LINE and COMP_POINT, tcsh COMMAND_LINE only
    command_line: str = (
        os.environ.get("COMP_LINE") or os.environ.get("COMMAND_LINE") or ""
    )
    command_index: int = int(os.environ.get("COMP_POINT") or len(command_line))

    try:
        candidates: set[str]
        cur_word: str
        candidates, cur_word = autocomplete(command_line, command_index)

        print_completions(candidates, cur_word)
    except KeyboardInterrupt:
        # If the user hits Ctrl+C, we don't want to print
        # a traceback to the user.
        pass
    return 0
