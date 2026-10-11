# Onboarding

Run this once, when `~/job-hunt/profile.md` does not exist. Keep it friendly and short: the user wants to start applying, not fill out a survey.

## 1. Ask the questions

Use your multiple-choice question tool if you have one (in Claude Code: AskUserQuestion), batching related questions together. Otherwise ask in one message. Accept "skip" for anything optional.

1. **Roles**: target job titles, seniority, years of experience.
2. **Location**: current city and country; remote, hybrid or onsite; cities or countries they would work in; open to relocation?
3. **Work authorization**: countries where they can work without sponsorship; do they need visa sponsorship elsewhere?
4. **Pay**: currency, minimum acceptable, and target, per location type if they differ (for example India office vs remote abroad). Ask whether to quote the company's posted range when one exists.
5. **Notice period** or earliest start date.
6. **Platforms**: LinkedIn, Indeed, Wellfound, Naukri, company career pages, others.
7. **Approval mode**: ask before every submit (recommended) or auto-submit. Daily application limit (default 20).
8. **Optional**: answers for demographic questions, or "Decline to self-identify".

## 2. Get the resume

Ask the user to paste their resume text or give a file path (PDF or DOCX).

- Copy files into `~/job-hunt/resume/`. Keep the original file name.
- Read it and fill the profile's facts from it: name, email, phone, links, education, experience, skills.
- Offer to review it. Suggest concrete improvements (clarity, impact, keywords for their target roles), but never add anything that isn't true. If they want a revised version, write it to `~/job-hunt/resume/resume.md` and help them export it to PDF. Until then, applications use the original file.

## 3. Write `profile.md`

Create `~/job-hunt/profile.md` from `profile-template.md` next to this file. Show the user the result and ask them to correct anything wrong.

## 4. Connect the browser

Run `sgaj tabs`.

- If it lists tabs, the browser is connected.
- If it prints setup steps: ask the user to open `chrome://inspect/#remote-debugging` in Chrome and enable "Allow remote debugging for this browser instance". Run `sgaj tabs` again; if Chrome shows an "Allow" prompt, they click Allow once.

## 5. Sign in

For each chosen platform:

1. `sgaj open <login URL>` (for example `https://www.linkedin.com/login`, `https://secure.indeed.com/auth`, `https://wellfound.com/login`), then `sgaj show`.
2. Ask the user to sign in in that tab and tell you when they are done. Never ask for or type their password.
3. `sgaj look` to confirm they are signed in (profile menu, no "Sign in" button).

Then tell the user setup is done and ask what they want first, for example: "Apply to 10 remote AI engineer jobs on LinkedIn".
