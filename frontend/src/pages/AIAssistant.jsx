import React, { useState, useEffect, useCallback, useImperativeHandle, forwardRef } from 'react';
import ChatWindow from '../components/ChatWindow';
import ChatInput from '../components/ChatInput';
import { 
  sendMessage, 
  getDocuments, 
  getSessionDetail, 
  deleteSession 
} from '../services/api';

const AIAssistant = forwardRef((props, ref) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasDocs, setHasDocs] = useState(true);
  const [inputValue, setInputValue] = useState('');
  
  const [activeSessionId, setActiveSessionId] = useState(null);

  useImperativeHandle(ref, () => ({
    handleNewChat,
    handleSelectSession,
    handleDeleteSession
  }));

  useEffect(() => {
    const checkDocs = async () => {
      try {
        const data = await getDocuments();
        setHasDocs(data.documents && data.documents.length > 0);
      } catch (err) {
        console.error('Error checking documents:', err);
      }
    };
    checkDocs();
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      const loadSession = async () => {
        setIsLoading(true);
        try {
          const data = await getSessionDetail(activeSessionId);
          setMessages(data.messages || []);
        } catch (err) {
          setError('Failed to load chat history.');
          console.error(err);
        } finally {
          setIsLoading(false);
        }
      };
      loadSession();
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);

  const handleSend = async (question) => {
    if (!question.trim() || isLoading) return;
    setError(null);
    const userMessage = { id: Date.now(), role: 'user', content: question, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setInputValue('');
    try {
      const data = await sendMessage(question, activeSessionId);
      const assistantMessage = { id: Date.now() + 1, role: 'assistant', content: data.answer, sources: data.sources, timestamp: new Date().toISOString() };
      setMessages((prev) => [...prev, assistantMessage]);
      if (!activeSessionId && data.session_id) setActiveSessionId(data.session_id);
      if (props.fetchSessions) props.fetchSessions();
    } catch (err) {
      setError(err.message || 'Something went wrong.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestion = (suggestion) => {
    setInputValue(suggestion);
  };

  const handleNewChat = () => { setActiveSessionId(null); setMessages([]); setError(null); setInputValue(''); };
  const handleSelectSession = (sessionId) => { setActiveSessionId(sessionId); setError(null); setInputValue(''); };
  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteSession(sessionId);
      if (activeSessionId === sessionId) handleNewChat();
      if (props.fetchSessions) props.fetchSessions();
    } catch (err) {
      setError('Failed to delete session.');
    }
  };

  return (
    <div className='flex-1 flex flex-col min-w-0 bg-white h-full overflow-hidden'>
      <ChatWindow 
        messages={messages} 
        isLoading={isLoading} 
        onSuggestion={handleSuggestion}
      />
      <div className='p-4 bg-white border-t border-slate-100'>
        <ChatInput 
          onSend={handleSend} 
          disabled={isLoading || !hasDocs} 
          value={inputValue}
          onChange={setInputValue}
        />
        {!hasDocs && <p className='text-center text-xs text-red-500 mt-2 font-semibold animate-pulse'>⚠️ Knowledge base is empty.</p>}
        {error && <p className='text-center text-xs text-red-400 mt-2 font-medium bg-red-50 py-1 rounded-lg'>{error}</p>}
      </div>
    </div>
  );
});

export default AIAssistant;
