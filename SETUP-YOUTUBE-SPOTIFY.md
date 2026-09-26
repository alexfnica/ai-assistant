# Connecting Jarvis to Spotify and YouTube (one-time, about 10 minutes each)

Jarvis never sees your passwords. You approve access on the official Spotify / Google page, and Jarvis keeps
only a login token inside the `data` folder on this PC. Say `disconnect spotify` or `disconnect youtube` to remove it.

## Spotify (needs Premium)

1. Open https://developer.spotify.com/dashboard and log in with your Spotify account.
2. Click **Create app**. Name: `Jarvis`. Description: `Personal assistant`.
3. **Redirect URI**: type exactly `http://127.0.0.1:4891/spotify/callback` and click **Add**.
   (It must be `127.0.0.1`, not `localhost`.)
4. Under "Which API/SDKs are you planning to use?" tick **Web API**, accept the terms, click **Save**.
5. Open the app, then **Settings**, and copy the **Client ID**. You do not need the secret.

## YouTube

1. Open https://console.cloud.google.com and sign in with the Google account that owns your channel.
2. Top left, project menu, **New project**, name `Jarvis`, **Create**, and select it.
3. Menu, **APIs & Services**, **Library**. Search and **Enable** both: **YouTube Data API v3** and **YouTube Analytics API**.
4. Menu, **APIs & Services**, **OAuth consent screen** (or "Google Auth Platform"). Click **Get started**:
   app name `Jarvis`, your email, audience **External**, your email again, accept, **Create**.
5. In **Audience**, click **Publish app** (status "In production"). This stops the login from expiring every 7 days.
   It stays private: only you use it. Google will show an "unverified app" warning at login; that is normal here.
6. Menu, **Clients** (or Credentials), **Create client**, type **Desktop app**, name `Jarvis`, **Create**.
   Copy the **Client ID** and the **Client secret**.

## Give the values to Jarvis

Double-click `Setup-YouTube-Spotify.cmd` in the Jarvis folder and paste the values when asked
(right-click in the black window to paste). They are saved only on this computer. Do not paste the client secret in chat.

## Connect and use

Restart Jarvis (`Restart-Jarvis.cmd`), then say or type:

- `connect spotify` and approve in the page that opens. Then: `play Back in Black`, `play Thunderstruck by AC/DC`,
  `pause`, `resume`, `next`, `previous`, `volume 40`, `what's playing`.
  If Spotify is closed, Jarvis starts it and plays on this PC.
- `connect youtube`. On the Google page choose your channel's account, click **Advanced**, then
  **Go to Jarvis (unsafe)** and allow read-only access. Then: `my channel`, `my videos`,
  `video report: king tiger`, `give me feedback on my latest video`.

Written feedback uses the cloud model (it needs your Claude API key and credit); without it Jarvis shows the numbers and comments.
YouTube access is read-only: Jarvis cannot upload, edit or delete anything.
