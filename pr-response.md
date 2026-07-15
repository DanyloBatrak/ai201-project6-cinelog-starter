# PR Response Doc — CineLog Watchlist Feature

## AI Usage

I used AI throughout this project for several distinct purposes:

- Codebase orientation and pattern-matching: understanding how `add_to_collection()` handled deduplication before writing my own version for `add_to_watchlist()`, without having AI write the dedup code itself.
- Debugging: working through a series of real errors during the rebase (an untracked `.gitignore` blocking checkout, a `.gitignore` merge conflict, a missing `WatchlistEntry` model after rebasing onto a `main` that had migrated `Film.id` from integer to UUID, and a stuck interactive rebase session) — AI helped me interpret each error message and decide the right git commands, but I ran every command and verified every result myself.
- Commit message format verification: before finalizing my interactive rebase, I gave AI my `git log --oneline` output and asked whether the messages followed conventional commit format and whether any commit bundled multiple logical changes. It flagged that one commit's message ("added watchlist model and endpoint fixed a bug more changes") suggested a bundled change. After inspecting the actual diff myself (`git diff HEAD~1 --stat`), I determined the commit's content was in fact a single cohesive feature addition despite the messy wording, so I reworded it rather than splitting it — a case where I verified the AI's flag against the real diff instead of accepting it at face value.
- Grammar and clarity editing: for my written responses in this file (Comments 1–6), AI helped catch typos, tense inconsistencies, and unclear phrasing as I drafted them.

## Comment 1 — Rename

**What I did:**

Renamed `save_to_watchlist()` to `add_to_watchlist()` in `services/watchlist_service.py` and update all call sites

**How I verified:**

- Ran a project-wide search for the old name to confirm no remaining references :

```bash
  grep -rn "save_to_watchlist" --include="*.py" .
```

- First run turned up two remaining references in `routes/watchlist/watchlist.py` (an import and a call site) that I'd missed — updated both.

- Confirmed `routes/watchlist/watchlist.py` calls `add_to_watchlist(...)`.

- Ran `pytest tests/ -v` - all tests passed

## Comment 2 — Deduplication

**What I did:**

- Added deduplication logic to `add_to_watchlist()` in `services/watchlist_service.py`
- Followed the same pattern used in `add_to_collection()`: query for an existing `WatchlistEntry` by `user_id` and `film_id` before creating the new entry.
- Raised a new `AlreadyInWatchlistError` if a duplicate is found

**How I verified:**

- Confirmed the import resolve cleanly:

```bash
  python -c "from services.watchlist_service import add_to_watchlist, AlreadyInWatchlistError; print('OK')"
```

- Confirmed collection_service.py is back to its original state

```bash
  $ git diff services/collection_service.py
```

- Output was empty — no leftover changes.

- Ran `pytest tests/ -v` - all tests passed

## Comment 3 — Missing test

**What I did:**

- Created a new file tests/test_watchlist.py.
- Moved app and sample_user definitions to tests/conftest.py and fixed missing "import pytest"
- Read `tests/test_collection.py`, found `test_add_to_collection_nonexistent_film_raises` and wrote the equivalent test for `add_to_watchlist()` following the same fixture and assertion structure

**How I verified:**

- Confirmed test_watchlist.py resolves cleanly:

```bash
  pytest tests/test_watchlist.py -v
```

- Ran `pytest tests/ -v` - all tests passed

## Comment 4 — Default visibility

**My position:**

`public=True` as the default is the wrong call — it should default to `False` (private).

**Reasoning:**

A watchlist is fundamentally different from a collection. A collection `CollectionEntry` represents films that user already watched and choosing to log. Through this action, user would made a deliberate, restrospective statement about their taste. A watchlist, by contrast, is aspirational and often impulsive: someone adds a film because a trailer looked interesting, a friend recommended it, or they want to remember to check it out later. It's closer to a personal to-do list than a selected public statement.

Defaulting that to public means that majority of user - who never open a settings screen and never think about visibility at all - would end up broadcasting their watchlist by default, without ever making an active choice to do so. Based on how `add_to_watchlist()` works through testing, this default would silently inherit nearly every entry in database. It would be a lot of risk riding on a default nobody chose.

There's also a difference in what's embarrassing to have public. A watched-and-rated collection is something people already expect to be somewhat public. For example, a watchlist can include things people are curious about but wouldn't want tied to their public profile such as a guilty-pleasure movie, something for research, something a friend recommended ironically. So defaulting to private should protect the "more" private category, not the more public-facing one.

**Tradeoff acknowledged:**

Defaulting to private does cost the product something real: social engagement. Part of what makes a film-tracking app engaging is seeing what your friends want to watch which leads to conversation, recommendations, and repeat engagement. If most of these watchlists would be private by default, then this feature effectively goes dark for the majority of users who never dig into settings to turn visibility on, and the "social" half of the product may end up feeling emptier than intended. But if the team's growth strategy leans heavily on watchlists being a "visible", shareable feature (the way Letterboxd's activity feed drives engagement), defaulting to public is a defensible product bet — it needs to be a deliberate one, made with eyes open about the privacy cost, not an accidental side effect of whichever value someone happened to type first.

## Comment 5 — Sort order

**My position:**

Keep the watchlist sorted alphabetically by title rather sort fims by data-added

**Reasoning:**

A collection is a log (an ordered record of activity over time), so recency is the natural option to browse it by ("what have I watched lately"). Watchlist is different, however: it's a reference list you return to repeatedly to decide "what should I watch tonight," often weeks or months after adding items to it. By that point, when something was added is almost useless information, since a person wouldn't remember or care that they added a film three weeks before another one. What people would remember is that film's name, so they can scan for it. Alphabetical order supports that lookup use case directly, while date-added order doesn't tell the user anything meaningful about the list's contents at a glance.

