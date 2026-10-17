{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-parts.follows = "baskingspot/flake-parts";
    baskingspot = {
      url = "github:baskingspot/nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [ inputs.baskingspot.flakeModules.base ];

      perSystem =
        { pkgs, config, ... }:
        let
          # Fonts for the brand SVGs. Text is laid out from these so every
          # machine renders the same glyphs. The final assets outline the text.
          fonts = pkgs.symlinkJoin {
            name = "brand-fonts";
            paths = with pkgs; [
              fraunces
              inter
              hanken-grotesk
              commit-mono
              recursive
            ];
          };
        in
        {
          devShells.default = pkgs.mkShell {
            inputsFrom = [ config.devShells.base ];

            packages =
              with pkgs;
              [
                chafa
                oxlint
                resvg
                ruff
                svgo
                ty
              ]
              ++ [
                (python3.withPackages (ps: [
                  ps.fonttools
                  ps.skia-pathops
                ]))
              ];

            env = {
              BRAND_FONT_DIR = "${fonts}/share/fonts";
              # Tells the justfile it is already here, so it does not nest.
              BASKINGSPOT_BRAND_SHELL = "1";
            };
          };
        };
    };
}
