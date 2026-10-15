<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="brand/assets/logo-dark.svg">
    <img src="brand/assets/logo.svg" alt="baskingspot" height="48">
  </picture>
</h1>

The org-level repo for [baskingspot](https://github.com/baskingspot). GitHub reads two things from it. `profile/README.md` renders on the org's overview page. Files at the root and in `ISSUE_TEMPLATE/` become defaults for every org repo that has none of its own.

The rest is where the org keeps what it shares:

- `docs/VOICE.md` is how baskingspot writes. Read it before you write anything public.
- `docs/AI.md` says how LLMs are used and how that work is checked.
- `brand/` holds the logo system, the org's brand files, and the generator that makes a new library's logos.
- `templates/library/` is the README every library starts from.

## Working here

`nix develop` provides every tool, and `direnv allow` loads it on entry. `just` lists the recipes. `just ci` runs what CI runs.
