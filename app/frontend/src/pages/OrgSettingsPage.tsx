import { OrgSettings } from '../components/OrgSettings';

const OrgSettingsPage = () => {
  return (
    <div className="flex flex-col h-full p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">Organization Settings</h2>
        <p className="text-gray-400 mt-2">Manage your organization members and settings</p>
      </div>
      <div className="flex-1 min-h-0">
        <OrgSettings />
      </div>
    </div>
  );
};

export default OrgSettingsPage;
