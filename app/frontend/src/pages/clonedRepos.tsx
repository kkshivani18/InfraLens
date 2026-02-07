import { useState } from 'react';
import { Trash2, ExternalLink } from 'lucide-react'; 

const ClonedReposPage = () => {
  const [repos, setRepos] = useState([
    { id: '1', name: 'terraform-azure-infrastructure', url: 'https://github.com/kkshivani18/...' },
  ]);

  const handleDelete = (id: string) => {
    // call repoService.deleteRepo
    setRepos(repos.filter(repo => repo.id !== id));
  };

  return (
    <div className="p-10">
      <h2 className="text-2xl font-bold mb-6">Your Codebases</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {repos.map((repo) => (
          <div key={repo.id} className="bg-gray-800 p-6 rounded-xl border border-gray-700 flex justify-between items-center group">
            <div>
              <h3 className="font-semibold text-blue-400">{repo.name}</h3>
              <p className="text-sm text-gray-500 truncate max-w-xs">{repo.url}</p>
            </div>
            <div className="flex gap-4 opacity-0 group-hover:opacity-100 transition-opacity">
              <button className="text-gray-400 hover:text-white"><ExternalLink size={20} /></button>
              <button onClick={() => handleDelete(repo.id)} className="text-red-500 hover:text-red-400">
                <Trash2 size={20} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ClonedReposPage;