There's also a practical bunching problem with date-added ordering on a watchlist specifically because watchlists tend to grow in bursts (e.g.,someone adds twelve films after a conversation with a friend), and a strict date-added sort would cluster all ten together at the top, pushing everything older down — even if those older entries are exactly what the user is most likely to watch next. So alphabetical order stays stable and predictable regardless of when entries were added, which matters more for a list people revisit and scan repeatedly than for a list people mostly just add to rather than depend on date-added sorting.

**Engagement with reviewer's point:**

The maintainer's likely argument is that the two features (collection and watchlist) should be consistent because if collection entries would ordered by recency, then watchlist entries should be too, so the codebase has one predictable convention for "list order" rather than two.

That's a fair judgment, and I'm not rejecting it — consistency has genuine value for anyone maintaining both services later. However, I don't think consistency alone should override what actually serves the watchlist's specific use case. A collection is a historical log, so recency is the obviously "correct" axis to sort it by and there's no real tension between "consistent" and "useful" there. A watchlist, on the other hand, is different enough in purpose that blindly inheriting the same sort key risks optimizing for uniformity over usability. So while I take the maintainer's consistency argument seriously, I'm siding with alphabetical anyway — not because it ignores their point, but because on reflection, the lookup behavior it supports ("find this specific film I remember by name") turns out to matter more for how people actually use a watchlist than matching `get_collection()`'s sort key does

## Comment 6 — Rebase

**What conflicted:**

Running `git rebase origin/main` initially failed with:

error: The following untracked working tree files would be overwritten by checkout:
.gitignore

This happened because I had a local, untracked `.gitignore` that hadn't been committed, and `origin/main` also had its own `.gitignore` which means that Git refused to switch branches to avoid silently overwriting my uncommitted file.

**How I resolved it:**

I opened `.gitignore` and found the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)

Both sides had unique entries (mine added `.env`, origin/main added `__pycache__/`), so I merged both sets of lines together and removed the conflict markers, rather than discarding either side.

I added .gitignore using command:

```bash
  git add .gitignore
```

Rebased .gitignore:

```bash
  git rebase --continue
```

**How I verified no conflict remains:**

- Ran `git status` after `git rebase --continue` completed — output showed a clean working tree with no "rebase in progress" or "you have unmerged paths" message, confirming the rebase finished successfully.
- Opened `.gitignore` again and confirmed no leftover conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) remained in the file.
- Ran the full test suite to make sure nothing from `origin/main` broke my existing changes:

```bash
  pytest tests/ -v
```

- (in models.py) Resolve the UUID conflict by updating your watchlist code to use UUIDs where it still references integer IDs.

Ran again:

```bash
  pytest tests/ -v
```

All tests passed.

- Ran `git log --oneline --graph` to confirm the rebase produced a linear history for my own commits (rename, dedup, test, and the `WatchlistEntry` restoration), sitting cleanly on top of `origin/main`. The only merge commit visible (`bbe206c`) is a pre-existing merge already part of `origin/main`'s history from before my branch's commits, not one introduced by my rebase which confirms tht I didn't accidentally create a merge commit myself.

## PR Description

Adds a **watchlist** feature to CineLog, letting users save films they want to watch later (as distinct from `CollectionEntry`, which tracks films they've already watched). This includes:

- `WatchlistEntry` model (`models.py`)
- `add_to_watchlist()` and `get_watchlist()` service functions (`services/watchlist_service.py`)
- A `/watchlist` route (`routes/watchlist/watchlist.py`), registered as a blueprint in `app.py`
- Deduplication logic preventing the same film from being added twice to a user's watchlist
- A test covering the nonexistent-film error path (`tests/test_watchlist.py`)

## Design decisions

1. Default visibility (`public=True` vs `False`):
   I chose to keep/argue for `public=False` as the default (as I said in Comment 4) — a watchlist is aspirational and often impulsive, closer to a personal to-do list than a curated public statement, so defaulting to private avoids exposing entries the user never actively chose to share. Full reasoning and the acknowledged tradeoff (reduced social discovery) is documented in `pr-response.md`.

2. Sort order (alphabetical vs date-added):
   `get_watchlist()` sorts alphabetically by film title, rather than by `date_added` (which is how `get_collection()` sorts). A watchlist is a reference list people return to and scan by name, often long after adding an item, so title-based lookup serves that use case better than recency. Full reasoning, engagement with the counterargument for date-added, and the acknowledged tradeoff are documented in `pr-response.md`, Comment 5.

## How to manually test

1. Installed dependencies and start the app locally
2. Create a user and a film via the existing `/collection` or a direct DB insert, since there's no dedicated user/film-creation endpoint in this PR
3. Add to watchlist:
   POST /watchlist
   { "user_id": "<uuid>", "film_id": "<uuid>" }
   Expected a 2xx response with the new watchlist entry.
4. Duplicate check: repeat step 3 with the same `user_id`/`film_id`. Expected an error response (mapped from `AlreadyInWatchlistError`), not a duplicate row.
5. Nonexistent film check: repeat step 3 with a `film_id` that doesn't exist. Expect an error response (mapped from `FilmNotFoundError`).
6. List watchlist:
   GET /watchlist?user_id=<uuid>
   Expected films returned sorted alphabetically by title.
7. Run the automated test suite:

```bash
   pytest tests/ -v
```

All tests, including `tests/test_watchlist.py`, should pass
