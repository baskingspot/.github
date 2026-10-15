# How these libraries are made

I use LLMs to write code, tests, and docs for the baskingspot libraries. I work in [pi](https://pi.dev), a coding agent, with models from several vendors, and I use subagents to research and review. I'm the maintainer, almost every commit is mine, and I'm responsible for what ships.

I review nearly everything myself. Where the subject is beyond what I know, I set up guardrails before the code exists. The tests come first and follow the spec, with the RFC section cited for each behavior. Then the code goes through many rounds of adversarial review by several frontier models, and I have them explain the code and their findings until I understand it.

The tests and the evidence behind them live in each repo, so you can check the work.

Each repo's `AGENTS.md` describes how the agents work in it, and the review agents live in `.pi/agents/`. Both are public.

Some people don't want LLM-assisted code in their dependencies. That's a reasonable call, and this page is here so you can make it.

If you contribute, LLM assistance is welcome. You have to understand the change well enough to explain it without the model, and you're responsible for it. If an LLM wrote a large part, say so in the PR.

Zig's own project doesn't accept LLM-assisted contributions. That's their policy, and nothing here is headed upstream.
