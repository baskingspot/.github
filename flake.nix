{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    mattware = {
      url = "github:mattrobenolt/nixpkgs";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{
      flake-parts,
      nixpkgs,
      mattware,
      ...
    }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];

      perSystem =
        { system, ... }:
        let
          pkgs = import nixpkgs {
            inherit system;
            overlays = [ mattware.overlays.default ];
          };

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
          formatter = pkgs.nixfmt-tree;

          devShells.default = pkgs.mkShell {
            packages =
              with pkgs;
              [
                resvg
                svgo
                just
                oxfmt
                fd
                chafa
                actionlint
                zizmor
                pinact
                gh
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
