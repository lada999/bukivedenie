{
  description = "bukivedenie development shell";

  outputs = { self }: let
    pkgs = import <nixpkgs> { };
    shell = pkgs.mkShell {
      packages = with pkgs; [
        bashInteractive
        curl
        git
        gnumake
        chromium
        nodejs_22
        python3
        python3Packages.pytest
      ];

      shellHook = ''
        export CHROME_PATH=${pkgs.chromium}/bin/chromium
        export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
        echo "Entered bukivedenie dev shell. Use: make frontend-install, make dev, make ui-smoke, pytest"
      '';
    };
  in {
    devShells.${pkgs.stdenv.hostPlatform.system}.default = shell;
  };
}
