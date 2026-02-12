import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@clerk/clerk-react';
import { ArrowRight, Trash2, ExternalLink, Clock } from 'lucide-react';
import { repoService } from '../services/api';

interface Repository {
  _id: string;
  name: string;
  github_url: string;
  files_processed: number;
  chunks_stored: number;
  ingested_at: string;
}

const ClonedReposPage = () => {
  const navigate = useNavigate();
  const { getToken } = useAuth();
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    loadRepositories();
  }, []);

  const loadRepositories = async () => {
    try {
      const token = await getToken();
      const data = await repoService.getRepositories(token);
      setRepos(data.repositories || []);
    } catch (error) {
      console.error("Failed to load repositories:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleNavigateToChat = (repo: Repository) => {
    navigate('/chat', { 
      state: { 
        repoName: repo.name,
        repoUrl: repo.github_url 
      } 
    });
  };

  const handleDelete = async (id: string, repoName: string) => {
    if (!confirm(`Are you sure you want to delete "${repoName}"? This will remove all associated chat history.`)) {
      return;
    }

    setDeletingId(id);
    try {
      const token = await getToken();
      await repoService.deleteRepo(id, token);
      setRepos(repos.filter(repo => repo._id !== id));
    } catch (error) {
      console.error("Failed to delete repository:", error);
      alert("Failed to delete repository. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading repositories...</div>
      </div>
    );
  }

  if (repos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <div className="text-gray-400 text-lg mb-4">No repositories yet</div>
        <button 
          onClick={() => navigate('/add')}
          className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg font-semibold"
        >
          Add Your First Repository
        </button>
      </div>
    );
  }

  return (
    <div className="p-10">
      <h2 className="text-2xl font-bold mb-6">Your Cloned Repositories</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {repos.map((repo) => (
          <div 
            key={repo._id} 
            className="bg-gray-800 p-6 rounded-xl border border-gray-700 hover:border-blue-500 transition-all group"
          >
            <div className="flex justify-between items-start mb-3">
              <div className="flex-1">
                <h3 className="font-semibold text-blue-400 text-lg mb-1">{repo.name}</h3>
                <a 
                  href={repo.github_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-xs text-gray-500 hover:text-gray-400 flex items-center gap-1"
                >
                  <ExternalLink size={12} />
                  {repo.github_url}
                </a>
              </div>
              <div className="flex gap-4">
                <button 
                  onClick={() => handleDelete(repo._id, repo.name)}
                  disabled={deletingId === repo._id}
                  className="bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed p-2 rounded-lg transition-colors"
                  title="Delete Repository"
                >
                  <Trash2 size={20} />
                </button>
                <button 
                  onClick={() => handleNavigateToChat(repo)}
                  className="bg-blue-600 hover:bg-blue-700 p-2 rounded-lg transition-colors"
                  title="Open in Chat"
                >
                  <ArrowRight size={20} />
                </button>
              </div>
            </div>
            
            <div className="flex items-center gap-4 text-sm text-gray-400 mt-4">
              <div className="flex items-center gap-1">
                <Clock size={14} />
                <span>{formatDate(repo.ingested_at)}</span>
              </div>
              <span>|</span>
              <span>{repo.files_processed} files</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ClonedReposPage;