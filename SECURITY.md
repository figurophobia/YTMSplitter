# Security policy

## Supported versions

Security fixes are applied to the latest release on the `main` branch.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for a security problem.

Email **dasamiarea@gmail.com** with:

- a description of the issue and its impact;
- steps to reproduce it;
- the affected version;
- any suggested fix, if you have one.

You will get an acknowledgement as soon as possible. Please allow time for a
fix and a coordinated release before publishing details.

## Credentials and personal data

YTMSplitter stores the YouTube session in `data/auth.json` with permissions
`600`. That file, browser request headers and everything inside `data/` are
ignored by Git. Never attach them to an issue or a pull request.

The tool talks to YouTube Music through [`ytmusicapi`](https://github.com/sigma67/ytmusicapi)
and to an LLM endpoint only when you configure one. Review the privacy policy of
your chosen model provider before sending song metadata to it.
