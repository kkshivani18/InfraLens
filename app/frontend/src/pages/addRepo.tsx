import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, useOrganization } from '@clerk/clerk-react';
import { repoService } from '../services/api';
import GitHubTokenSetup from '../components/GitHubTokenSetup';
import OrgSwitcher from '../components/OrgSwitcher';

const AddRepoPage = () => {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [repositories, setRepositories] = useState([]);
  const [reposLoading, setReposLoading] = useState(false);
  const [activeOrgId, setActiveOrgId] = useState<string | null>(null);
  const navigate = useNavigate();

  // determine workspace type based on activeOrgId
  const workspaceType = activeOrgId ? "org" : "personal";
  const workspaceLabel = activeOrgId ? "Team Workspace" : "Personal Workspace";

  // init from Clerk org context
  useEffect(() => {
    if (organization?.id) {
      setActiveOrgId(organization.id);
      localStorage.setItem('activeOrgId', organization.id);
    } else {
      setActiveOrgId(null);
      localStorage.removeItem('activeOrgId');
    }
  }, [organization?.id]);

  // fetch repositories when workspace changes
  useEffect(() => {
    const fetchRepositories = async () => {
      try {
        setReposLoading(true);
        const token = await getToken();
        const result = await repoService.getRepositories(token, workspaceType, activeOrgId);
        setRepositories(result.repositories || []);
      } catch (error) {
        console.error('Failed to fetch repositories:', error);
        setRepositories([]);
      } finally {
        setReposLoading(false);
      }
    };

    fetchRepositories();
  }, [workspaceType, activeOrgId, getToken]);

  const handleIngest = async () => {
    if (!repoUrl.trim()) {
      alert("Please enter a repository URL");
      return;
    }

    if (!repoUrl.includes("github.com")) {
      alert("Please enter a valid GitHub URL");
      return;
    }

    setLoading(true);

    try {
      const token = await getToken();
      await repoService.ingestRepo(repoUrl, token, activeOrgId);
      
      const repoName = repoUrl.split('/').pop()?.replace('.git', '') || 'repository';
      
      // Refresh repositories list  
      const result = await repoService.getRepositories(token, workspaceType, activeOrgId);
      setRepositories(result.repositories || []);
      
      // Reset form
      setRepoUrl("");
      
      // Navigate to chat
      navigate('/chat', { state: { repoName, repoUrl } });
    } catch (error) {
      console.error(error);
      const errorMsg = error instanceof Error ? error.message : "Unknown error";
      
      if (errorMsg.includes("402")) {
        alert("Monthly ingestion quota reached for this organization. Please wait until next month or upgrade your plan.");
      } else if (errorMsg.includes("403")) {
        alert("You don't have permission to ingest repos for this organization.");
      } else if (errorMsg.includes("404")) {
        alert("Repository not found. Make sure:\n1. The URL is correct (e.g., https://github.com/username/repo)\n2. GitHub token is connected\n3. You have access to the repository");
      } else if (errorMsg.includes("500")) {
        alert("Server error during cloning. Please ensure:\n1. GitHub token is connected\n2. Repository URL is valid\n3. Repository is not too large\n\nCheck GitHub status and try again.");
      } else if (errorMsg.includes("private repository")) {
        alert("This is a private repository. Please connect your GitHub account first.");
      } else {
        alert("Error cloning repository:\n\n" + errorMsg);
      }
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-full">
      <div className="w-full max-w-2xl bg-gray-800 p-8 rounded-xl border border-gray-700">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">Load Repository</h2>
          <OrgSwitcher onOrgChange={setActiveOrgId} className="flex-shrink-0" />
        </div>

        {/* Workspace Info */}
        <div className="mb-4 p-3 bg-blue-900/20 border border-blue-700 rounded-lg">
          <p className="text-sm text-blue-300">
            Ingesting to: <span className="font-semibold">{workspaceLabel}</span>
            {activeOrgId && <span className="ml-2 text-xs text-blue-400">(shared with team members)</span>}
          </p>
        </div>
        
        {/* GitHub Token Setup */}
        <div className="mb-6">
          <GitHubTokenSetup />
        </div>

        {/* Ingest Form */}
        <div className="mb-8">
          <input 
            className="w-full p-3 rounded bg-gray-900 border border-gray-600 mb-4 focus:outline-none focus:border-blue-500"
            placeholder="https://github.com/username/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
          />
          <button 
            onClick={handleIngest} 
            disabled={loading}
            className="w-full bg-green-600 py-3 rounded font-bold hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Cloning..." : "Load Repo"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddRepoPage;