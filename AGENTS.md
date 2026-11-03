# nstack (~/Projects/nstack)

The source of Nate's agent stack: rules (`omp-rules.md`), skills, agents, commands and the `web` tool. `README.md` has the layout, and `install.py` installs it. This repo is public: run the personal-information check before every push (the first name Nate stays).

## Decisions

- A change to the ruleset is followed by a sweep of the whole ruleset for gaps. Guidance missing by omission is a defect even when nothing in it is wrong; a review that only hunts incorrect statements never sees a silent gap.
