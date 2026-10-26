<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/baskingspot/.github/main/brand/assets/logo-dark.svg">
    <img src="https://raw.githubusercontent.com/baskingspot/.github/main/brand/assets/logo.svg" alt="baskingspot" height="48">
  </picture>
</h1>

Zig is cold-blooded. Come bask.

The libraries between `std` and your application: the parts that std stops short of and every project ends up rewriting. Each one is a Zig 0.16 package that does one job and documents it.

There are [agent skills](https://github.com/baskingspot/skills) too, for the same reason. A guide says what exists; a skill says how we write. Written cold, Zig drifts toward C, tests go through the built-in runner, and nothing reaches for a primitive that already exists. Install them with `npx skills add baskingspot/skills`, or in pi with `pi install git:github.com/baskingspot/skills`.

Guides, API references, and install lines are at [baskingspot.dev](https://baskingspot.dev). A library that has tagged a release installs from the tag; the others install from `main` until they have one.

I build these with LLM assistance and review nearly all of it myself. [How, in detail](https://github.com/baskingspot/.github/blob/main/docs/AI.md).
