"""awssh simplifies secure shell connections over AWS simple systems manager.

EXIT STATUS
    This utility exits with the same status as the underlying aws or ssh process:
    0   No error.
    >0  An error occurred.

Usage:
  awssh [options] <profile> <instance-id> [<command>...]
  awssh (-h | --help)

Options:
  -c --credentials=FILENAME     Shared credentials file name.
  -n --no-ssh                   Open an SSM shell session without using ssh.
  -r --region=REGION            AWS region name to use.
  -s --ssh-args=ARGUMENTS       Arguments to send to ssh.
  --log-level=LEVEL             If specified, then the log level will be set to
                                the specified value.  Valid values are "debug", "info",
                                "warning", "error", and "critical". [default: info]
  -h --help                     Show this message.
"""


# Standard Python Libraries
import logging
import os
from pathlib import Path
import subprocess  # nosec: B404 subprocess use is required for this tool
import sys
from typing import Any, Dict, Optional

# Third-Party Libraries
import docopt

# I cannot find a package that includes type stubs for schema, so I must add
# "type: ignore" to tell mypy to ignore this library
from schema import And, Schema, SchemaError, Use  # type: ignore

from . import CREDENTIAL_DIR
from ._version import __version__

# Options required for ssh to use ssm
# We will construct this for the user so they don't have to have it in their ssh config
# Note: They will probably still want to specify their own "User" option.
DEFAULT_SSH_OPTIONS = {
    "GSSAPIAuthentication": "yes",
    "GSSAPIDelegateCredentials": "yes",
    "ProxyCommand": """sh -c "aws ssm start-session --target %h --document-name AWS-StartSSHSession --parameters 'portNumber=%p'" """,
    "StrictHostKeyChecking": "no",
    "UserKnownHostsFile": "/dev/null",
}


def main() -> int:
    """Set up logging and prepare and SSM/ssh command."""
    args: Dict[str, str] = docopt.docopt(__doc__, version=__version__)

    # Validate and convert arguments as needed
    schema: Schema = Schema(
        {
            "--log-level": And(
                str,
                Use(str.lower),
                lambda n: n in ("debug", "info", "warning", "error", "critical"),
                error="Possible values for --log-level are "
                + "debug, info, warning, error, and critical.",
            ),
            str: object,  # Don't care about other keys, if any
        }
    )

    try:
        validated_args: Dict[str, Any] = schema.validate(args)
    except SchemaError as err:
        # Exit because one or more of the arguments were invalid
        print(err, file=sys.stderr)
        sys.exit(1)

    # Assign validated arguments to variables
    command: list[str] = validated_args["<command>"]
    credential_file: Optional[Path] = None
    if validated_args["--credentials"]:
        credential_file = CREDENTIAL_DIR / Path(validated_args["--credentials"])
    instance_id: str = validated_args["<instance-id>"]
    log_level: str = validated_args["--log-level"]
    no_ssh: bool = validated_args["--no-ssh"]
    profile: str = validated_args["<profile>"]
    region: str = validated_args["--region"]
    ssh_args: list[str]
    if validated_args["--ssh-args"]:
        ssh_args = validated_args["--ssh-args"].split()
    else:
        ssh_args = []

    if os.environ.get("AWSSH_USER"):
        ssh_args.append(f'-o User={os.environ["AWSSH_USER"]}')

    # Set up logging
    logging.basicConfig(
        format="%(asctime)-15s %(levelname)s %(message)s", level=log_level.upper()
    )

    returncode: int = _run_subprocess(
        credential_file, profile, region, instance_id, no_ssh, ssh_args, command
    )

    # Stop logging and clean up
    logging.shutdown()
    return returncode


def _run_subprocess(
    credential_file: Optional[Path],
    profile: str,
    region: Optional[str],
    instance_id: str,
    no_ssh: bool,
    ssh_args: list[str],
    remote_command: list[str],
) -> int:
    # Setup a modified environment for our awssh command
    awssh_env = os.environ.copy()
    if credential_file:
        awssh_env["AWS_SHARED_CREDENTIALS_FILE"] = str(credential_file)
    if region:
        awssh_env["AWS_DEFAULT_REGION"] = str(region)
    awssh_env["AWS_PROFILE"] = str(profile)
    if no_ssh:
        command = (
            ["aws", "ssm", "start-session"]
            + ["--target", instance_id]
            + ["--document-name", "SSM-SessionManagerRunShell"]
        )
    else:
        command = (
            ["ssh"]
            + [f"-o {key}={value}" for key, value in DEFAULT_SSH_OPTIONS.items()]
            + ssh_args
            + [instance_id]
            + remote_command
        )
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug("environment: ")
        for key in sorted(os.environ):
            logging.debug("%s=%s", key, os.environ[key])
        logging.debug("command: %s", " ".join(i for i in command))
    completed_process = (
        subprocess.run(  # nosec: B603 subprocess input is carefully validated
            args=command, env=awssh_env
        )
    )
    return completed_process.returncode
