'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import { chatAPI, feedbackAPI, contextAPI, messagesAPI } from '@/lib/api';
import { v4 as uuidv4 } from 'uuid';
import ContextPanel from './ContextPanel';
import ExplanationPanel from './ExplanationPanel';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  responseId?: string;
  candidateId?: string;
  recommendation?: any; // Store recommendation data for detailed explanation
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [candidateId, setCandidateId] = useState('');
  const [sessionId] = useState(() => uuidv4());
  const [loading, setLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [currentResponseId, setCurrentResponseId] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [selectedRecommendation, setSelectedRecommendation] = useState<any>(null);
  const [activeCandidates, setActiveCandidates] = useState<Array<{ candidate_id?: string; candidateId?: string }>>([]);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [messageOffset, setMessageOffset] = useState(0);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const lastFetchedUserEmailRef = useRef<string | null>(null);
  const { user, logout } = useAuthStore();
  const router = useRouter();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  // Load message history on mount (all user messages, not per candidate)
  useEffect(() => {
    const loadMessageHistory = async () => {
      if (!user?.email || loadingMessages) return;
      
      setLoadingMessages(true);
      
      try {
        // Get all messages for this user
        const response = await messagesAPI.getAllMessages(50);
        
        // Convert backend messages to frontend format
        const historyMessages: Message[] = response.messages.flatMap((msg) => [
          {
            id: msg.request_id,
            role: 'user' as const,
            content: msg.message,
            timestamp: new Date(msg.timestamp),
            candidateId: msg.candidate_id || undefined
          },
          {
            id: `${msg.request_id}-response`,
            role: 'assistant' as const,
            content: msg.response,
            timestamp: new Date(msg.timestamp),
            candidateId: msg.candidate_id || undefined
          }
        ]);
        
        // Sort by timestamp (oldest first)
        historyMessages.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
        
        // Set messages
        setMessages(historyMessages);
        setHasMoreMessages(false); // For now, load all at once
      } catch (error) {
        console.error('Failed to load message history:', error);
      } finally {
        setLoadingMessages(false);
      }
    };
    
    loadMessageHistory();
  }, [user?.email]);

  // Fetch current candidate and active candidates on mount
  useEffect(() => {
    const userEmail = user?.email;
    if (userEmail && lastFetchedUserEmailRef.current !== userEmail) {
      lastFetchedUserEmailRef.current = userEmail;
      const fetchCurrentCandidate = async () => {
        try {
          const data = await contextAPI.getCurrentCandidate();
          if (data.candidate_id) {
            setCandidateId(data.candidate_id);
          }
        } catch (error) {
          console.error('Failed to fetch current candidate:', error);
        }
      };
      fetchCurrentCandidate();
    }
  }, [user?.email]);

  // Fetch active candidates
  useEffect(() => {
    const fetchActiveCandidates = async () => {
      try {
        const data = await contextAPI.getCandidates('active');
        // Handle both response formats: {candidates: [...]} or just array
        const candidates = data.candidates || (Array.isArray(data) ? data : []);
        if (Array.isArray(candidates)) {
          setActiveCandidates(candidates);
        }
      } catch (error) {
        console.error('Failed to fetch active candidates:', error);
      }
    };
    if (user?.email) {
      fetchActiveCandidates();
    }
  }, [user?.email, candidateId]); // Refresh when candidateId changes

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

          setMessages((prev) => {
            // Deduplicate by checking if message already exists
            const exists = prev.find(m => 
              m.role === 'user' && 
              m.content === input && 
              Math.abs(m.timestamp.getTime() - new Date().getTime()) < 1000
            );
            if (exists) return prev;
            return [...prev, userMessage];
          });
    setInput('');
    setLoading(true);
    setStreamingMessage('');
    setCurrentResponseId(null);
    setProcessingStatus(null);

    let assistantMessageId = uuidv4();
    let finalContent = '';
    let finalResponseId: string | null = null;
    let finalCandidateId: string | null = null;
    let finalRecommendation: any = null;

    try {
      const cleanup = await chatAPI.streamChat(
        {
          message: input,
          candidate_id: candidateId || undefined,
          session_id: sessionId,
        },
        (data) => {
          if (data.type === 'response') {
            // Parse content - should be clean text now (no JSON)
            let contentToDisplay = data.content;
            let recommendationData = null;

            // Check if recommendation data is included separately
            if (data.recommendation) {
              recommendationData = data.recommendation;
            } else {
              // Fallback: try to parse if it's still JSON (for backward compatibility)
              try {
                const parsed = JSON.parse(data.content);
                if (parsed.response_text) {
                  contentToDisplay = parsed.response_text;
                }
                if (parsed.recommendation || parsed.status === 'approved') {
                  recommendationData = parsed;
                }
              } catch (e) {
                // Not JSON, use as-is
                contentToDisplay = data.content;
              }
            }

            finalContent = contentToDisplay;
            finalResponseId = data.response_id;
            setStreamingMessage(contentToDisplay);
            setCurrentResponseId(data.response_id);
            setProcessingStatus(null); // Clear processing status when final response arrives
            // Only update candidate ID if provided and different (means it's active)
            if (data.candidate_id && data.candidate_id !== candidateId) {
              setCandidateId(data.candidate_id);
              // Refresh active candidates list
              const fetchActiveCandidates = async () => {
                try {
                  const data = await contextAPI.getCandidates('active');
                  const candidates = data.candidates || (Array.isArray(data) ? data : []);
                  if (Array.isArray(candidates)) {
                    setActiveCandidates(candidates);
                  }
                } catch (error) {
                  console.error('Failed to fetch active candidates:', error);
                }
              };
              fetchActiveCandidates();
            } else if (!data.candidate_id && candidateId) {
              // Candidate was closed, clear it
              setCandidateId('');
              // Refresh active candidates list
              const fetchActiveCandidates = async () => {
                try {
                  const data = await contextAPI.getCandidates('active');
                  const candidates = data.candidates || (Array.isArray(data) ? data : []);
                  if (Array.isArray(candidates)) {
                    setActiveCandidates(candidates);
                  }
                } catch (error) {
                  console.error('Failed to fetch active candidates:', error);
                }
              };
              fetchActiveCandidates();
            }

            // Store candidate ID and recommendation for explanation
            finalCandidateId = data.candidate_id || candidateId;
            finalRecommendation = recommendationData;
          } else if (data.type === 'processing') {
            // Show continuous feedback for each processing stage
            if (data.message) {
              setProcessingStatus(data.message);
            }
            // Update candidate ID if extracted during processing
            if (data.candidate_id && data.candidate_id !== candidateId) {
              setCandidateId(data.candidate_id);
            }
          }
        },
        (error) => {
          console.error('Stream error:', error);
          setMessages((prev) => [...prev, {
            id: uuidv4(),
            role: 'assistant',
            content: 'I encountered an error processing your request. Please try again.',
            timestamp: new Date(),
          }]);
          setLoading(false);
          setStreamingMessage('');
        }
      );

      // Wait for streaming to complete (check every 500ms)
      const checkInterval = setInterval(() => {
        if (finalContent && !loading) {
          const message: Message = {
            id: assistantMessageId,
            role: 'assistant',
            content: finalContent,
            timestamp: new Date(),
            responseId: finalResponseId || undefined,
            candidateId: finalCandidateId || undefined,
            recommendation: finalRecommendation || undefined, // Store recommendation for explanation
          };
          setMessages((prev) => {
            // Check if message already exists (deduplicate)
            const exists = prev.find(m => 
              m.id === assistantMessageId || 
              (m.responseId === finalResponseId && finalResponseId)
            );
            if (exists) return prev;
            return [...prev, message];
          });
          setStreamingMessage('');
          setCurrentResponseId(null);
          setProcessingStatus(null);
          setLoading(false);
          clearInterval(checkInterval);
          cleanup();
        }
      }, 500);

      // Fallback timeout
      setTimeout(() => {
        if (finalContent) {
          const message: Message = {
            id: assistantMessageId,
            role: 'assistant',
            content: finalContent,
            timestamp: new Date(),
            responseId: finalResponseId || undefined,
          };
          setMessages((prev) => {
            // Deduplicate
            const exists = prev.find(m => m.id === assistantMessageId);
            if (exists) return prev;
            return [...prev, message];
          });
        }
        setStreamingMessage('');
        setCurrentResponseId(null);
        setProcessingStatus(null);
        setLoading(false);
        clearInterval(checkInterval);
        cleanup();
      }, 10000);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) => [...prev, {
        id: uuidv4(),
        role: 'assistant',
        content: 'I encountered an error. Please try again.',
        timestamp: new Date(),
      }]);
      setLoading(false);
      setStreamingMessage('');
      setProcessingStatus(null);
    }
  };

  const handleFeedback = async (messageId: string, type: 'thumbs_down' | 'report_error', comment?: string) => {
    const message = messages.find((m) => m.id === messageId);
    if (!message?.responseId) return;

    try {
      await feedbackAPI.submitFeedback({
        response_id: message.responseId,
        feedback_type: type,
        comment,
        candidate_id: candidateId || undefined,
      });
      alert('Thank you for your feedback!');
    } catch (error) {
      console.error('Feedback error:', error);
      alert('Failed to submit feedback. Please try again.');
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  const handleCandidateSwitch = async (newCandidateId: string) => {
    if (newCandidateId === candidateId) return;

    if (!newCandidateId) {
      // If empty selection, just clear
      setCandidateId('');
      setMessages([]);
      setHasMoreMessages(false);
      setMessageOffset(0);
      return;
    }

    try {
      // Clear current messages and reset pagination
      setMessages([]);
      setHasMoreMessages(false);
      setMessageOffset(0);
      
      // Switch candidate by sending /switch command
      setInput(`/switch ${newCandidateId}`);
      setTimeout(() => {
        handleSend();
        setCandidateId(newCandidateId);
        // Refresh active candidates after switch
        const fetchActiveCandidates = async () => {
          try {
            const data = await contextAPI.getCandidates('active');
            const candidates = data.candidates || (Array.isArray(data) ? data : []);
            if (Array.isArray(candidates)) {
              setActiveCandidates(candidates);
            }
          } catch (error) {
            console.error('Failed to fetch active candidates:', error);
          }
        };
        fetchActiveCandidates();
      }, 100);
    } catch (error) {
      console.error('Failed to switch candidate:', error);
    }
  };

  // Load more messages when scrolling to top
  const handleScrollUp = async () => {
    if (!candidateId || !hasMoreMessages || loadingMessages) return;
    
    setLoadingMessages(true);
    const newOffset = messageOffset + 10;
    
    try {
      const response = await messagesAPI.getMessages(candidateId, 10, newOffset);
      
      if (response.messages.length > 0) {
        // Convert backend messages to frontend format
        const newMessages: Message[] = response.messages.map((msg) => ({
          id: msg.request_id,
          role: 'user' as const,
          content: msg.message,
          timestamp: new Date(msg.timestamp),
          candidateId: msg.candidate_id
        })).concat(
          response.messages.map((msg) => ({
            id: `${msg.request_id}-response`,
            role: 'assistant' as const,
            content: msg.response,
            timestamp: new Date(msg.timestamp),
            candidateId: msg.candidate_id
          }))
        );
        
        // Sort by timestamp (oldest first)
        newMessages.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
        
        // Prepend to existing messages
        setMessages((prev) => {
          // Deduplicate by ID
          const existingIds = new Set(prev.map(m => m.id));
          const uniqueNew = newMessages.filter(m => !existingIds.has(m.id));
          return [...uniqueNew, ...prev].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
        });
        
        setMessageOffset(newOffset);
        setHasMoreMessages(response.offset + response.messages.length < response.total);
      } else {
        setHasMoreMessages(false);
      }
    } catch (error) {
      console.error('Failed to load more messages:', error);
    } finally {
      setLoadingMessages(false);
    }
  };

  // Scroll detection for loading more messages
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container || !hasMoreMessages || loadingMessages) return;

    let isLoading = false;
    const handleScroll = () => {
      // If scrolled to top (within 100px), load more
      if (container.scrollTop < 100 && !isLoading) {
        isLoading = true;
        handleScrollUp().finally(() => {
          isLoading = false;
        });
      }
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [candidateId, hasMoreMessages, loadingMessages, messageOffset]);

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Main Chat Area */}
      <div className="flex flex-col flex-1">
        {/* Header */}
        <header className="bg-white/95 backdrop-blur-sm shadow-soft border-b border-gray-200 px-8 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-primary-600 to-indigo-600 bg-clip-text text-transparent">
                  Compensation Assistant
                </h1>
                <div className="flex items-center gap-4 mt-2">
                  <p className="text-sm text-gray-600 font-medium">
                    {user?.email} <span className="text-gray-400">({user?.user_type})</span>
                  </p>

                </div>
              </div>

            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowHelpModal(true)}
                className="px-4 py-2 text-sm font-medium text-primary-600 bg-primary-50 hover:bg-primary-100 rounded-xl transition-all shadow-sm hover:shadow border border-primary-200"
              >
                Help
              </button>
              <button
                onClick={handleLogout}
                className="px-5 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all shadow-sm hover:shadow"
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        {/* Messages */}
        <div 
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto px-8 py-6 space-y-6 smooth-scroll"
        >
          {loadingMessages && messageOffset > 0 && (
            <div className="flex justify-center py-4">
              <div className="text-sm text-gray-500">Loading older messages...</div>
            </div>
          )}
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
            >
              <div
                className={`max-w-3xl rounded-2xl px-5 py-3.5 shadow-soft ${message.role === 'user'
                  ? 'bg-gradient-to-r from-primary-600 to-indigo-600 text-white'
                  : 'bg-white text-gray-900 border border-gray-200'
                  }`}
              >
                <p className={`whitespace-pre-wrap leading-relaxed ${message.role === 'user' ? 'text-white' : 'text-gray-800'}`}>
                  {message.content}
                </p>
                {message.role === 'assistant' && message.responseId && (
                  <div className="mt-3 pt-3 border-t border-gray-200 flex gap-3 flex-wrap items-center">
                    {message.recommendation && message.recommendation.status === 'approved' && (
                      <button
                        onClick={() => {
                          setSelectedRecommendation(message.recommendation);
                          setShowExplanation(true);
                        }}
                        className="text-sm text-primary-600 hover:text-primary-700 font-semibold transition-colors flex items-center gap-1.5 hover:underline"
                        title="View Detailed Explanation"
                      >
                        <span>📊</span> View Details
                      </button>
                    )}
                    <button
                      onClick={() => handleFeedback(message.id, 'thumbs_down')}
                      className="text-sm text-gray-500 hover:text-red-600 transition-colors p-1 rounded-lg hover:bg-red-50"
                      title="Thumbs Down"
                    >
                      👎
                    </button>
                    <button
                      onClick={() => {
                        const comment = prompt('Please describe the issue:');
                        if (comment) {
                          handleFeedback(message.id, 'report_error', comment);
                        }
                      }}
                      className="text-sm text-gray-600 hover:text-red-600 transition-colors font-medium hover:underline"
                      title="Report Error"
                    >
                      Report Error
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {streamingMessage && (
            <div className="flex justify-start animate-fade-in">
              <div className="max-w-3xl rounded-2xl px-5 py-3.5 bg-white text-gray-900 border border-gray-200 shadow-soft">
                <p className="whitespace-pre-wrap leading-relaxed">{streamingMessage}</p>
                <span className="inline-block w-2 h-4 bg-primary-600 animate-pulse ml-1 rounded" />
              </div>
            </div>
          )}

          {processingStatus && !streamingMessage && loading && (
            <div className="flex justify-start animate-fade-in">
              <div className="max-w-3xl rounded-2xl px-5 py-3.5 bg-primary-50 text-gray-800 border border-primary-200 shadow-soft">
                <div className="flex items-center gap-3">
                  <div className="flex gap-1.5">
                    <span className="w-2.5 h-2.5 bg-primary-500 rounded-full animate-bounce" />
                    <span className="w-2.5 h-2.5 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                    <span className="w-2.5 h-2.5 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                  </div>
                  <span className="text-sm font-semibold text-primary-800">{processingStatus}</span>
                </div>
              </div>
            </div>
          )}

          {loading && !streamingMessage && !processingStatus && (
            <div className="flex justify-start animate-fade-in">
              <div className="max-w-3xl rounded-2xl px-5 py-3.5 bg-white text-gray-800 border border-gray-200 shadow-soft">
                <div className="flex gap-1.5">
                  <span className="w-2.5 h-2.5 bg-gray-400 rounded-full animate-bounce" />
                  <span className="w-2.5 h-2.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <span className="w-2.5 h-2.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="bg-white/95 backdrop-blur-sm border-t border-gray-200 px-8 py-5 shadow-medium">
          <div className="flex gap-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder="Type your message... (Enter to send)"
              className="flex-1 px-5 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-gray-900 placeholder-gray-400 disabled:bg-gray-50 disabled:cursor-not-allowed shadow-sm"
              disabled={loading}
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="px-8 py-3 bg-gradient-to-r from-primary-600 to-indigo-600 text-white rounded-xl hover:from-primary-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold shadow-medium hover:shadow-lg transform hover:-translate-y-0.5 disabled:transform-none"
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Context Panel */}
      <ContextPanel
        candidateId={candidateId}
        onCandidateIdChange={setCandidateId}
      />

      {/* Explanation Panel Sidebar */}
      {showExplanation && (
        <ExplanationPanel
          recommendation={selectedRecommendation}
          onClose={() => {
            setShowExplanation(false);
            setSelectedRecommendation(null);
          }}
        />
      )}

      {/* Help Modal */}
      {showHelpModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowHelpModal(false)}>
          <div className="bg-white rounded-2xl p-8 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Available Commands</h2>
              <button
                onClick={() => setShowHelpModal(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors p-2 rounded-lg hover:bg-gray-100"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div className="border-l-4 border-primary-500 pl-4">
                <h3 className="font-semibold text-gray-900 mb-1">/switch &lt;candidate_id&gt;</h3>
                <p className="text-sm text-gray-600">Switch to a different active candidate. Example: <code className="bg-gray-100 px-1 rounded">/switch ABC123</code></p>
              </div>

              <div className="border-l-4 border-primary-500 pl-4">
                <h3 className="font-semibold text-gray-900 mb-1">/close</h3>
                <p className="text-sm text-gray-600">Close the currently active candidate. This marks the candidate as closed and clears it from active status.</p>
              </div>

              <div className="border-l-4 border-primary-500 pl-4">
                <h3 className="font-semibold text-gray-900 mb-1">/reopen &lt;candidate_id&gt;</h3>
                <p className="text-sm text-gray-600">Reopen a closed candidate. Example: <code className="bg-gray-100 px-1 rounded">/reopen ABC123</code></p>
              </div>

              <div className="border-l-4 border-primary-500 pl-4">
                <h3 className="font-semibold text-gray-900 mb-1">/list</h3>
                <p className="text-sm text-gray-600">List all active candidates you're working with.</p>
              </div>

              <div className="border-l-4 border-primary-500 pl-4">
                <h3 className="font-semibold text-gray-900 mb-1">/status</h3>
                <p className="text-sm text-gray-600">Get the current status and context for the active candidate, including job title, location, level, and interview feedback.</p>
              </div>

              <div className="border-l-4 border-primary-500 pl-4">
                <h3 className="font-semibold text-gray-900 mb-1">/new</h3>
                <p className="text-sm text-gray-600">Start working with a new candidate. You'll be prompted to provide candidate information.</p>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-gray-200">
              <p className="text-xs text-gray-500">
                <strong>Tip:</strong> You can also use natural language instead of commands. For example,
                "Get compensation for candidate ABC123" or "What's the status of the current candidate?"
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

