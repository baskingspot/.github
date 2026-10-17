# Voice

Accepted 2026-10-15. Matt: "I think this is good!" Two choices in it are
my defaults, not his answers: contractions are fine in narrative text, and
the STE rules apply only to procedure and reference (see Registers).

How baskingspot writes: READMEs, guides, API docs, the org profile, the
site, issue and PR text. stdx's `docs/VOICE.md` stays in force for stdx
until it shrinks to its own mechanics.

Slack and chat are out of scope. The `write-like-matt` skill covers Slack.

This guide serves the reader. It is not a way to hide how the work is made.
baskingspot says plainly that LLMs help write it, in `AI.md`, and no text may
misstate that.

## The reader

A Zig programmer, tired, partway through something else. They are
deciding whether to depend on a library, or they are debugging at the end
of a long day and want the one edge that bites. They don't read for
pleasure. They notice padding within a sentence, and once they notice,
they stop trusting the rest.

## The voice

Write the way a good colleague answers a question at their desk. Give the
answer first, the reason once, and stop. Every sentence carries something
the reader can use: a symbol, a number, an error name, a command, a
constraint, a decision. If a sentence could sit unchanged in another
project's docs, it says nothing here.

Have opinions. "Use `String` for `[]const u8` keys, because `autoHash`
rejects slices" is a recommendation. "Several options are available
depending on your needs" is a shrug.

Humor is dry and rare, and it arrives inside a real sentence. zig-benchmark's
"without each project growing its own half-haunted benchmark runner" works
because it also says what the library is for. A joke that carries no
information is decoration. The lizard lives on the org's front page, not in
the API docs.

## What makes prose read as machine-written

Words are the weakest signal. Shape and emptiness are the strongest, and
they survive any word ban. The mechanical audit in this repo's toolchain
scored a PR body that Matt called slop at 0 out of 100. It sees vocabulary
and can't see cadence.

### Emptiness

Wikipedia's "Signs of AI writing" page describes the core failure as
regression to the mean. The model drops the specific,
unusual fact and substitutes a generic, positive claim that fits any
subject. "The inventor of the first train-coupling device" becomes "a
revolutionary titan of industry." The subject gets less specific and more
inflated at once.

The test for every sentence: swap the project name for another project's.
If it still reads true, cut it or replace it with the fact only this
project has.

### Inflated significance

Claims about importance in place of facts. Watch for: _pivotal_, _crucial_,
_vital_, _key role_, _testament_, _stands as_, _underscores_, _highlights_,
_reflects broader_, _evolving landscape_, _rich_, _vibrant_, _commitment
to_. A library isn't "a pivotal part of the Zig ecosystem." It parses
integers and rejects the ones std accepts by accident.

### Tacked-on analysis

A sentence ends with a participle phrase that comments on the sentence:
"...highlighting its importance", "...ensuring seamless integration",
"...contributing to a more robust ecosystem." Delete the phrase. If it was
a real consequence, state it as its own sentence with a number.

### The contrast pose

"Not X, but Y." "It isn't just a parser, it's a philosophy." "Y rather than
X." One in a document is rhetoric. Several is a fingerprint. State Y. If the
reader holds a wrong belief about X, name the belief once and correct it
with a fact.

### Three of everything

Triplets for rhythm, with a padded third item. "Fast, safe, and ergonomic."
Use the number of items that exist. Two is fine. Five is fine. Don't build a
list because a sentence felt short.

### Structure that exists because a template expects it

- A heading over one sentence.
- A bold lead-in on every bullet, all the same grammatical shape.
- A table with two rows.
- A closing paragraph that restates the section.
- A "Challenges and future directions" section on a library with a bug
  tracker. The tracker is where challenges live.
- A summary of what the doc just said.

If a section only exists to have a section there, remove it.

### Hedging stacks and chatbot residue

"It's worth noting that, generally speaking, in most cases..." Pick the
condition and state it. If the code is deterministic, don't say "typically."

Also out: offers ("let me know if you'd like..."), sycophancy, and any
sentence that talks to the reader about the document instead of the thing.

### Status as prose

"Currently", "now", "recently", "not yet wired up." Readiness belongs in an
issue. stdx already bans this in mechanism docs. In product copy it reads as
a progress report nobody asked for.

### Labels the reader never saw

Milestone codes, decision numbers, internal acronyms, `#123` with no
`owner/repo`. Name the thing. Write cross-repo references in full.

### Words

None of these is a crime alone. A cluster is a tell. Most of the list comes
from Kobak et al. (Science Advances, 2025), who counted words that jumped in
15 million PubMed abstracts after ChatGPT shipped, and from Wikipedia's
"Signs of AI writing" page. _Leverage_, _utilize_, _robust_, _seamless_, and
_delve_ are already banned in Matt's agent instructions. _Empower_,
_elevate_, _journey_, and _cutting-edge_ are marketing filler I added. They
are my additions, not measured ones.

