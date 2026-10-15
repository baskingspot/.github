<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/static/logo-dark.svg">
    <img src="docs/static/logo.svg" alt="{{name}}" height="48">
  </picture>
</h1>

{{tagline}}

TODO: one paragraph. Say why this exists, what it is, and the one fact that sets it apart. Name real symbols and say what is true: no dependencies, no allocator, whatever applies. Delete this line.

## What is in it

TODO: one bullet per chapter of the guide, in that chapter's own words. Each bullet carries a symbol and a fact. Delete this line.

- [Chapter title](https://baskingspot.dev/{{name}}/#chapter-title): what it does in one sentence, with the symbol that matters.

## Install

```sh
zig fetch --save git+https://github.com/baskingspot/{{name}}
```

Add the module to your build:

```zig
const {{ident}} = b.dependency("{{name}}", .{ .target = target, .optimize = optimize });
exe.root_module.addImport("{{name}}", {{ident}}.module("{{name}}"));
```

{{name}} builds with Zig 0.16 only.

## Documentation

- The [guide](https://baskingspot.dev/{{name}}/) says which piece to use for a task, with examples that compile.
- The [API reference](https://baskingspot.dev/{{name}}/api/) documents every symbol.

## Work on it

```sh
just ci
```

`nix develop` provides the toolchain. `just` lists the recipes, and `just ci` runs what CI runs.

## License

MIT. See `LICENSE`. TODO: if any code is adapted from elsewhere, list it in `THIRD_PARTY.md` and link that file here. Otherwise delete this sentence.

## How it's made

Built with LLM assistance. [How, in detail](https://github.com/baskingspot/.github/blob/main/docs/AI.md).

<a href="https://github.com/baskingspot"><img src="https://raw.githubusercontent.com/baskingspot/.github/main/brand/assets/badge.svg" alt="baskingspot" height="24"></a>
