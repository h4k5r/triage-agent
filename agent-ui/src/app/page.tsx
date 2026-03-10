'use client';

import * as React from 'react';
import {
  Box,
  Container,
  TextField,
  IconButton,
  Typography,
  Paper,
  Avatar,
  CircularProgress,
  AppBar,
  Toolbar,
  Tooltip,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import TerminalIcon from '@mui/icons-material/Terminal';
import SupportAgentIcon from '@mui/icons-material/SupportAgent';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: Date;
}

export default function ChatPage() {
  const [query, setQuery] = React.useState('');
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!query.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/triage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMessage.content }),
      });

      const data = await response.json();
      
      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'agent',
        content: data.response || 'Agent produced no response.',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'agent',
          content: 'Error: Failed to connect to the Triage Agent API.',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh', bgcolor: 'background.default' }}>
      {/* Header */}
      <AppBar position="static" elevation={0} sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', bgcolor: 'rgba(22,22,24,0.8)', backdropFilter: 'blur(10px)' }}>
        <Toolbar>
          <TerminalIcon sx={{ mr: 2, color: 'primary.main' }} />
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700, letterSpacing: -0.5 }}>
            AI Triage <Box component="span" sx={{ color: 'primary.main' }}>Agent</Box>
          </Typography>
          <Tooltip title="Cluster Status: Connected">
            <IconButton size="small" sx={{ ml: 1 }}>
              <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: '#4caf50', boxShadow: '0 0 8px #4caf50' }} />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* Message Area */}
      <Box 
        ref={scrollRef}
        sx={{ 
          flexGrow: 1, 
          overflowY: 'auto', 
          p: 3,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          scrollBehavior: 'smooth'
        }}
      >
        <Container maxWidth="md">
          {messages.length === 0 && (
            <Box sx={{ mt: 10, textAlign: 'center', opacity: 0.5 }}>
              <SupportAgentIcon sx={{ fontSize: 64, mb: 2 }} />
              <Typography variant="h5" gutterBottom>How can I assist your cluster today?</Typography>
              <Typography variant="body2">Ask about pod status, logs, or metrics.</Typography>
            </Box>
          )}

          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                style={{ marginBottom: '16px', display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}
              >
                <Box sx={{ 
                  display: 'flex', 
                  flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                  alignItems: 'flex-start',
                  gap: 1.5,
                  maxWidth: '85%'
                }}>
                  <Avatar sx={{ 
                    bgcolor: msg.role === 'user' ? 'secondary.main' : 'primary.main',
                    width: 32,
                    height: 32
                  }}>
                    {msg.role === 'user' ? <SupportAgentIcon sx={{ fontSize: 20 }} /> : <SmartToyIcon sx={{ fontSize: 20 }} />}
                  </Avatar>
                  <Paper sx={{ 
                    p: 2, 
                    bgcolor: msg.role === 'user' ? 'rgba(255, 64, 129, 0.1)' : 'rgba(0, 229, 255, 0.05)',
                    border: '1px solid',
                    borderColor: msg.role === 'user' ? 'rgba(255, 64, 129, 0.2)' : 'rgba(0, 229, 255, 0.1)',
                    backdropFilter: 'blur(5px)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}>
                    <Typography variant="body1">
                      {msg.content}
                    </Typography>
                  </Paper>
                </Box>
              </motion.div>
            ))}
          </AnimatePresence>

          {isLoading && (
            <Box sx={{ display: 'flex', gap: 1.5, mb: 2 }}>
              <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>
                <SmartToyIcon sx={{ fontSize: 20 }} />
              </Avatar>
              <Paper sx={{ p: 2, bgcolor: 'rgba(0, 229, 255, 0.05)', border: '1px solid rgba(0, 229, 255, 0.1)', display: 'flex', alignItems: 'center', gap: 2 }}>
                <CircularProgress size={16} thickness={5} />
                <Typography variant="body2" color="text.secondary">Agent is analyzing cluster data...</Typography>
              </Paper>
            </Box>
          )}
        </Container>
      </Box>

      {/* Input Area */}
      <Box sx={{ p: 3, borderTop: '1px solid rgba(255,255,255,0.05)', bgcolor: '#161618' }}>
        <Container maxWidth="md">
          <Box sx={{ position: 'relative' }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              variant="outlined"
              placeholder="Query the cluster (e.g., 'Check logs for node-typescript-app')"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  bgcolor: 'rgba(0,0,0,0.2)',
                  borderRadius: 3,
                  pr: 7,
                }
              }}
            />
            <IconButton 
              disabled={isLoading || !query.trim()}
              onClick={handleSend}
              sx={{ 
                position: 'absolute', 
                right: 8, 
                bottom: 8,
                bgcolor: 'primary.main',
                color: 'background.default',
                '&:hover': { bgcolor: 'primary.light' },
                '&.Mui-disabled': { bgcolor: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.2)' }
              }}
            >
              {isLoading ? <CircularProgress size={24} color="inherit" /> : <SendIcon />}
            </IconButton>
          </Box>
          <Typography variant="caption" sx={{ mt: 1, display: 'block', opacity: 0.4, textAlign: 'center' }}>
            Powered by LangGraph & MCP Tools. Responses are generated based on real-time cluster telemetry.
          </Typography>
        </Container>
      </Box>
    </Box>
  );
}
