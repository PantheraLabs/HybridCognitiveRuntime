import express from 'express';
import fetch from 'node-fetch';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config({ path: path.join(__dirname, '..', '..', '..', '.env') });

const app = express();
app.use(express.json());

const CLIENT_ID = process.env.VITE_GITHUB_CLIENT_ID;
const CLIENT_SECRET = process.env.VITE_GITHUB_CLIENT_SECRET;
const PORT = process.env.GITHUB_AUTH_PROXY_PORT || 5174;

if (!CLIENT_ID || !CLIENT_SECRET) {
  console.warn('[GitHubAuthProxy] Missing GitHub OAuth credentials in .env');
}

app.post('/api/auth/github/callback', async (req, res) => {
  try {
    const { code } = req.body;
    if (!code) {
      return res.status(400).json({ error: 'Missing authorization code' });
    }

    const tokenResponse = await fetch('https://github.com/login/oauth/access_token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
        code
      })
    });

    const tokenJson = await tokenResponse.json();

    if (tokenJson.error) {
      return res.status(400).json({ error: tokenJson.error_description || tokenJson.error });
    }

    const userResponse = await fetch('https://api.github.com/user', {
      headers: {
        Authorization: `Bearer ${tokenJson.access_token}`,
        'User-Agent': 'HCR-Onboarding-App'
      }
    });

    if (!userResponse.ok) {
      return res.status(400).json({ error: 'Failed to fetch GitHub profile' });
    }

    const userJson = await userResponse.json();

    res.json({
      access_token: tokenJson.access_token,
      token_type: tokenJson.token_type,
      scope: tokenJson.scope,
      user: {
        id: userJson.id,
        login: userJson.login,
        name: userJson.name,
        avatar_url: userJson.avatar_url,
        html_url: userJson.html_url
      }
    });
  } catch (error) {
    console.error('[GitHubAuthProxy] Token exchange failed', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.get('/api/auth/health', (_req, res) => {
  res.json({ status: 'ok', clientConfigured: Boolean(CLIENT_ID && CLIENT_SECRET) });
});

app.listen(PORT, () => {
  console.log(`[GitHubAuthProxy] listening on http://localhost:${PORT}`);
});
