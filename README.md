# alitunc.net

Personal website of Ali Tunç. Static site, bilingual (Dutch at the root, English under `/en/`),
built by `build.py` and hosted on Netlify.

- **Production:** https://alitunc.net (branch `main`)
- **Content editor (CMS):** https://alitunc.net/admin/

---

## 1. Overview

```
content/nl/*.json            ┐
content/en/*.json            │
templates/*.html             │
notes/nl/*.md, notes/en/*.md ├─►  build.py  ─►  dist/  ─►  Netlify  ─►  alitunc.net
css/ js/ images/ vendor/ …   ┘   (checks + build)
```

- `main` is production. Every push to `main` (also a save in the CMS) triggers a Netlify build.
- `build.py` **checks everything first**. If a check fails, the build stops (exit code 1), the
  Netlify deploy fails and **the previous version stays online**. GitHub Actions (`validate`)
  runs the same build on every push and pull request to `main`.
- `dist/` is generated and not in git. Only what is listed in `STATIC` in `build.py` is
  published; sources such as `build.py`, `templates/`, `content/`, `notes/` and
  `content-denylist.txt` are not.
- Site texts live in `content/<language>/`: `site.json` (navigation, footer, contact block,
  lab-notes texts) and one file per page (`home`, `expertise`, `about`, `projects`, `cv`,
  `contact`), each with its own `seo` block. Dutch and English always have the same files,
  fields and list lengths.
- Code changes: create a branch from `main`, open a pull request, test the deploy preview,
  then merge (squash).

## 2. Working locally

Requires Python 3.12 (the same version as Netlify and the GitHub Action).

```powershell
python build.py                          # check + build into dist/
python build.py --list                   # same, and list the contents of dist/
python -m http.server 8000 -d dist       # view at http://localhost:8000
```

If the build fails, every problem is listed as a `FOUT:` line with the file and, where
possible, the line number. Fix them all and run it again.

All rules that `build.py` enforces are described at the top of `build.py`.

## 3. Using the CMS

### Sign in

1. Open https://alitunc.net/admin/
2. Click **Sign In with Token** and paste the personal access token (see section 4).
3. Only sign in on your own devices; never on shared or public computers. Sign out when you
   stop using a device (avatar, top right → **Sign Out**). The token is stored in that browser
   for that address only.

### Write a lab note

1. **Lab notes** → **New**. Each note exists in **Dutch and English**; fill in both tabs.
2. Fields: **Titel** (title), **Datum** (date, same for both languages), **Korte beschrijving**
   (one sentence for the list and for search engines), **Concept (niet publiceren)**, **Tekst**.
3. **Tekst** supports: `##` and `###` headings, bold, italic, `inline code`, links, bulleted
   and numbered lists, quotes and code blocks. Links must start with `https://` or `/`
   (a page on this site). Anything else stops the build. `mailto:` links are technically
   accepted by the link check, but every e-mail address is blocked by the content denylist
   (section 3, "Forbidden content"), so in practice they stop the build too.
4. **Save.** The CMS commits to `main`; the site is updated in 1–2 minutes.

### Concept (draft) and publishing

- **Concept on** = draft: the note is not built, not checked and not online. A half-written
  note never blocks a deploy.
- **Concept off** = publish: all checks apply, and the note must be complete in both languages.
- New notes start with **Concept on**. To publish: open the note, switch Concept off, Save.
- The Concept switch is shared by both languages. On the English tab it is greyed out; the
  value is copied from the Dutch tab when saving.
- Files without a `draft:` line (for example notes written outside the CMS) make the build
  fail on purpose, so nothing is published by accident.
- **Caution with older notes:** for a note whose file has no `draft:` line yet, the switch
  that the CMS *shows* can differ from what it *saves*. After saving, check the frontmatter on
  GitHub (`notes/nl/<slug>.md` and `notes/en/<slug>.md`): `draft: true` or `draft: false`
  must be what you intended.
- Lab notes appear in the navigation only when at least one note is published.

### Slug (file name / URL)

- The slug is created from the title when the note is first saved and cannot be changed later.
- Only `a-z`, `0-9` and hyphens are allowed.
- **Turkish dotless `ı`:** the CMS drops it from the slug (for example `ışık` becomes `s-k`).
  For titles with `ı`, correct the slug by hand when creating the note.

### Forbidden content (denylist)

`content-denylist.txt` (repository root, never published) lists what must never appear on the
site: the current employer, former employers, the home address, phone numbers and e-mail
addresses. `build.py` checks all texts in `content/`, all published lab notes and every
text file that goes online (HTML, JSON, YAML, TXT, XML; not `vendor/` and not the data files
`json/news.json`, `json/globe.json`, `json/topology.json`). A match stops the build and names
the file and field or line; the matched text is only shown partially in the log.

- One term per line: case-insensitive, whole words only.
- Lines starting with `re:` are regular expressions (phone and e-mail patterns are included).
- Lines starting with `#` are comments.

**Editing the list (on your own computer):**

1. Open `D:\mijnwebsite\content-denylist.txt` in Notepad++.
2. Add your terms under "Zelf invullen", one per line, without the leading `#`.
   Add common variants too (with and without legal form, abbreviations, domain name).
3. Save (keep the encoding UTF-8).
4. In PowerShell, in `D:\mijnwebsite`:
   ```powershell
   python build.py                 # must still say OK; otherwise the site contains a match
   git add content-denylist.txt
   git commit -m "content: denylist bijgewerkt"
   git push
   ```
   Commit on a branch and open a pull request if other work is in progress.

The file is in the (private) repository. Do not list secrets in it, only words that must not
appear on the site.

