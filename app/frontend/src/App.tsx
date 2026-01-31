import { useState } from 'react';

function App () {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<{ role: string, text: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [repoUrl, setRepoUrl] = useState("")

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
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: "ai", text: "Error cloning repo." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-gray-900 text-white flex flex-col items-center p-10">
      <h1 className="text-3xl font-bold mb-8 text-blue-400">InfraLens</h1>
      
      <div className="w-full max-w-2xl mb-6 flex gap-2">
        <input 
          type="text" 
          placeholder="paste github repo URL"
          className="flex-1 p-2 rounded bg-gray-800 border border-gray-600 text-sm"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
        />
        <button 
          onClick={handleIngest}
          disabled={loading}
          className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded text-sm font-bold"
        >
          Load Repo
        </button>
      </div>

      {/* chat area */}
      <div className="w-full max-w-2xl bg-gray-800 rounded-lg p-6 h-125 overflow-y-auto flex flex-col gap-4 border border-gray-700">
        {messages.length === 0 && (
          <p className="text-gray-500 text-center mt-10">Ask me about your infrastructure...</p>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`p-3 rounded-lg max-w-[80%] ${
            msg.role === "user" 
              ? "bg-blue-600 self-end" 
              : "bg-gray-700 self-start border border-gray-600"
          }`}>
            <p className="text-sm">{msg.text}</p>
          </div>
        ))}
        
        {loading && <p className="text-gray-400 text-sm animate-pulse">Analysing...</p>}
      </div>

      {/* input area */}
      <div className="w-full max-w-2xl mt-4 flex gap-2">
        <input 
          type="text" 
          className="flex-1 p-3 rounded bg-gray-800 border border-gray-700 text-white focus:outline-none focus:border-blue-500"
          placeholder="Type a message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button 
          onClick={sendMessage}
          className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded font-bold transition-colors"
          disabled={loading}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default App;