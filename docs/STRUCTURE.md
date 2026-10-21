# Structure

How a baskingspot library's README and guide are laid out. [`VOICE.md`](VOICE.md) says how the sentences read. This file says what goes where, and in what order.

The rule: a reader who knows one library's README and guide can find the same thing in any other, in the same place, under the same heading.

## The tagline

One sentence. It says what the library is and what it covers. It ends with a period. Code and flags in it are in backticks.

The same sentence appears in five places. Change all five together.

- `README.md`, under the logo.
- The first sentence of `docs/content/_index.md`.
- The first lines of `src/root.zig`.
- `description` in `docs/config.toml`.
- The GitHub About text.

## The README

The README is the front door. It is short, and it links to the guide for everything else. If a section would add a heading that is not in the list below, the text belongs in the guide.

Sections appear in this order. Each `##` heading is spelled exactly as shown.

1. The logo `<h1>`, then the tagline.
2. The opening: one to three short paragraphs, no heading. Say why the library exists, what it is, and the one fact that sets it apart. Two things may also sit here:
   - one code example of at most 12 lines, when the call shape sells the library
   - one sentence on status when it changes an adopter's decision, such as "pin a commit"
3. `## What is in it`
4. `## Install`
5. `## Documentation`
6. `## Work on it`
7. `## License`
8. `## How it's made`, then the badge.

`## What is in it` mirrors the guide's opening list. It has one linked bullet for each chapter in that list, in the same order and in the chapter's own words. A bullet carries a symbol and a fact. The README may fold the last small chapters into one closing bullet. A library with one namespace per format uses a table of namespace, format, and support instead of bullets.

If the guide has a `# Limits` chapter, `## What is in it` ends with a `Not implemented:` list. It has one bullet for each limit that a reader would assume does not exist, each with the symbol or error that says so.

`## Install` has the `zig fetch` line, the `build.zig` snippet, and the import line when it helps. It names the std namespace that the module collides with and the alias to bind. Its last sentence says the library builds with Zig 0.16 only. The fetch line follows the install rule in `AGENTS.md`.

`## Documentation` is a bullet list in this order:

1. The guide.
2. The API reference.
3. `examples/`, when the repo has one.
4. Repo-specific documents, such as a security policy or a readiness file.

`## Work on it` says `nix develop` provides the toolchain and `just ci` runs what CI runs. It lists extra recipes only when a contributor needs them.

`## License` names the license, links `LICENSE`, links `THIRD_PARTY.md` when code is adapted, and says the logo files are not covered.

## The guide

The guide is one page, `docs/content/_index.md`. The reader finds a topic with Cmd+F. Split it only when one page stops being searchable.

The page has this shape:

1. Front matter with the title.
2. The tagline, as the first sentence.
3. The opening: the origin paragraph, the same one the README uses, and any further paragraph that the guide needs.
4. A list with one linked bullet for each chapter except `Getting started`. Each bullet uses the chapter's title and says in one sentence what it does, with the symbol that matters.
5. One sentence that links the API reference.
6. `# Getting started`, always the first chapter.
7. The subject chapters.
8. `# Limits`, when the reader would assume something exists and does not. It is the last chapter.

`# Getting started` has these sections:

1. `## Install`
2. `## Import it`
3. `## Name the bindings`, when a std namespace has the same name
4. `## Read the examples`

Add a section there when a first-time reader needs it, for example how to wire a test runner. Put the next step after it, not a second `Getting started`.

A guide that has performance claims has a `# Performance` chapter, placed before `# Limits`. It states the headline number, the measured loss, and a link to the evidence. A claim in a README or a guide opening links to it.

## Headings

- Sentence case. Capitalize the first word and proper names only.
- `#` is a chapter. `##` is a section. `###` is for parallel variants, such as the client loop and the server loop. Nothing goes deeper.
- A chapter title names the subject: `Strict parsing`, `Timekeeping`, `Streaming`.
- A section title is an imperative phrase when it is a task (`Parse an integer`, `Pick the loss policy`) and a noun phrase when it is a reference (`Event union`).
- No colons, no numbering, no question marks, no trailing punctuation.
- A heading's slug is its anchor. Renaming a heading breaks every link to it, including the README bullets, the integration READMEs, and the API docs. Search the repo for the old slug before you rename.
- A chapter holds at least two sections or a body of its own. A heading over one sentence does not earn its place.

## Doc comments

`//!` and `///` comments in `src/` state the contract. The guide says which piece to pick, and the comments say what a symbol does.

- A module opens with a `//!` brief: what it is and what it promises, in one or two sentences. The root module's first lines are the tagline.
- A public declaration gets a `///` comment when its name and type do not carry the contract. State invariants, failure modes, and who owns the memory.
- A comment explains why, not what. No walkthroughs, no review or PR references, no status words.
- Doc comments keep the repo voice and are exempt from the guide's STE rules. A precise long sentence beats a vague short one.
- A claim about another symbol needs its own check. A comment written for one type and pasted onto its neighbor is the commonest wrong doc.

## Other documents

Anything the guide does not hold lives beside it, linked from `## Documentation`:

- `CHANGELOG.md` for released changes.
- `SECURITY.md` for the reporting policy.
- `THIRD_PARTY.md` for adapted code and its terms.
- `docs/research/` for evidence, such as benchmark captures and the threat model.

Each README that sits in `src/` or `examples/` follows the same voice. It does not need the full shape above.

## Checks

`just audit` checks the README and the guide of every repo that has a guide:

- The README's `##` headings are the list above, in order, and none repeats.
- The guide's opening list has one bullet for each `#` chapter except `Getting started`, in chapter order.
- Each guide link in the README's `## What is in it` points at a real heading, and the links follow the guide's chapter order. `Limits` needs no bullet, because the `Not implemented:` list carries it.

Whether each bullet says what its chapter says is a judgment, and the `docs-librarian` agent reads for it.
