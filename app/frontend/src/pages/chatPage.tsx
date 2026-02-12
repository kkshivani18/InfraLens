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
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  useEffect(() => {
    if (location.state?.repoName) {
      const newRepoName = location.state.repoName;
      
      // clear msgs when switching to diff repo
      if (newRepoName !== repoName) {
        setMessages([]);
      }
      
      setRepoName(newRepoName);
      loadChatHistory(newRepoName);
    }
  }, [location.state?.repoName]);

  const loadChatHistory = async (repositoryName: string) => {
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      const token = await getToken();
      const data = await chatService.getChatHistory(repositoryName, token);
      
      console.log('Chat history response:', data);
      
      if (data.messages && data.messages.length > 0) {
        const formattedMessages = data.messages.map((msg: any) => ({
          role: msg.role,
          text: msg.content
        }));
        setMessages(formattedMessages);
        console.log(`Loaded ${formattedMessages.length} messages for ${repositoryName}`);
      } else {
        console.log(`No chat history found for ${repositoryName}`);
        setMessages([]);
      }
    } catch (error) {
      console.error("Failed to load chat history:", error);
      setHistoryError("Failed to load chat history");
      setMessages([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { role: "user", text: input};
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    const currentInput = input; 
    setInput(""); 

    try {
      const token = await getToken();
      
      const data = await chatService.sendMessage(currentInput, token, repoName || undefined);

      // add AI resp to UI
      const AImsg = { role: "ai", text: data.response}
      setMessages(prev => [...prev, AImsg]);
    } catch (error) {
      console.error("Error connecting to backend:", error);
      const errorMsg = { role: "assistant", text: "Error: Could not connect to backend." };
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
      
      {loadingHistory ? (
        <div className="flex items-center justify-center flex-1">
          <div className="text-gray-400">Loading chat history...</div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {historyError && (
            <div className="flex justify-center">
              <div className="bg-red-900/20 border border-red-700 rounded-lg px-4 py-2 text-red-400 text-sm">
                {historyError}
              </div>
            </div>
          )}
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full text-gray-500">
              {repoName 
                ? "Start a conversation about the repository" 
                : "Select a repository to start chatting"
              }
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${msg.role === "user" ? "bg-blue-600" : "bg-gray-800"}`}>
                <pre className="whitespace-pre-wrap font-sans">{msg.text}</pre>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 rounded-2xl px-5 py-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      
      <div className="p-6">
        <input 
          className="w-full bg-gray-800 p-4 rounded-xl border border-gray-700 focus:border-blue-500 focus:outline-none" 
          placeholder={repoName ? "Ask anything about the repository's code..." : "Select a repository first..."}
          value={input} 
          onChange={(e) => setInput(e.target.value)} 
          onKeyDown={(e) => e.key === 'Enter' && !loading && sendMessage()}
          disabled={!repoName || loading}
        />
      </div>
    </div>
  );
};

export default ChatPage;