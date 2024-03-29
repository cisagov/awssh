# awssh ☁️🔒🐚 #

[![GitHub Build Status](https://github.com/cisagov/awssh/workflows/build/badge.svg)](https://github.com/cisagov/awssh/actions)
[![CodeQL](https://github.com/cisagov/awssh/workflows/CodeQL/badge.svg)](https://github.com/cisagov/awssh/actions/workflows/codeql-analysis.yml)
[![Coverage Status](https://coveralls.io/repos/github/cisagov/awssh/badge.svg?branch=develop)](https://coveralls.io/github/cisagov/awssh?branch=develop)
[![Known Vulnerabilities](https://snyk.io/test/github/cisagov/awssh/develop/badge.svg)](https://snyk.io/test/github/cisagov/awssh)

This project provides a tool that simplifies secure shell connections over
[AWS Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/what-is-systems-manager.html)
(formerly known as SSM).

## Pre-requisites ##

- The [AWS CLI](https://aws.amazon.com/cli/) installed on your system.
- The [Session Manager plugin for the AWS CLI](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)
  installed on your system.
- A valid AWS profile that has permissions to start/stop SSM sessions.
- A [`bash`](https://www.gnu.org/software/bash/) shell.

## Usage ##

### Setup ###

1. Install the `awssh` command line utility.  One easy way to do this is
   to run the `setup-env` script in the main directory.
1. Define environment variables:
   - `AWSSH_PROFILE_FILTER`: A string that will match one or more profiles
     in your AWS configuration file that have permission to start/stop SSM
     sessions.
   - `AWSSH_USER`: The username to use for ssh connections over SSM.

    ```bash
    export AWSSH_PROFILE_FILTER="startstopssmsession"
    export AWSSH_USER="lemmy.kilmister"
    ```

1. Source the [`awssh-completion.bash`](tools/awssh-completion.bash) file in
   your `bash` environment:

   ```bash
   source tools/awssh-completion.bash
   ```

   If you skip this step, you won't get to enjoy any of that sweet, sweet
   tab completion that will make life a lot easier for you.  Don't say we
   didn't warn you.

## Nix ###

If you have [Nix](https://nixos.org/download.html) installed you can use
the [`flake.nix`](flake.nix) configuration file located at the root of the
project to build and run `awssh`:

```console
nix build
```

After the build has completed, the `awssh` executable can be found at:
`result/bin/awssh`

To run the program simply execute the binary from the project root:

```console
result/bin/awssh --help
```

### Start a SSM shell session without ssh ###

```console
awssh --no-ssh my-aws-startstopssmsession-profile i-01234567890abcdef
```

### Start a SSM shell session with ssh ###

```console
awssh my-aws-startstopssmsession-profile i-01234567890abcdef
```

Tab completion can be used to autocomplete the following items as you type
your `awssh` command:

- Shared credentials file (following `-c`, `--credentials=FILENAME`), by
  showing matching files in the `.aws` directory in your home directory
  (e.g. `~/.aws/`)
- AWS region (`-r`, `--region`)
- AWS profile (`<profile>`), provided your chosen (or default) credentials
  file contains at least one profile that matches the string specified by the
  `AWSSH_PROFILE_FILTER` environment variable
- AWS instance you want to open a session to (`<instance-id>`); note that
  if your instance is tagged with a name, you can start typing that name and
  when you tab complete, the name will be transformed into the instance ID
  (assuming you have typed enough of the name to identify a unique instance).

## Contributing ##

We welcome contributions!  Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) for
details.

### Special development pre-requisites ###

> [!Note]
> This project supports installation via a [Nix](https://nixos.org/)
> [`flake.nix`](https://nixos.wiki/wiki/Flakes) file, and as a result
> the `bump_version.sh` script requires that Nix be installed locally.

## License ##

This project is in the worldwide [public domain](LICENSE).

This project is in the public domain within the United States, and
copyright and related rights in the work worldwide are waived through
the [CC0 1.0 Universal public domain
dedication](https://creativecommons.org/publicdomain/zero/1.0/).

All contributions to this project will be released under the CC0
dedication. By submitting a pull request, you are agreeing to comply
with this waiver of copyright interest.
