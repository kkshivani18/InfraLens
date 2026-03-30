import { useState } from 'react';
import { useAuth } from '@clerk/clerk-react';

interface ShareChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  chatSessionId: string;
  repositoryName: string;
  teamMembers?: Array<{ id: string; name: string; email: string }>;
}

export const ShareChatModal = ({
  isOpen,
  onClose,
  chatSessionId,
  repositoryName,
  teamMembers = []
}: ShareChatModalProps) => {
  const { getToken } = useAuth();
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleShareWithMembers = async () => {
    if (selectedMembers.length === 0) {
      setError("Please select at least one team member");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = await getToken();
      
      // Call backend to create shares for each member
      for (const memberId of selectedMembers) {
        await fetch(`${import.meta.env.VITE_API_URL}/api/chat/share`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            chat_session_id: chatSessionId,
            repository_name: repositoryName,
            shared_with_user_id: memberId
          })
        });
      }

      // Generate shareable link
      const baseUrl = window.location.origin;
      const link = `${baseUrl}/chat?session=${chatSessionId}&repo=${repositoryName}`;
      setShareLink(link);
      
      setSelectedMembers([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to share chat");
    } finally {
      setLoading(false);
    }
  };

  const toggleMemberSelection = (memberId: string) => {
    setSelectedMembers((prev) =>
      prev.includes(memberId)
        ? prev.filter((id) => id !== memberId)
        : [...prev, memberId]
    );
  };

  const copyToClipboard = () => {
    if (shareLink) {
      navigator.clipboard.writeText(shareLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white">Share Chat</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>

        {/* Repository Info */}
        <div className="bg-gray-900/50 rounded-lg p-3 mb-4">
          <p className="text-sm text-gray-400">Repository:</p>
          <p className="text-white font-semibold">{repositoryName}</p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-900/20 border border-red-700 rounded-lg p-3 mb-4 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Share Link Display */}
        {shareLink && (
          <div className="mb-4">
            <p className="text-sm text-gray-400 mb-2">Share Link:</p>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={shareLink}
                readOnly
                className="flex-1 bg-gray-900 text-sm p-2 rounded border border-gray-700 text-gray-300"
              />
              <button
                onClick={copyToClipboard}
                className="px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium text-white transition"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          </div>
        )}

        {/* Team Members List */}
        {teamMembers.length > 0 && !shareLink && (
          <div className="mb-4">
            <p className="text-sm text-gray-400 mb-2">Share with team members:</p>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {teamMembers.map((member) => (
                <label
                  key={member.id}
                  className="flex items-center gap-3 p-2 hover:bg-gray-700/50 rounded cursor-pointer transition"
                >
                  <input
                    type="checkbox"
                    checked={selectedMembers.includes(member.id)}
                    onChange={() => toggleMemberSelection(member.id)}
                    className="w-4 h-4 rounded border-gray-600 bg-gray-700"
                  />
                  <div className="flex-1 text-sm">
                    <p className="text-white font-medium">{member.name}</p>
                    <p className="text-gray-400 text-xs">{member.email}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* No Members */}
        {teamMembers.length === 0 && !shareLink && (
          <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-3 mb-4 text-sm text-blue-300">
            💡 Share links work for Pro/Team plan members. To share with specific team members, invite them to your organization first.
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          {!shareLink && teamMembers.length > 0 && (
            <button
              onClick={handleShareWithMembers}
              disabled={loading || selectedMembers.length === 0}
              className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed rounded font-medium text-white transition"
            >
              {loading ? "Sharing..." : `Share (${selectedMembers.length})`}
            </button>
          )}
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded font-medium text-white transition"
          >
            {shareLink ? "Close" : "Cancel"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ShareChatModal;
