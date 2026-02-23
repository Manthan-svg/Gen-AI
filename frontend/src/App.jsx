import React, { useState } from 'react';
import axios from 'axios';
import { Send, Upload, FileText } from 'lucide-react';

function App() {
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append('file', file);
    await axios.post('http://127.0.0.1:2020/upload', formData);
    alert("File uploaded and ingested!");
  };

  const askQuestion = async () => {
    if (!question) return;
    setLoading(true);
    const userMsg = { role: 'user', text: question };
    setChat([...chat, userMsg]);

    const res = await axios.post('http://127.0.0.1:2020/get-answer', { question });
    const aiMsg = { role: 'ai', text: res.data.answer, sources: res.data.sources };
    
    setChat((prev) => [...prev, aiMsg]);
    setQuestion("");
    setLoading(false);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-gray-900">
      {/* Sidebar / Header */}
      <header className="p-4 bg-white border-b flex justify-between items-center">
        <h1 className="text-xl font-bold">DeepContext</h1>
        <label className="cursor-pointer bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2">
          <Upload size={18} /> Upload <input type="file" hidden onChange={handleUpload} />
        </label>
      </header>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {chat.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-2xl p-4 rounded-2xl ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white border'}`}>
              <p>{msg.text}</p>
              {msg.sources && (
                <div className="mt-2 text-xs opacity-70 flex gap-1">
                  <FileText size={12} /> Sources: {msg.sources.join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input Bar */}
      <div className="p-4 bg-white border-t">
        <div className="max-w-3xl mx-auto flex gap-2">
          <input 
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="flex-1 border rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Ask your team's knowledge..."
          />
          <button onClick={askQuestion} className="bg-blue-600 text-white p-2 rounded-xl">
            <Send />
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;