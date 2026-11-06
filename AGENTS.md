# nstack (~/Projects/nstack)

The source of Nate's agent stack: rules (`omp-rules.md`), skills, agents, commands and the `web` tool. `README.md` has the layout, and `install.py` installs it. This repo is public: run the personal-information check on the pushed diff and commit messages before every push (the first name Nate stays). Push to origin after each committed change without asking.

## Changing the ruleset

- Each rule lives in one file: the floor (`omp-rules.md`) holds only what every agent needs on every turn, `skills/nstack` holds the method, and a specialist skill holds only its specialist job. Other files point to a rule by name (`skill://nstack` › Design) instead of restating it. Credits go in the README; a skill keeps only the provenance and evidence that explain one of its rules.
- An outside idea (a post, a repo, a paper) goes in only where Nate's agents fail without it on his work. It merges into the section it belongs to, in that section's voice, and replaces what it supersedes instead of sitting beside it.
- A change is followed by one sweep of the whole ruleset for gaps it leaves and for duplicates or contradictions it creates. Guidance missing by omission is a defect even when nothing in it is wrong.