- Verbs: _delve, underscore, showcase, highlight, foster, enhance, leverage,
  utilize, unveil, navigate, streamline, empower, unlock, elevate_
- Adjectives: _pivotal, crucial, robust, seamless, comprehensive, intricate,
  meticulous, transformative, unparalleled, vibrant, rich, cutting-edge_
- Nouns: _landscape, tapestry, realm, journey, testament, insights_
- Connectives: _additionally, furthermore, moreover, notably, particularly,
  ultimately, in order to_

Replace by saying the concrete thing. Don't swap to a synonym. A "robust"
parser that becomes a "reliable" parser has changed nothing.

### Phrases

Some tells are phrases, not words. _Reserved seat_ and _empty seat_ are
the one that spread through the compress docs, as a stock metaphor for
"this isn't built yet". Say what is missing: "other qualities return
`error.Unimplemented`." The audit warns on these in a README.

### Punctuation

Don't use em dashes in new org prose. Use a period, a comma, or a colon.
Matt's `write-like-matt` profile, built from about 240 of his own Slack
messages, finds none, and calls the dash the most reliable machine
fingerprint in his corpus. Outside this corpus the signal is contested:
some models overuse the dash and some barely touch it, and human writers
use it too. The tell is function more than presence, a dash that bolts an
explanatory aside onto the end of a sentence.

This is a rule for what you write, not a reason to rewrite. stdx's module
docs use dashes in sentences that carry real content. Leave them. Don't
flatten a precise sentence to remove one.

## Registers

One reader, a few surfaces. The surface sets how formal the sentences are.
It doesn't change the rules above.

**Reference and procedure** (API docs, install steps, runbooks, error
messages). Short active sentences. One instruction per sentence. Conditions
before commands: "If the test fails, read the log." Pick `must` or delete the
word. Avoid `should`, `may`, `might`. This is where ASD-STE100 earns its
keep, because a reader can't ask what you meant.

**Narrative** (README opening, profile, landing page, PR description, issue).
Plain speech. Contractions are fine. First person is fine when a person did
the thing. Lead with what it is and why it exists.

**Org surfaces** (bio, profile README, front page). The warm, dry register
from the brand brief. The tagline lives here. It's one line, and it doesn't
repeat.

The org has two lines, always in this order. The tagline is "Zig is
cold-blooded. Come bask." The descriptor is "Libraries between std and your
application." The tagline goes first so that no surface opens with "Zig"
twice. They appear in the org bio, the front page and its description and
social meta tags, and the profile README's opening. Change them in all four
at once.

**Open question for Matt:** does the no-contractions rule from stdx's guide
become org policy, or does it stay limited to procedure and reference? The
evidence points two ways. In September, stiff no-contraction prose in a PR
body read as machine-written to Matt. In October he faulted another PR body
for ignoring the github skill, which specifies STE. My recommendation: STE
for procedure and reference, plain speech for narrative.

## Before it ships

1. Every claim carries a handle: a symbol, a number, an error name, a
   command. Cut the ones that can't.
2. Swap the project name. If the sentence survives, it's filler.
3. Delete the sentence. Would the reader miss it?
4. Each fact appears once. Read for restatement across the opener, the
   intro, and the section that follows.
5. Every claim is true on the pinned toolchain. Read the std source before
   writing what std lacks. Run it before writing what you only read.
6. Run `prose_audit` for the vocabulary it can see. A low score proves
   nothing about cadence.
7. Read it once as the tired reader. Then stop editing.

Don't fix a tell by swapping in another cliché, and don't damage a clear
sentence because it contains one em dash. Delete before you rewrite.

## Examples

Slop, built from the pattern lists above:

> stdx is a comprehensive toolkit that seamlessly extends Zig's standard
> library, empowering developers to build robust, high-performance
> applications with confidence.

Fixed:

> stdx has the containers and parsers std lacks.

Slop:

> ztls isn't just another TLS library. It's a fresh take on how secure
> communication should work, offering performance, flexibility, and control.

Fixed, which is nearly how ztls's README already opens:

> ztls is a TLS 1.3 library that does no I/O. You feed it the bytes you read
> off the wire, and it hands you the bytes to write. Your socket, your event
> loop, your buffers.

What the second one gets right: it says what the thing does and names the
boundary. The last sentence is a list of three, but they are three actual
things.

## Where this goes

On acceptance:

- This file becomes the org-level voice guide, living in
  `baskingspot/.github` under `docs/`.
- stdx's `docs/VOICE.md` keeps the stdx mechanics (five-place tagline,
  example rules, tool recipes) and links here for the rest.
- An agent skill points at this file and carries the "Before it ships"
  list, so any agent writing for the org reads it first.
- A deterministic word-list check, a small `just` recipe over the READMEs and
  guides, warns on the "Words" list. It warns and does not fail, since one
  hit isn't a tell.
