# LinkedIn Auto-Poster

Post to your own LinkedIn profile on a schedule, automatically, with generated
graphic images — using LinkedIn's official API, running entirely on GitHub's
free infrastructure. No third-party service, no monthly subscription, no one
but you ever holds your LinkedIn access token.

**What this does:**
- Runs on a schedule (default: Monday & Thursday) with zero servers of your own
- Auto-generates a branded quote-card graphic for each post
- Auto-publishes a privacy policy page for you (needed for the LinkedIn app form)
- Offers to draft your posts with Claude/ChatGPT (optionally from your LinkedIn
  profile PDF) and push them for you, right from the setup wizard
- Warns you (via a GitHub issue → email) before your access token expires
- 100% yours — your own repo, your own token, your own data

**What this doesn't do:** post to Pages/company accounts (LinkedIn gates that
behind a partner-approval program), or run without you creating a LinkedIn
Developer app first (a one-time, ~5 minute step LinkedIn requires from everyone,
company or not).

---

## Setup (about 10 minutes, mostly one-time)

### Step 1 — Get your own copy of this repo

Click **"Use this template"** at the top of this repo's GitHub page → create
your own repository (keep it **Private**, since it'll hold your content queue).

Clone it locally:
```
git clone https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git
cd YOUR-REPO-NAME
```

**Recommended:** install the [GitHub CLI](https://cli.github.com) and run
`gh auth login` before continuing — this unlocks the automatic parts of the
next step (privacy policy publishing, secret pushing). Without it, those two
steps become manual (instructions are still provided either way).

### Step 2 — Run the setup wizard

```
python3 setup.py
```

This single command handles almost everything:

1. **Installs dependencies** (requests, pillow)
2. **Auto-publishes a privacy policy page** via GitHub Pages, using an email
   you provide, **copies the live URL to your clipboard**, and **waits until
   the page actually resolves** (up to ~2.5 min — GitHub Pages isn't instant)
   before telling you it's safe to use, so you're never handed a dead URL
3. **Pauses** so you can go create your LinkedIn Developer app using that URL:
   - Go to [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps) → **Create App**
   - **LinkedIn Page**: no company? Select **"Default Company Page for Individual Developer"** — a built-in LinkedIn option made exactly for this case
   - **Logo**: no logo of your own? Upload `default-logo.png` from this folder
   - **Privacy Policy URL**: paste the URL already in your clipboard from step 2
   - Under **Products**, add both **"Share on LinkedIn"** and **"Sign In with LinkedIn using OpenID Connect"** (both instant/self-serve, no approval wait)
   - Go to the **Auth** tab — your **Client ID** and **Client Secret** are shown at the top of that page
   - On the same **Auth** tab, under **OAuth 2.0 settings**, add `http://localhost:8080/callback` as an Authorized redirect URL
4. **Opens your browser** for LinkedIn's login/consent screen — you approve once
5. **Saves your access token** locally as `tokens.json` (never committed — it's in `.gitignore`)
6. **Automatically pushes that token** to your repo's GitHub Actions secrets — if you installed the GitHub CLI in Step 1, this needs zero manual copy-pasting
7. **Asks for a display name and tagline** to show on your generated graphics, **how often to post**, and **whether to include auto-generated graphics or post text-only** — saves all of this to `config.json` and updates the workflow schedule automatically. This only happens on first-time setup; re-running `setup.py` later (e.g. to renew your token) skips straight past it.

   For frequency, pick **weekly / 2x-week / 3x-week** and you'll be asked
   which day(s) (defaults: Mon / Mon+Thu / Mon+Wed+Fri); **daily** needs no
   day picker; **twice a month** asks for two days-of-month (default: 1st
   and 15th); or pick **Custom** and enter your own cron expression for
   anything else — [crontab.guru](https://crontab.guru) helps build one.
   All presets post at a fixed 9:00 AM IST; use Custom for a different time.
8. **Offers to draft your posts for you** — asks if you want AI help, which
   tool you use (Claude / ChatGPT / other), what to post about, and how many.
   First it walks you through downloading your LinkedIn profile as a PDF
   (`More` button → `Save to PDF`) so the AI can write from your actual
   experience instead of generic advice. It then builds the exact prompt,
   copies it to your clipboard, and opens a new chat with it pre-loaded —
   if the deep link doesn't pre-fill for your account, the prompt is on your
   clipboard either way, just paste it in (and attach the PDF, if you got one).
9. **Offers to push `queue.json` for you** — once you've pasted the AI's
   output (or written your own posts) into `queue.json` and saved it, tells
   it to check: it re-validates the file (looping if it still needs fixing),
   warns you if it still looks like the unedited example placeholders, then
   commits and pushes automatically.

### Changing frequency, branding, or image preference later

Just edit `config.json` directly (`display_name`, `tagline`, `use_images: true/false`,
`schedule_cron`), then update the `cron:` line in `.github/workflows/scheduled-post.yml`
to match if you changed the schedule. All of this takes effect on the next scheduled
run — no need to re-run the full setup wizard.

### Compatibility

This repo works on **both macOS and Windows** (and Linux). A few OS-specific notes:
- Use `python3` on Mac/Linux, `python` on most Windows installs — if one doesn't work, try the other
- `renew.command` is the Mac renewal shortcut, `renew.bat` is the Windows one
- Clipboard auto-copy (for the privacy policy URL) uses `pbcopy` on Mac, `clip` on Windows, and `xclip`/`xsel` on Linux (install one of those two if neither is present)
- The actual scheduled posting always runs on GitHub's own Linux servers regardless of your OS — your computer only matters for the one-time/renewal setup steps

### Step 3 (only if you skipped the GitHub CLI) — Manual fallbacks

**Privacy policy:** fill in your email in `docs/privacy-policy-template.html`,
save it as `docs/privacy-policy.html`, and host it anywhere (GitHub Pages,
manually enabled in Settings → Pages, works fine).

**GitHub secret:** run `cat tokens.json`, copy the output, then on GitHub go
to your repo → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret** → name it `TOKENS_JSON` → paste the value → Save.

### Step 4 — Add your content

If you used the wizard's built-in AI helper (Step 8) and let it push for you
(Step 9), **you're already done** — skip to the next section. Otherwise, or
to add more posts later, here's the manual path:

Edit `queue.json` — see `queue.example.json` for the format. It must be a JSON
array where each entry is either a plain string, or an object with:
- `text`: the full post (use `\n\n` for paragraph breaks)
- `hook`: a short line (under ~12 words) used to generate the graphic image (optional)

**Add at least 2 posts** before relying on the schedule — the workflow warns
you (via a GitHub issue) once the queue drops below that.

Before committing, sanity-check the file locally:
```
python3 check_queue.py
```
This is the same check the workflow runs before every post. If `queue.json`
has a syntax error or a malformed entry, it prints exactly what's wrong (e.g.
which item, which field) instead of a raw JSON error — and if you push it
broken anyway, the workflow opens a GitHub issue with that same message and
pauses posting until it's fixed, rather than failing silently.

Then:
```
git add queue.json
git commit -m "add my posts"
git push
```

That's it. The workflow in `.github/workflows/scheduled-post.yml` will now run
on schedule, generate a graphic per post, publish it, and remove it from the
queue automatically.

#### Generating content with an AI assistant

`setup.py`'s Step 8 does this interactively (asks your topic/count, offers to
use your LinkedIn profile PDF for context, opens a pre-loaded chat with
Claude or ChatGPT). To do it by hand instead — with any AI assistant, at any
time — give it a prompt like:

> Write me 6 LinkedIn posts about [your topic]. Output ONLY a raw JSON array,
> no markdown code fences, no commentary before or after. Each item must be an
> object with exactly two string fields: "text" (2-4 short paragraphs,
> `\n\n` between paragraphs, specific numbers/stories over generic advice) and
> "hook" (a punchy line under 12 words summarizing the post, for a graphic).
> Example of the exact shape required:
> `[{"text": "...", "hook": "..."}]`

Paste the output straight into `queue.json` (replacing its contents, not
appending — it must stay a single valid JSON array), then run
`python3 check_queue.py` to confirm it's well-formed before pushing.

---

## Customizing

- **Schedule**: edit the `cron:` line in `.github/workflows/scheduled-post.yml` ([crontab.guru](https://crontab.guru) helps build the expression)
- **Graphic style**: edit the colors/fonts/layout in `generate_image.py`
- **Name/tagline on the graphic**: edit `display_name` and `tagline` in `config.json`

## Important limits

- **Personal profile only.** Posting to a company Page requires LinkedIn's
  Marketing Developer Platform partner approval — a separate, months-long
  process not covered by this tool.
- **Tokens expire every ~60 days and don't auto-refresh** — that's a LinkedIn
  platform limit for self-serve apps, not something this tool can work around.
  When you get the reminder issue/email, double-click `renew.command` (Mac)
  or `renew.bat` (Windows) in your project folder to renew.
- **150 posts/day cap** per LinkedIn's API limits (far more than you'll need).
- **Keep at least 2 posts queued.** If your queue drops below 2, the workflow
  still posts what's left but opens a "queue running low" reminder issue
  (→ email) so you don't get caught with an empty queue. At 0, it stops
  posting entirely and keeps reminding you until you add more.
- **A broken `queue.json` pauses posting, not fails silently.** If it's not
  valid JSON, or an entry is missing its `text` field, the workflow opens a
  "queue.json has a formatting error" issue with the exact problem and skips
  posting until it's fixed. Run `python3 check_queue.py` locally before
  pushing to catch this earlier.

## Running it locally instead of on a schedule

```
python3 post_to_linkedin.py "Your post text" "Your hook line for the graphic"
```
or to post the next queued item on demand:
```
python3 post_to_linkedin.py --from-queue
```

## Contributing

Issues and pull requests welcome — this is meant to stay a simple, readable
tool anyone can audit and self-host, not grow into a heavyweight framework.

## License

MIT — see [LICENSE](LICENSE).
