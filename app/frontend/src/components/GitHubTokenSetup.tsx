import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';

export const GitHubTokenSetup = () => {
  const { getToken } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [tokenInput, setTokenInput] = useState('');

  const API_BASE_URL = 'http://localhost:8000';

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_BASE_URL}/api/github/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setIsConnected(data.connected);
    } catch (error) {
      console.error('Failed to check GitHub status:', error);
    }
  };

  const handleConnect = async () => {
    if (!tokenInput.trim()) {
      alert('Please enter a GitHub token');
      return;
    }

    setLoading(true);
    try {
      const token = await getToken();
      
      console.log('[GitHub Connect] Sending request to:', `${API_BASE_URL}/api/github/connect`);
      console.log('[GitHub Connect] Token length:', tokenInput.trim().length);
      
      const response = await fetch(`${API_BASE_URL}/api/github/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          github_token: tokenInput.trim(),
          github_username: 'user' // Will be extracted from token
        })
      });

      console.log('[GitHub Connect] Response status:', response.status);
      
      if (response.ok) {
        const result = await response.json();
        console.log('[GitHub Connect] Success:', result);
        setIsConnected(true);
        setShowTokenInput(false);
        setTokenInput('');
        alert('✅ GitHub connected! You can now access private repositories.');
        checkStatus(); // Refresh status
      } else {
        const errorText = await response.text();
        console.error('[GitHub Connect] Error response:', errorText);
        
        try {
          const errorJson = JSON.parse(errorText);
          alert(`Failed: ${errorJson.detail || errorJson.message || 'Unknown error'}`);
        } catch {
          alert(`Failed: ${response.status} - ${errorText}`);
        }
      }
    } catch (error) {
      console.error('[GitHub Connect] Exception:', error);
      const errorMessage = error instanceof Error ? error.message : 'Network error';
      alert(`Failed to connect GitHub: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  if (isConnected) {
    return (
      <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <span className="text-green-800 font-medium">GitHub Connected - Private repos enabled</span>
        </div>
      </div>
    );
  }

  if (!showTokenInput) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-5 h-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span className="text-yellow-800 font-medium">GitHub Not Connected</span>
          </div>
          <p className="text-sm text-yellow-700 mb-3">
            To analyze private repositories, connect your GitHub account with a Personal Access Token.
          </p>
          <button
            onClick={() => setShowTokenInput(true)}
            className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors"
          >
            Connect GitHub
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
      <h3 className="font-semibold text-blue-900 mb-3">Connect GitHub</h3>
      
      <div className="mb-4 p-3 bg-blue-100 rounded-lg text-sm">
        <p className="font-medium text-blue-900 mb-2">📝 How to get a GitHub token:</p>
        <ol className="list-decimal list-inside space-y-1 text-blue-800">
          <li>Go to <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer" className="underline">GitHub Settings → Tokens</a></li>
          <li>Click "Generate new token (classic)"</li>
          <li>Select scope: <strong>repo</strong> (Full control of private repositories)</li>
          <li>Generate and copy the token</li>
        </ol>
      </div>

      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            GitHub Personal Access Token
          </label>
          <input
            type="password"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleConnect}
            disabled={loading || !tokenInput.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Connecting...' : 'Connect'}
          </button>
          <button
            onClick={() => {
              setShowTokenInput(false);
              setTokenInput('');
            }}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default GitHubTokenSetup;
