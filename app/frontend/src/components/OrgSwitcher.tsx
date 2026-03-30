import { useOrganization, useOrganizationList, useClerk } from '@clerk/clerk-react';
import { useState, useEffect } from 'react';

interface OrgSwitcherProps {
  onOrgChange?: (orgId: string | null) => void;
  className?: string;
}

export const OrgSwitcher = ({ onOrgChange, className = "" }: OrgSwitcherProps) => {
  const { organization } = useOrganization();
  const { userMemberships } = useOrganizationList({ userMemberships: true });
  const { setActive } = useClerk();
  const [isOpen, setIsOpen] = useState(false);

  // sync local state with Clerk org changes and persist to localStorage
  useEffect(() => {
    const orgId = organization?.id || null;
    localStorage.setItem('activeOrgId', orgId || 'personal');
    onOrgChange?.(orgId);
  }, [organization, onOrgChange]);

  const handleSwitchOrg = async (orgId: string | null) => {
    try {
      if (orgId === null) {
        // switch to personal workspace
        await setActive({ 
          session: window.location.href.includes('session') ? null : undefined,
          organization: null 
        });
        
        localStorage.setItem('activeOrgId', 'personal');
        setIsOpen(false);
        
        // Force UI update
        onOrgChange?.(null);
        window.location.reload();  
        return;
      }

      // Switch to organization
      await setActive({ organization: orgId });
      localStorage.setItem('activeOrgId', orgId);
      setIsOpen(false);
      onOrgChange?.(orgId);
      window.location.reload();  
    } catch (error) {
      console.error("Failed to switch organization:", error);
    }
  };

  const currentWorkspace = organization?.name || "Personal";
  const currentRole = organization ? "Member" : null;

  return (
    <div className={`relative ${className}`}>
      {/* Workspace Badge */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-700 bg-gray-800 hover:bg-gray-700 transition"
      >
        <div className="flex flex-col items-start">
          <span className="text-xs text-gray-400">Workspace</span>
          <span className="text-sm font-semibold text-white">{currentWorkspace}</span>
        </div>
        
        {/* Dropdown Arrow */}
        <svg
          className={`w-4 h-4 text-gray-400 transition ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 14l-7 7m0 0l-7-7m7 7V3"
          />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-56 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50">
          {/* Personal Workspace */}
          <button
            onClick={() => handleSwitchOrg(null)}
            className={`w-full text-left px-4 py-3 hover:bg-gray-800 transition flex items-center justify-between ${
              !organization ? "bg-blue-900/30 border-l-2 border-blue-500" : ""
            }`}
          >
            <div>
              <div className="text-sm font-medium text-white">Personal</div>
              <div className="text-xs text-gray-400">Your personal workspace</div>
            </div>
            {!organization && (
              <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            )}
          </button>

          {/* Divider */}
          {userMemberships?.data && userMemberships.data.length > 0 && (
            <div className="border-t border-gray-700" />
          )}

          {/* Organization Workspaces */}
          {userMemberships?.data?.map((membership) => (
            <button
              key={membership.organization.id}
              onClick={() => handleSwitchOrg(membership.organization.id)}
              className={`w-full text-left px-4 py-3 hover:bg-gray-800 transition flex items-center justify-between ${
                organization?.id === membership.organization.id
                  ? "bg-blue-900/30 border-l-2 border-blue-500"
                  : ""
              }`}
            >
              <div>
                <div className="text-sm font-medium text-white">
                  {membership.organization.name}
                </div>
                <div className="text-xs text-gray-400 capitalize">
                  {membership.role}
                </div>
              </div>
              {organization?.id === membership.organization.id && (
                <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </button>
          ))}

          {/* Empty State */}
          {(!userMemberships?.data || userMemberships.data.length === 0) && (
            <div className="px-4 py-3 text-sm text-gray-400">
              No organizations yet. Create one to collaborate with your team!
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default OrgSwitcher;
