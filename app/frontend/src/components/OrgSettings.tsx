import { useState, useEffect } from 'react';
import { useAuth, useOrganization } from '@clerk/clerk-react';
import { orgService } from '../services/api';

interface OrgMember {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'member';
}

interface OrgDetailsType {
  org_id: string;
  name: string;
  owner_user_id: string;
  plan: string;
  member_count: number;
  seats_max: number;
  ingestion_quota_monthly: number;
  repos_ingested_this_month: number;
  created_at: string;
}

export const OrgSettings = () => {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  
  const [orgDetails, setOrgDetails] = useState<OrgDetailsType | null>(null);
  const [inviteEmail, setInviteEmail] = useState('');
  const [loading, setLoading] = useState(true);
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Fetch org details on mount
  useEffect(() => {
    if (!organization?.id) {
      setError("Not in an organization");
      setLoading(false);
      return;
    }

    fetchOrgDetails();
  }, [organization?.id]);

  const fetchOrgDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const token = await getToken();
      const data = await orgService.getOrgDetails(token, organization?.id);
      
      if (data.error) {
        setError(data.message || "Failed to load organization details");
        setOrgDetails(null);
        return;
      }
      
      setOrgDetails(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load org details");
      setOrgDetails(null);
    } finally {
      setLoading(false);
    }
  };

  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inviteEmail || !inviteEmail.includes('@')) {
      setError('Please enter a valid email address');
      return;
    }

    setInviting(true);
    setError(null);
    setSuccess(null);

    try {
      const token = await getToken();
      await orgService.inviteMember(inviteEmail, token, organization?.id);
      
      setSuccess(`Invitation sent to ${inviteEmail}`);
      setInviteEmail('');
      
      // refresh org details
      setTimeout(() => fetchOrgDetails(), 1000);
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Failed to invite member";
      
      // parse specific error codes
      if (errMsg.includes('402')) {
        setError('Seat limit reached. Upgrade your plan to add more members.');
      } else if (errMsg.includes('403')) {
        setError('Only org admins can invite members.');
      } else {
        setError(errMsg);
      }
    } finally {
      setInviting(false);
    }
  };

  if (!organization?.id) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-gray-400 mb-4">Not in an organization</p>
          <p className="text-sm text-gray-500">Create or join an org to access settings</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading organization settings...</div>
      </div>
    );
  }

  if (!orgDetails) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-red-400 mb-4">Failed to load organization</p>
          <button
            onClick={() => fetchOrgDetails()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white text-sm font-medium"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const quotaPercentage = (orgDetails.repos_ingested_this_month / orgDetails.ingestion_quota_monthly) * 100;
  const seatsPercentage = (orgDetails.member_count / orgDetails.seats_max) * 100;

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      <div className="max-w-2xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">{orgDetails.name}</h1>
          <p className="text-gray-400">Organization Settings</p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 mb-6 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="bg-green-900/20 border border-green-700 rounded-lg p-4 mb-6 text-green-400 text-sm">
            {success}
          </div>
        )}

        {/* Subscription Info */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-4">Subscription</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-400">Plan</p>
              <p className="text-white font-semibold capitalize">{orgDetails.plan}</p>
            </div>
            <div>
              <p className="text-sm text-gray-400">Organization ID</p>
              <p className="text-white font-mono text-sm">{orgDetails.org_id}</p>
            </div>
            <div>
              <p className="text-sm text-gray-400">Created</p>
              <p className="text-white">{new Date(orgDetails.created_at).toLocaleDateString()}</p>
            </div>
            <div>
              <p className="text-sm text-gray-400">Owner ID</p>
              <p className="text-white font-mono text-sm">{orgDetails.owner_user_id}</p>
            </div>
          </div>
        </div>

        {/* Quota Usage */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-4">Monthly Quota</h2>
          <div className="mb-2 flex justify-between items-center">
            <span className="text-sm text-gray-400">Repositories Ingested</span>
            <span className="text-white font-semibold">
              {orgDetails.repos_ingested_this_month} / {orgDetails.ingestion_quota_monthly}
            </span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all ${
                quotaPercentage > 90
                  ? 'bg-red-500'
                  : quotaPercentage > 70
                  ? 'bg-yellow-500'
                  : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(quotaPercentage, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-2">
            {orgDetails.ingestion_quota_monthly - orgDetails.repos_ingested_this_month} repos remaining this month
          </p>
        </div>

        {/* Team Members */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-4">Team Members</h2>
          
          {/* Seats Usage */}
          <div className="mb-4 pb-4 border-b border-gray-700">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-400">Seats Used</span>
              <span className="text-white font-semibold">
                {orgDetails.member_count} / {orgDetails.seats_max}
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full transition-all ${
                  seatsPercentage > 90
                    ? 'bg-red-500'
                    : seatsPercentage > 70
                    ? 'bg-yellow-500'
                    : 'bg-blue-500'
                }`}
                style={{ width: `${Math.min(seatsPercentage, 100)}%` }}
              />
            </div>
          </div>

          {/* Invite Form */}
          <form onSubmit={handleInviteMember} className="mb-6">
            <label className="block text-sm text-gray-400 mb-2">Invite New Member</label>
            <div className="flex gap-2">
              <input
                type="email"
                placeholder="member@company.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                disabled={inviting}
                className="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
              <button
                type="submit"
                disabled={inviting || orgDetails.member_count >= orgDetails.seats_max}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-white text-sm font-medium transition"
              >
                {inviting ? "Inviting..." : "Invite"}
              </button>
            </div>
            {orgDetails.member_count >= orgDetails.seats_max && (
              <p className="text-xs text-yellow-400 mt-2">
                Seat limit reached. Upgrade your plan to invite more members.
              </p>
            )}
          </form>

          {/* Members List */}
          <div className="space-y-2">
            <p className="text-sm text-gray-400 mb-3">Active Members</p>
            <div className="bg-gray-900/50 rounded-lg p-3 text-sm text-gray-300">
              <p>👤 Owner Account</p>
              <p className="text-xs text-gray-500">ID: {orgDetails.owner_user_id}</p>
            </div>
            {orgDetails.member_count > 1 && (
              <p className="text-xs text-gray-400 mt-2">
                +{orgDetails.member_count - 1} team member{orgDetails.member_count - 1 !== 1 ? 's' : ''}
              </p>
            )}
          </div>
        </div>

        {/* Upgrade Section */}
        {seatsPercentage > 80 && (
          <div className="bg-blue-900/20 border border-blue-700 rounded-xl p-6">
            <div className="flex items-start gap-4">
              <div className="flex-1">
                <h3 className="text-white font-semibold mb-2">Need more seats?</h3>
                <p className="text-sm text-blue-300">
                  Upgrade your plan to add more team members and increase your monthly ingestion quota.
                </p>
              </div>
              <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm font-medium whitespace-nowrap transition">
                Upgrade Plan
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrgSettings;
