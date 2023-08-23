{
    description = "Tool to simplify secure shell connections over AWS simple systems manager.";
  
    inputs = {
      nixpkgs.url = "github:NixOS/nixpkgs?ref=nixpkgs-unstable";
      utils.url = "github:numtide/flake-utils";
    };
    outputs = { self, nixpkgs, utils }: {
      devShell = self.defaultPackage;
      defaultPackage.x86_64-darwin =
        with import nixpkgs { system = "x86_64-darwin"; };
        let
          awssh = pkgs.python310Packages.buildPythonPackage rec {
            pname = "awssh";
            version = "1.1.0";
            doCheck = false;
            propagatedBuildInputs = with pkgs.python310Packages; [
              boto3
              docopt
              schema
              setuptools
              wheel
              ];
            src = (pkgs.fetchFromGitHub {
              owner = "cisagov";
              repo = "awssh";
              rev = "v1.1.0";
              sha256 = "sha256-4b2VBFUQye4wTvuagPwEImLwkUO4Dk5hvOYW+eg8OGA=";
          });};
        in
          pkgs.python310Packages.buildPythonPackage rec {
            pname = "awssh";
            version = "1.1.0";
            src = ./.;
            propagatedBuildInputs = with pkgs.python310Packages; [
              boto3
              docopt
              schema
              wheel
              setuptools
            ];
          };
    };
  }
  

