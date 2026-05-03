import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function GitHubCallback() {
  const navigate = useNavigate();
  const [status, setStatus] = useState('processing');
  const [message, setMessage] = useState('Exchanging authorization code with GitHub...');

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const code = query.get('code');
    const returnedState = query.get('state');
    const storedState = sessionStorage.getItem('github_oauth_state');

    if (!code) {
      setStatus('error');
      setMessage('Missing authorization code. Please restart the login flow.');
      return;
    }

    if (!storedState || storedState !== returnedState) {
      setStatus('error');
      setMessage('Security check failed (state mismatch). Try signing in again.');
      return;
    }

    const exchangeCode = async () => {
      try {
        const response = await fetch('/api/auth/github/callback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ code })
        });

        if (!response.ok) {
          const errorPayload = await response.json().catch(() => ({}));
          throw new Error(errorPayload.error || 'GitHub token exchange failed');
        }

        const data = await response.json();
        sessionStorage.removeItem('github_oauth_state');

        setStatus('success');
        setMessage(`Welcome back ${data.user?.name || data.user?.login || 'developer'}! Redirecting...`);

        const next = sessionStorage.getItem('github_oauth_next') || '/app';
        sessionStorage.removeItem('github_oauth_next');
        setTimeout(() => navigate(next, { replace: true }), 1200);
      } catch (err) {
        setStatus('error');
        setMessage(err.message);
      }
    };

    exchangeCode();
  }, [navigate]);

  const statusStyles = {
    processing: 'text-blue-300',
    success: 'text-emerald-300',
    error: 'text-red-300'
  };

  const StatusIcon = {
    processing: Loader2,
    success: CheckCircle2,
    error: AlertCircle
  }[status];

  return (
    <div className="min-h-screen bg-[#050505] flex flex-col items-center justify-center text-center px-6">
      <div className="max-w-md w-full border border-white/10 rounded-3xl p-10 bg-[#0C0C0C]">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-white text-black font-black text-2xl mb-8">
          Ω
        </div>
        <StatusIcon className={`w-10 h-10 mx-auto mb-6 ${status === 'processing' ? 'animate-spin' : ''} ${statusStyles[status]}`} />
        <p className="text-white text-xl font-semibold mb-4">
          {status === 'processing' && 'Completing GitHub sign-in'}
          {status === 'success' && 'Authenticated successfully'}
          {status === 'error' && 'Authentication failed'}
        </p>
        <p className="text-zinc-400 text-sm leading-relaxed">{message}</p>
      </div>
    </div>
  );
}
