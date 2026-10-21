# Shared copy (optional): let a friend see the list

The **shared copy** is a tiny always-on web server that holds your finished listings page, your notes and statuses, and (if you use the fun layer) the points and pictures. A friend logs in and sees the same list, and what they mark or write shows up on your side too. It never scrapes anything: all scraping stays on your own computer.

It is written for [Railway](https://railway.app) because that is what the author used, but it is one small Python file (`cloud/app.py`) and a Dockerfile, so any host that runs a container with a disk will do.

You need it for: sharing with a friend, background notifications on your phone, and the points / streaks / pictures of the fun layer. You do **not** need it for anything else.

## Setup (about 15 minutes)

1. **Install the Railway CLI** and log in: `railway login`.
2. **Create a project** with one empty service (Railway dashboard, "New project", "Empty service"). Note the **project ID** and the **service name** (dashboard, Settings).
3. **Add a volume** to the service, mounted at `/data`. This is where notes, points and pictures live. Without it they vanish at every deploy.
4. **Set the service variables**:

   | Variable | Value |
   |---|---|
   | `USERS` | `you:a-long-password,friend:another-long-password` (lowercase names, one login each) |
   | `PUBLISH_TOKEN` | a long random string. Your computer uses it to publish. Never share it |
   | `REQUIRE_HTTPS` | `1` |
   | `TZ_NAME` | optional, default `Europe/Brussels` (the clock used to decide which edit is newer) |

5. **Deploy** from the project folder:

   ```bash
   ./cloud/deploy.sh <project-id> <service-name>
   ```

6. **Generate a domain** for the service (Settings, Networking). You get something like `https://xyz.up.railway.app`.
7. **Tell your computer about it**: add three lines to `.env` (next to `serve.py`):

   ```
   CLOUD_URL=https://xyz.up.railway.app
   CLOUD_TOKEN=<the same string as PUBLISH_TOKEN>
   CLOUD_OWNER=you
   ```

   `CLOUD_OWNER` must be one of the names in `USERS` (it is the name your own changes are recorded under).
8. Open the control panel and press **Publish now** (every scrape also publishes). Send your friend the address and their login.

## What goes there, and what does not

- **Sent to the shared copy:** the finished page, the listing descriptions (the text of the public ads), statuses, marks, notes, history lines, viewing dates, and the fun layer's events and pictures.
- **Never sent:** your `.env`, the Gemini key, `config.json`, the Gmail link and your emails, the scraper state, your run history. The Gmail text stays on your computer: only a flat's status can become "replied".
- **Both ways:** marks, notes and history written on the shared site reach your computer, and the other way round. If you both change the same flat, the newer change wins, and both histories are kept.

## Notifications on the phone or browser

Open the **shared site** (not the local page), go to the Today tab, and press **Allow notifications**. The server then sends the hourly nudges and your morning summary, even when the page is closed. The push keys are created by the server on first start and kept on the volume. On an iPhone the site has to be added to the Home Screen first; I have not tested that.

## Safety

- Every page and API call needs a login (HTTP Basic over HTTPS) or the publish token. Repeated wrong passwords lock an address out for ten minutes.
- Use long, different passwords. The page is private, not secret: anyone with a login sees everything on it.
- If the publish token or a password leaks, change the variable in Railway and in your `.env`.
- Uploads that arrive cut off are refused, so a dropped connection cannot leave a half-written page.

## Cost

A small always-on container plus a small volume. Expect a few dollars a month at most, but check Railway's current pricing; it changes.

## When something goes wrong

- **"Deploys have been paused temporarily":** Railway is having an incident. Your running copy keeps working with the old code. Try again later, and check their status page.
- **401 on the page:** wrong login. **429:** too many wrong passwords, wait ten minutes.
- **The page is empty or old:** press "Publish now" in the control panel and read the error under "Shared copy".
- **A new feature does nothing on the shared site:** the server code is older than the page. Deploy again.
