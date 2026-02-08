import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '@clerk/clerk-react';
import { chatService } from '../services/api';

const ChatPage = () => {
  const location = useLocation();
  const { getToken } = useAuth();
  const [repoName, setRepoName] = useState<string | null>(null);
  const [messages, setMessages] = useState<{ role: string, text: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (location.state?.repoName) {
      setRepoName(location.state.repoName);
    }
  }, [location.state]);

  const sendMessage = async () => {
    if (!input) return;

    // add user msg to UI
    const userMsg = { role: "user", text: input};
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    const currentInput = input; 
    setInput(""); 

    try {
      const token = await getToken();
      
      // call fastapi backend
      const data = await chatService.sendMessage(currentInput, token);

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

  return (
    <div className="flex flex-col h-full">
      {repoName && (
        <div className="flex justify-center pt-4 pb-2">
          <div className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2">
            <span className="text-sm text-gray-400">Repository: </span>
            <span className="text-sm font-semibold text-blue-400">{repoName}</span>
          </div>
        </div>
      )}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${msg.role === "user" ? "bg-blue-600" : "bg-gray-800"}`}>
              {msg.text}
            </div>
          </div>
        ))}
      </div>
      <div className="p-6">
        <input 
          className="w-full bg-gray-800 p-4 rounded-xl" 
          value={input} 
          onChange={(e) => setInput(e.target.value)} 
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
        />
      </div>
    </div>
  );
};

export default ChatPage;