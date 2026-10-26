# Contributing to YTMSplitter

Thanks for your interest in improving YTMSplitter. Bug reports, feature ideas
and pull requests are all welcome.

## Development setup

```bash
git clone https://github.com/figurophobia/YTMSplitter.git
cd YTMSplitter

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev,browsers]"
```

Run the test suite and the linter before opening a pull request:

```bash
pytest
ruff check .
```

Use `ruff format .` if you want the formatter to normalise your changes.

## Project layout

```text
ytmsplitter/
  cli.py       argparse commands and terminal output
  api.py       thin ytmusicapi wrapper and JSON helpers
  ai.py        LLM prompt, batching and bucket grouping
  labels.py    export/import batches for external assistants
  auth.py      browser cookies and request-header authentication
  config.py    paths, tags, buckets and playlist names
tests/         network-free unit tests
prompts/       copy of the classification prompt
assets/        logo and social preview
```

## Guidelines

- Keep the code network-free in `tests/`; mock or isolate external calls.
- Prefer small, focused changes with a clear commit message.
- Keep user-facing output and documentation in English.
- Do not commit `auth.json`, request headers, `data/` or any personal library
  export. They are ignored by default; keep it that way.
- If you change playlist names or AI buckets, add a migration path for files
  created by previous versions (see `LEGACY_AI_BUCKETS`).
- New commands should include an entry in `README.md` and a `--help` example.

## Reporting bugs

Please include:

- the output of `ytmsplitter --version` and `ytmsplitter doctor`;
- your OS, Python version and browser;
- the command you ran;
- the error output, with cookies and tokens removed.

## Security

Do not open a public issue for a vulnerability. See [SECURITY.md](SECURITY.md).
