with import <nixpkgs> {};

stdenv.mkDerivation {
  name = "d3mlm-ta2-env";
  buildInputs = [
    python27Full
    python27Packages.virtualenv
    python27Packages.pip

    R
    rPackages.devtools
    rPackages.withr
  ];
  src = null;
  shellHook = ''
    # Allow the use of wheels.
    SOURCE_DATE_EPOCH=$(date +%s)

    # Add the virtualenv path to the shell path.
    mkdir -p venv
    export PATH=$PWD/venv/bin:$PATH

    # Add the local R libraries to the R library path.
    mkdir -p rlib
    export R_LIBS_SITE=$PWD/rlib:$R_LIBS_SITE
  '';
}
