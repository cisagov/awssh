{
  description =
    "Tool to simplify secure shell connections over AWS Systems Manager (SSM).";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-23.05";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        awssh = pkgs.python310Packages.buildPythonPackage rec {
          name = "awssh";
          version = "1.1.1";
          doCheck = false;
          propagatedBuildInputs = with pkgs.python310Packages; [
            boto3
            docopt
            schema
            setuptools
            wheel
          ];
          src = pkgs.fetchFromGitHub {
            owner = "cisagov";
            repo = "awssh";
            rev = "v${version}";
            hash = "sha256-4b2VBFUQye4wTvuagPwEImLwkUO4Dk5hvOYW+eg8OGA=";
          };
        };
      in
      {
        packages.default = pkgs.python310Packages.buildPythonPackage rec {
          name = "awssh";
          version = "1.1.1";
          src = ./.;
          propagatedBuildInputs = with pkgs.python310Packages; [
            boto3
            docopt
            schema
            setuptools
            wheel
          ];
        };
      });
}