### Images

- **Assets** → **Upload**. Allowed: JPG, PNG, WebP, AVIF. SVG is not allowed.
- Every upload is converted to **WebP** (quality 85, max. 2400 px). This also removes
  EXIF/GPS/camera data. `build.py` rejects any upload that still contains EXIF, XMP or IPTC.
- iPhone photos in **HEIC** cannot be uploaded. Use JPEG
  (iPhone: Settings → Camera → Formats → Most Compatible).
- Maximum 5 MB after conversion.
- Images inside a note are not supported yet (see section 7).

## 4. Access token (PAT)

The CMS signs in with a GitHub **fine-grained personal access token**. No OAuth app is used.

| | |
|---|---|
| Name | `alitunc-cms` |
| Repository access | only `tunc-ali/portfolio` |
| Permissions | Contents: **Read and write** (Metadata: read-only, automatic). Nothing else. |
| Created | 2026-11-21 |
| **Expires** | **2027-02-19** |
| **Renew by** | **2027-02-12** (one week before) |

The token is stored in a password manager. Never paste it in chats, issues, commits or files.

### Renewing (by 2027-02-12)

1. GitHub → avatar (top right) → **Settings** → **Developer settings** →
   **Personal access tokens** → **Fine-grained tokens** → `alitunc-cms`.
2. Click **Regenerate token**, choose an expiration of 90 days, **Regenerate**.
   Check that the repository access and permissions are still as in the table above.
3. Copy the new token into the password manager (replace the old one).
4. On https://alitunc.net/admin/: **Sign Out**, then **Sign In with Token** with the new token.
5. Update the dates in the table above (in a pull request).

### If the token expires

Signing in to the CMS fails. The website itself keeps working. Create or regenerate a token
as above.

### If the token leaks

1. GitHub → Settings → Developer settings → Fine-grained tokens → `alitunc-cms` → **Delete**.
2. Check the recent commits on `main` for changes you did not make.
3. Create a new token with the same settings.

## 5. Updating Sveltia CMS

Sveltia CMS is stored locally in `vendor/sveltia-cms/` with a fixed version (no CDN).
`vendor/README.md` lists the version, the npm integrity value, the SHA-256 checksums and the
update steps. Always test a new version in a deploy preview first (sign in, open a note,
upload an image, check the browser console for CSP errors).

Check the files on Windows:

```powershell
Get-ChildItem vendor -Recurse -File | Get-FileHash -Algorithm SHA256 | Format-Table Hash, Path -AutoSize
```

`.gitattributes` keeps everything under `vendor/` byte for byte, so the hashes also match
after a checkout on Windows.

## 6. Troubleshooting

**"validate failed" e-mail or a failed Netlify deploy**
The site still shows the previous version. Open the failed run
(GitHub → Actions, or Netlify → Deploys → the failed deploy → log) and read the `FOUT:` lines.
Fix the content in the CMS or in git and save again. A half-finished note: switch Concept on.

**Go back to an earlier version of the site**
- Fast: Netlify → **Deploys** → choose an earlier successful deploy → **Publish deploy**.
  Netlify then stops auto-publishing until you click **Start auto publishing** again.
- Permanent: `git revert <commit>` on a branch, pull request, merge.

**The CMS looks broken after an update / errors in the console**
`/admin` has a strict Content Security Policy (see `netlify.toml`). Press F12 → Console and look
for `Refused to …` messages. Only add the exact source that is needed, and only for `/admin`.
Known and harmless: blocked requests to `unpkg.com` (update check, UI translations,
transliteration) and `www.githubstatus.com`.

**"Work with Local Repository" does not work**
Known issue: selecting the repository folder fails with "A repository root directory could not
be selected". Workaround for testing a new `admin/config.yml` before it is online:

```powershell
python -m http.server 8000 --bind 127.0.0.1     # in the repository root, not dist/
```

Open http://127.0.0.1:8000/admin/ and sign in with the token. **This writes to the branch in
`admin/config.yml` on GitHub.** Sign out afterwards. This local page has no security headers (no CSP); use it only
briefly for testing.

## 7. Security summary

- `/admin`: strict CSP (`default-src 'none'`, scripts only from this site, connections only to
  the GitHub API, fonts additionally from `cdn.jsdelivr.net`), `X-Frame-Options: DENY`,
  `frame-ancestors 'none'`, `noindex`, `Cache-Control: no-store`, `Permissions-Policy`,
  `Referrer-Policy: no-referrer`. Also excluded in `robots.txt`.
- `/images/uploads/*`: `nosniff` and a sandbox CSP.
- Notes: HTML in a note is always shown as text, never executed; only safe link types.
- Content denylist (`content-denylist.txt`): employer, address, phone numbers and e-mail
  addresses can never be published by accident.
- Uploads: type checked by content (not by extension), no metadata, size limit.
- Third-party code in `vendor/` is pinned and checksummed.
- GitHub Pages must stay disabled (Settings → Pages → Source: None); it published the
  repository root before.
- Two-factor authentication must be enabled on the GitHub account (the CMS acts with its
  permissions via the token).

## 8. To do

- Fix "Work with Local Repository" (see section 6).
- Images inside lab notes (Markdown images in `build.py`).
- Second round of CMS fields: all pages from `content/<language>/*.json` (in progress).
- Site-style 404 page (NL/EN).
- Hardening phase: CSP and security headers for the whole site, HSTS, secret scan of the
  full git history, checks on old hosting addresses, and a periodic check for other deploy
  targets connected to the repository (GitHub → Settings → Integrations / Applications,
  webhooks).
