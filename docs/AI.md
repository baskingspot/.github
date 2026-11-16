# How I use LLMs

I use LLMs heavily to build my baskingspot libraries, and I don't want to hide that. This page is about how _I_ use them. Other people maintain repos in this org too, and if they want to write up how they work, they can.

To me, an LLM is a tool, in the same way a good editor or an LSP is a tool. It makes me faster, and it's able to push the boundaries of what I understand and help bridge the gaps in topics I only know partway. It also lets me work on a lot of things in parallel, which is why these repos move as fast as they do. Hundreds of commits in a few weeks is not hand-typed, and I'm not going to pretend it is. All of this happens in [pi](https://pi.dev).

I do nearly all of the high level design myself: the APIs, how a library is meant to be used, how it fits into the projects that depend on it, and the guardrails around it. Frankly, LLMs aren't very good at designing software. They're good at the mechanical stuff, but they don't design well on their own, so this is where I put most of my effort.

I read a lot of the code, but not all of it. Anything performance sensitive I read closely. Beyond that there's a boundary of trust, and if we're implementing an RFC to spec and it passes the integration and conformance tests, it's likely fine.

[TLS](https://github.com/baskingspot/tls) and [QUIC](https://github.com/baskingspot/quic) are good examples of this. I know both at a decently deep level, enough to understand and direct the work, and I know my limits well enough to ask the right questions and make sure the guarantees are in place before any code exists. The tests are written to the spec, with the RFC section cited for each behavior, and the parsers are fuzzed. Where the ecosystem already has a source of truth, we run it ([TLS-Anvil](https://github.com/tls-attacker/TLS-Anvil) and [tlsfuzzer](https://github.com/tlsfuzzer/tlsfuzzer) for tls, [h2spec](https://github.com/summerwind/h2spec) for [http](https://github.com/baskingspot/http), the [Connect conformance suite](https://github.com/connectrpc/conformance) for [grpc](https://github.com/baskingspot/grpc), [toml-test](https://github.com/toml-lang/toml-test) for [toml](https://github.com/baskingspot/toml)). Then the code goes through many rounds of adversarial review across several frontier models, and I have them explain it back to me until I understand it.

There's also a lot of work I just don't care that much about, and I think that's where LLMs are the most useful. I don't really care how the release tooling works, or the CI plumbing, or the EC2 fleet we run benchmarks on. I say "I want it to work like this" and that's about it. The same goes for baskingspot.dev, since I have zero design taste and simply don't want to build a website.

The models also write pretty sloppy Zig by default. They tend to write it like C and avoid std entirely, and I spend a lot of time cleaning that up. What I kept repeating went into [skills](https://github.com/baskingspot/skills), so the next agent gets a bit closer the first time. Those are public, along with [llms.txt](https://baskingspot.dev/llms.txt), so if you write Zig with an agent, point it at them. I don't want to only be open about using these tools, I'd like to be helpful to other people using them too.

Anything a model writes for another model lives in `docs/slop/` in each repo. Everything outside of that (READMEs, guides, changelogs) is meant for a human to read, and none of it links into `docs/slop/`.

I know a lot of the Zig community thinks LLMs are bad, and as far as I can tell that comes from two places. The first is quality, and the view that anything an LLM writes is slop. That's the one I care about the most, and I'd like these libraries to show that it's possible to build high quality software with LLM assistance. The second is how the models are trained, and whether that's theft. I genuinely sit on the fence there, but I also don't think ignoring how powerful these tools are is the answer. What I do is use open-weight models by default, so most of what I run doesn't go to OpenAI or Anthropic.

Some people don't want LLM-assisted code in their dependencies. That's a reasonable call, and this page is here so you can make it.

Zig itself doesn't accept LLM-assisted contributions, and that's their policy to set. I think a lot of what I'm building is complementary to Zig, but I'm not trying to get any of it upstream.

If you contribute, LLM help is welcome. You have to understand the change well enough to explain it without the model, and you own it. If a model wrote a large part of it, say so in the PR.

[Matt Robenolt](https://github.com/mattrobenolt)
