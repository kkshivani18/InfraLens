import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { repoService } from '../services/api';

const AddRepoPage = () => {
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<{ role: string, text: string }[]>([]);
  const navigate = useNavigate();

  const handleIngest = async () => {
    if (!repoUrl) return;
    setLoading(true);
    const statusMsg = { role: "ai", text: `Cloning ${repoUrl}` };
    setMessages(prev => [...prev, statusMsg]);

    try {
      const data = await repoService.ingestRepo(repoUrl);
      
      const successMsg = { 
        role: "ai", 
        text: `Analyzed ${data.files_processed} files.` 
      };
      setMessages(prev => [...prev, successMsg]);
      const repoName = repoUrl.split('/').pop()?.replace('.git', '') || 'repository';
      
      // navigate to chat
      navigate('/chat', { state: { repoName, repoUrl } });
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: "ai", text: "Error cloning repo." }]);
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-full">
      <div className="w-full max-w-xl bg-gray-800 p-8 rounded-xl border border-gray-700">
        <h2 className="text-2xl font-bold mb-6">Load Repository</h2>
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