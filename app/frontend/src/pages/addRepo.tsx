import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@clerk/clerk-react';
import { repoService } from '../services/api';
import GitHubTokenSetup from '../components/GitHubTokenSetup';

const AddRepoPage = () => {
  const { getToken } = useAuth();
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleIngest = async () => {
    if (!repoUrl) return;
    setLoading(true);

    try {
      const token = await getToken();
      await repoService.ingestRepo(repoUrl, token);
      
      const repoName = repoUrl.split('/').pop()?.replace('.git', '') || 'repository';
      
      // navigate to chat
      navigate('/chat', { state: { repoName, repoUrl } });
    } catch (error) {
      console.error(error);
      alert("Error cloning repository. Please check the URL and try again.");
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-full">
      <div className="w-full max-w-xl bg-gray-800 p-8 rounded-xl border border-gray-700">
        <h2 className="text-2xl font-bold mb-6">Load Repository</h2>
        
        {/* GitHub Token Setup */}
        <div className="mb-6">
          <GitHubTokenSetup />
        </div>

        <input 
          className="w-full p-3 rounded bg-gray-900 border border-gray-600 mb-4"
          placeholder="https://github.com/username/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
        />
        <button onClick={handleIngest} className="w-full bg-green-600 py-3 rounded font-bold">
          {loading ? "Cloning..." : "Load Repo"}
        </button>
      </div>
    </div>
  );
};

export default AddRepoPage;