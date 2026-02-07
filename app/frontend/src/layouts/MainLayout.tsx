import { Outlet, Link, useLocation } from 'react-router-dom';

const MainLayout = () => {
  const { pathname } = useLocation();

  const navItems = [
    { path: '/chat', label: 'AI Assistant', icon: '💬' },
    { path: '/repos', label: 'Cloned Repositories', icon: '📂' },
    { path: '/add', label: 'Add Repository', icon: '➕' },
  ];

  return (
    <div className="flex h-screen w-full bg-gray-950 text-white overflow-hidden">
      <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col p-4">
        <nav className="flex flex-col gap-2 mt-8">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`w-full px-4 py-3 rounded flex items-center gap-3 transition-colors ${
                pathname === item.path ? "bg-blue-600 text-white" : "text-gray-400 hover:bg-gray-800"
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex-1 flex flex-col bg-gray-900">
        <header className="h-16 border-b border-gray-800 flex items-center px-6">
          <h1 className="text-xl font-semibold">InfraLens</h1>
        </header>
        <div className="flex-1 overflow-hidden relative">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default MainLayout;