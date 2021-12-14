# awssh ☁️🔒🐚 #

[![GitHub Build Status](https://github.com/cisagov/awssh/workflows/build/badge.svg)](https://github.com/cisagov/awssh/actions)
[![CodeQL](https://github.com/cisagov/awssh/workflows/CodeQL/badge.svg)](https://github.com/cisagov/awssh/actions/workflows/codeql-analysis.yml)
[![Coverage Status](https://coveralls.io/repos/github/cisagov/awssh/badge.svg?branch=develop)](https://coveralls.io/github/cisagov/awssh?branch=develop)

This project implements a tool that simplifies secure shell connections over AWS
simple systems manager.

## Usage ##

<!--TODO: Correctly document -->

1. Install the `awssh` command line utility.

1. Define environment variables:

    ```bash
    export AWSSH_PROFILE_FILTER="startstopssmsession"
    export AWSSH_USER="lemmy.kilmister"
    ```

1. Source the [`awssh-completion.bash`](tools/awssh-completion.bash) file in
   your `bash` environment.

1. Profit!

## Contributing ##

We welcome contributions!  Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) for
details.

## License ##

This project is in the worldwide [public domain](LICENSE).

This project is in the public domain within the United States, and
copyright and related rights in the work worldwide are waived through
the [CC0 1.0 Universal public domain
dedication](https://creativecommons.org/publicdomain/zero/1.0/).

All contributions to this project will be released under the CC0
dedication. By submitting a pull request, you are agreeing to comply
with this waiver of copyright interest.
