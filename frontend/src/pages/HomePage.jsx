import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

// --- THE DEFINITIVE FIX ---
// Define the absolute base URL for the backend API.
// This bypasses the Vite proxy, which can be unreliable for long-running requests.
const API_BASE_URL = 'http://localhost:8000';
// --- END OF FIX ---

function HomePage() {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([
    { from: 'bot', text: 'Hello! Ask me anything about the content I have ingested.' }
  ]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Effect to scroll to the bottom of the chat on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault(); // Prevent form from refreshing the page
    if (!query.trim() || loading) return;

    const userMessage = { from: 'user', text: query };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    setQuery('');

    try {
      // Use the absolute URL to make a direct request to the backend.
      // The backend must have CORS enabled to accept this request.
      const response = await axios.post(`${API_BASE_URL}/api/chat`, { query: userMessage.text });
      
      const botMessage = {
        from: 'bot',
        text: response.data.answer,
        sources: response.data.sources || [] // Attach sources if they exist
      };
      setMessages(prev => [...prev, botMessage]);

    } catch (error) {
      const errorMessage = {
        from: 'bot',
        text: 'Sorry, something went wrong. Please try again. (Is the backend server running and reachable?)'
      };
      setMessages(prev => [...prev, errorMessage]);
      console.error("Error fetching chat response:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[85vh] bg-white rounded-lg shadow-md">
      {/* Message Display Area */}
      <div className="flex-1 p-4 overflow-y-auto">
        <div className="flex flex-col space-y-4">
          {messages.map((msg, index) => (
            <div key={index} className={`flex ${msg.from === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-lg p-3 rounded-2xl ${msg.from === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-800'}`}>
                <p style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</p>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-300">
                    <h4 className="text-xs font-bold mb-1">Sources:</h4>
                    {msg.sources.map((source, idx) => (
                      <a 
                        key={idx} 
                        href={source.meta.page_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="block text-xs truncate hover:underline"
                      >
                        {source.meta.title || source.meta.page_url}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="max-w-lg p-3 rounded-2xl bg-gray-200 text-gray-500">
                Thinking...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Form */}
      <div className="p-4 border-t border-gray-200">
        <form onSubmit={handleSend} className="flex space-x-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            type="submit"
            className="px-4 py-2 bg-blue-500 text-white font-semibold rounded-lg hover:bg-blue-600 disabled:bg-blue-300"
            disabled={loading}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

export default HomePage;