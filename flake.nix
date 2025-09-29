{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = inputs@{ self, nixpkgs, uv2nix, ... }:
  let
    system = "x86_64-linux";

    name = "lantime-prometheus-exporter";

    pkgs = import nixpkgs { inherit system; };

    python = pkgs.python313;

    workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

    overlay = workspace.mkPyprojectOverlay {
      sourcePreference = "wheel";
    };

    baseSet = pkgs.callPackage inputs.pyproject-nix.build.packages {
      inherit python;
    };

    pythonSet = baseSet.overrideScope (
      pkgs.lib.composeManyExtensions [
        inputs.pyproject-build-systems.overlays.default
        overlay
      ]
    );

    venv = pythonSet.mkVirtualEnv "${name}-env" workspace.deps.default;
  in {
    packages.${system} = {
      venv = venv;
      default = venv;
    };

    apps.${system}.default.program = "${self.packages.${system}.default}/bin/hello";

    devShells.${system} = {
      default = pkgs.mkShell {
        inputsFrom = [ venv ];
        buildInputs = with pkgs; [
          just
          uv
          ruff
        ];
        shellHook = ''
          export "UV_PYTHON=${pkgs.python313}"
          user_shell=$(getent passwd $USER |awk -F: '{print $7}')
          exec $user_shell
        '';
      };
    };
  };
}
