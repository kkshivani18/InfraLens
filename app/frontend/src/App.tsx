import { useState } from 'react';

function App () {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<{ role: string, text: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [repoUrl, setRepoUrl] = useState("")
  const [activeView, setActiveView] = useState("chat");

  const sendMessage = async () => {
    if (!input) return;

    // add user msg to UI
    const userMsg = { role: "user", text: input};
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    const currentInput = input; 
    setInput(""); 

    try {
      // call fastapi backend
      const response = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json"},
        body: JSON.stringify({message: currentInput}),
      });

      const data = await response.json()

      // add AI resp to UI
      const AImsg = { role: "ai", text: data.response}
      setMessages(prev => [...prev, AImsg]);
    } catch (error) {
      console.error("Error connecting to backend:", error);
      const errorMsg = { role: "ai", text: "Error: Could not connect to backend." };
      setMessages(prev => [...prev, userMsg, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleIngest = async () => {
    if (!repoUrl) return;
    setLoading(true);
    const statusMsg = { role: "ai", text: `Cloning ${repoUrl}` };
    setMessages(prev => [...prev, statusMsg]);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl }),
      });
      const data = await response.json();
      
      const successMsg = { 
        role: "ai", 
        text: `Success! I read ${data.files_processed} files. You can now chat with the codebase.` 
      };
      setMessages(prev => [...prev, successMsg]);
      // Switch to chat view on success
      setActiveView('chat');
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: "ai", text: "Error cloning repo." }]);
    } finally {
      setLoading(false);
    }
  };

  const SidebarButton = ({ view, label, icon }: { view: string, label: string, icon?: React.ReactNode }) => (
    <button 
      onClick={() => setActiveView(view)}
      className={`w-full text-left px-4 py-3 rounded flex items-center gap-3 transition-colors ${
        activeView === view 
          ? "bg-blue-600 text-white" 
          : "text-gray-400 hover:bg-gray-800 hover:text-white"
      }`}
    >
      <span className="text-lg">{icon || "⬜"}</span>
      <span>{label}</span>
    </button>
  );

  return (
    <div className="flex h-screen w-full bg-gray-950 text-white overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col p-4">
        <div className="mb-8 px-2">
          {/* Logo or similar could go here, keeping it empty as per sketch's sidebar */}
        </div>
        
        <nav className="flex flex-col gap-2">
          <SidebarButton view="chat" label="AI Assistant" icon="💬" />
          <SidebarButton view="repos" label="Cloned Repos" icon="📂" />
          <SidebarButton view="current-repo" label="Current Repo" icon="📄" />
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 bg-gray-900">
        
        {/* Header */}
        <header className="h-16 border-b border-gray-800 flex items-center px-6">
          <h1 className="text-xl font-semibold tracking-wide text-white">InfraLens</h1>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden relative flex flex-col">
          
          {activeView === 'chat' && (
            <>
              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
                {messages.length === 0 && (
                  <div className="h-full flex flex-col items-center justify-center text-gray-500 opacity-50">
                     <p className="text-lg">Ask me about your infrastructure...</p>
                  </div>
                )}
                
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                      msg.role === "user" 
                        ? "bg-blue-600 text-white rounded-br-none" 
                        : "bg-gray-800 border border-gray-700 text-gray-200 rounded-bl-none"
                    }`}>
                      {msg.text}
                    </div>
                  </div>
                ))}
                {loading && (
                   <div className="flex justify-start">
                      <div className="bg-gray-800 border border-gray-700 text-gray-400 px-5 py-3 rounded-2xl rounded-bl-none animate-pulse">
                         Thinking...
                      </div>
                   </div>
                )}
              </div>

              {/* Input Area */}
              <div className="p-6 pt-2">
                <div className="relative">
                  <input 
                    type="text" 
                    placeholder="Type a message..."
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-xl py-4 pl-5 pr-20 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-500"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                  />
                  <button 
                    onClick={sendMessage}
                    disabled={loading || !input}
                    className="absolute right-2 top-2 bottom-2 bg-blue-600 hover:bg-blue-700 text-white px-4 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Send
                  </button>
                </div>
              </div>
            </>
          )}

          {activeView === 'current-repo' && (
            <div className="flex-1 flex flex-col items-center justify-center p-10">
               <div className="w-full max-w-xl bg-gray-800 p-8 rounded-xl border border-gray-700">
                  <h2 className="text-2xl font-bold mb-6 text-white">Load Repository</h2>
                  <div className="flex flex-col gap-4">
                    <label className="text-gray-400 text-sm">GitHub Repository URL</label>
                    <input 
                      type="text" 
                      placeholder="https://github.com/username/repo"
                      className="w-full p-3 rounded bg-gray-900 border border-gray-600 text-white focus:border-blue-500 focus:outline-none"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                    />
                    <button 
                      onClick={handleIngest}
                      disabled={loading}
                      className="mt-2 w-full bg-green-600 hover:bg-green-700 py-3 rounded font-bold transition-colors disabled:opacity-50"
                    >
                      {loading ? "Cloning..." : "Load Repo"}
                    </button>
                  </div>
               </div>
            </div>
          )}

          {activeView === 'repos' && (
            <div className="flex-1 p-10">
              <h2 className="text-2xl font-bold mb-6 text-white">Cloned Repositories</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                 {/* Placeholder for repos list */}
                 <div className="bg-gray-800 p-4 rounded border border-gray-700 text-gray-400">
                    No repositories cloned yet.
                 </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}

export default App;