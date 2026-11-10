# nstack (~/Projects/nstack)

The source of Nate's agent stack: rules (`omp-rules.md`), skills, agents, commands and the `web` tool. `README.md` has the layout, and `install.py` installs it.

This repo is public. Before every push, run the personal-information check on what is about to be published:

    git log origin/master..HEAD --format='%an <%ae>%n%B'; git diff origin/master..HEAD

Read that output for anything that identifies Nate or anyone else beyond his first name and his public GitHub handle: an email address, phone number, street address or employer; another person's name; a tailnet hostname or private IP address; an account name; a key, token or password; the content of a private message or record; a private fact about him or his machine. This command prints the usual shapes, and printing nothing means only that those shapes are absent:

    { git log origin/master..HEAD --format='%ae%n%B'; git diff origin/master..HEAD | grep '^+' | sed 's/^+//'; } | grep -nE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|[a-z0-9-]+\.ts\.net|(^|[^0-9.])(10|192\.168|100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7]))\.[0-9]{1,3}\.[0-9]{1,3}|\(?[0-9]{3}\)?[-. ][0-9]{3}[-. ][0-9]{4}|/Users/[A-Za-z]'

A match is removed or, when it is public on purpose (the commit author's GitHub noreply address, a credited author's address in a vendored license), named in the report. A finding in a commit not yet pushed is fixed by rewriting that commit before the push, never by a later commit, because the pushed history is public. Push to origin after each committed change without asking.

## Changing the ruleset

- Each rule lives in one file: the floor (`omp-rules.md`) holds only what every agent needs on every turn, `skills/nstack` holds the method, and a specialist skill holds only its specialist job. Other files point to a rule by name (`skill://nstack` › Design) instead of restating it. Credits go in the README; a skill keeps only the provenance and evidence that explain one of its rules.
- A rule goes in against a failure the session logs show and comes out when it stops earning its place. The evidence is a row or a quoted message from `python3 audit/scripts/session_audit.py` (which writes to `local/audit/runs/`), or Nate's own dated words; the commit body cites it. An outside idea (a post, a repo, a paper) is a source of fixes for those failures only. It merges into the section it belongs to, in that section's voice, and replaces what it supersedes instead of sitting beside it.
- A change is followed by one sweep of the whole ruleset for gaps it leaves and for duplicates or contradictions it creates. Guidance missing by omission is a defect even when nothing in it is wrong.
