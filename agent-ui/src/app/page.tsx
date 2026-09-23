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
  Tabs,
  Tab,
  Badge,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import TerminalIcon from '@mui/icons-material/Terminal';
import SupportAgentIcon from '@mui/icons-material/SupportAgent';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import { motion, AnimatePresence } from 'framer-motion';
import IncidentList from '@/components/IncidentList';
import IncidentDetail from '@/components/IncidentDetail';
import MarkdownView from '@/components/MarkdownView';
import { Incident } from '@/types/incident';

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: Date;
}

export default function MainPage() {
  // Navigation & View state
  const [activeTab, setActiveTab] = React.useState<'incidents' | 'chat'>('incidents');
  const [selectedIncident, setSelectedIncident] = React.useState<Incident | null>(null);

  // Incidents state
  const [incidents, setIncidents] = React.useState<Incident[]>([]);
  const [isLoadingIncidents, setIsLoadingIncidents] = React.useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = React.useState<boolean>(true);
  const [isRefreshingDetail, setIsRefreshingDetail] = React.useState<boolean>(false);

  // Chat state
  const [query, setQuery] = React.useState('');
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [isLoadingChat, setIsLoadingChat] = React.useState(false);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  // Ref for selected incident to avoid stale closures in polling
  const selectedIncidentRef = React.useRef<Incident | null>(null);
  React.useEffect(() => {
    selectedIncidentRef.current = selectedIncident;
  }, [selectedIncident]);

  // Derive API base URL
  const apiBaseUrl = React.useMemo(() => {
    const raw = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return raw.replace(/\/triage\/?$/, '');
  }, []);

  // Fetch incidents
  const fetchIncidents = React.useCallback(async (silent = false) => {
    if (!silent) setIsLoadingIncidents(true);
    try {
      const res = await fetch(`${apiBaseUrl}/alerts`);
      if (res.ok) {
        const data: Incident[] = await res.json();
        setIncidents(data);

        // Keep selected incident synced if open
        if (selectedIncidentRef.current) {
          const updated = data.find((i) => i.id === selectedIncidentRef.current?.id);
          if (updated) {
            setSelectedIncident(updated);
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch incidents:', err);
    } finally {
      if (!silent) setIsLoadingIncidents(false);
    }
  }, [apiBaseUrl]);

  // Initial load
  React.useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  // Live polling for incidents
  React.useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchIncidents(true);
    }, 4000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchIncidents]);

  // Refresh single detail
  const handleRefreshDetail = async () => {
    if (!selectedIncident) return;
    setIsRefreshingDetail(true);
    try {
      const res = await fetch(`${apiBaseUrl}/alerts/${selectedIncident.id}`);
      if (res.ok) {
        const data: Incident = await res.json();
        setSelectedIncident(data);
        setIncidents((prev) => prev.map((i) => (i.id === data.id ? data : i)));
      }
    } catch (err) {
      console.error('Failed to refresh incident detail:', err);
    } finally {
      setIsRefreshingDetail(false);
    }
  };

  // Scroll to bottom of chat
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, activeTab]);

  // Send interactive chat query
  const handleSend = async (customQuery?: string) => {
    const textToSend = customQuery || query;
    if (!textToSend.trim() || isLoadingChat) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: textToSend,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!customQuery) setQuery('');
    setIsLoadingChat(true);

    try {
      const response = await fetch(`${apiBaseUrl}/triage`, {
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
          content: 'Error: Failed to connect to the Triage Agent API at ' + apiBaseUrl,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoadingChat(false);
    }
  };

  const handleBackToList = React.useCallback(() => {
    selectedIncidentRef.current = null;
    setSelectedIncident(null);
  }, []);

  // Switch to chat from an incident
  const handleDiscussInChat = (incident: Incident) => {
    setActiveTab('chat');
    const prompt = `Can you provide more details about incident ${incident.id} (${incident.alertname}) for service '${incident.service}'? How can we prevent this error in the future?`;
    setQuery(prompt);
  };

  const activeIncidentsCount = React.useMemo(() => {
    return incidents.filter((i) => i.status === 'INVESTIGATING').length;
  }, [incidents]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh', bgcolor: 'background.default' }}>
      {/* Global Header */}
      <AppBar
        position="static"
        elevation={0}
        sx={{
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          bgcolor: 'rgba(22, 22, 24, 0.85)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <Toolbar sx={{ justifyContent: 'space-between' }}>
          {/* Logo & Brand */}
          <Box
            onClick={() => {
              setActiveTab('incidents');
              handleBackToList();
            }}
            sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}
          >
            <TerminalIcon sx={{ mr: 1.5, color: 'primary.main', fontSize: 26 }} />
            <Typography variant="h6" sx={{ fontWeight: 750, letterSpacing: -0.5 }}>
              AI Triage <Box component="span" sx={{ color: 'primary.main' }}>Agent</Box>
            </Typography>
          </Box>

          {/* Navigation Tabs */}
          <Tabs
            value={activeTab}
            onChange={(_, val) => {
              setActiveTab(val);
              handleBackToList();
            }}
            sx={{
              minHeight: 48,
              '& .MuiTab-root': {
                minHeight: 48,
                color: 'text.secondary',
                textTransform: 'none',
                fontWeight: 655,
                fontSize: '0.9rem',
                px: 2.5,
                '&.Mui-selected': { color: '#00e5ff' },
              },
              '& .MuiTabs-indicator': {
                bgcolor: '#00e5ff',
                height: 3,
                borderRadius: '3px 3px 0 0',
              },
            }}
          >
            <Tab
              value="incidents"
              onClick={handleBackToList}
              icon={
                <Badge
                  badgeContent={activeIncidentsCount}
                  color="warning"
                  sx={{
                    '& .MuiBadge-badge': {
                      fontSize: '0.65rem',
                      height: 16,
                      minWidth: 16,
                      animation: activeIncidentsCount > 0 ? 'pulse 2s infinite' : 'none',
                    },
                  }}
                >
                  <WarningAmberIcon sx={{ fontSize: 18 }} />
                </Badge>
              }
              iconPosition="start"
              label="Incidents Hub"
            />
            <Tab
              value="chat"
              icon={<ChatBubbleOutlineIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              label="AI Assistant"
            />
          </Tabs>

          {/* Right Status Indicator */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Tooltip title="Connected to Kubernetes cluster & MCP tools">
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  px: 1.2,
                  py: 0.5,
                  borderRadius: 2,
                  bgcolor: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                }}
              >
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    bgcolor: '#10b981',
                    boxShadow: '0 0 8px #10b981',
                  }}
                />
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                  Cluster Live
                </Typography>
              </Box>
            </Tooltip>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Main Content Area */}
      {activeTab === 'incidents' ? (
        <Box sx={{ flexGrow: 1, overflowY: 'auto', p: { xs: 2, md: 4 } }}>
          <Container maxWidth="lg">
            <Box>
              {selectedIncident ? (
                <Box key="detail">
                  <IncidentDetail
                    incident={selectedIncident}
                    onBack={handleBackToList}
                    onDiscussInChat={handleDiscussInChat}
                    onRefresh={handleRefreshDetail}
                    isRefreshing={isRefreshingDetail}
                  />
                </Box>
              ) : (
                <Box key="list">
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="h4" sx={{ fontWeight: 800, color: '#f8fafc', letterSpacing: -0.5 }}>
                      Incident Triage Hub
                    </Typography>
                    <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
                      Automated alert investigations triggered by Grafana Alertmanager and diagnosed by the AI Agent.
                    </Typography>
                  </Box>

                  <IncidentList
                    incidents={incidents}
                    isLoading={isLoadingIncidents}
                    onRefresh={() => fetchIncidents(false)}
                    onSelectIncident={(inc) => {
                      selectedIncidentRef.current = inc;
                      setSelectedIncident(inc);
                    }}
                    autoRefresh={autoRefresh}
                    onToggleAutoRefresh={setAutoRefresh}
                  />
                </Box>
              )}
            </Box>
          </Container>
        </Box>
      ) : (
        /* Chat View */
        <Box sx={{ display: 'flex', flexDirection: 'column', flexGrow: 1, height: 'calc(100vh - 64px)' }}>
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
              scrollBehavior: 'smooth',
            }}
          >
            <Container maxWidth="md">
              {messages.length === 0 && (
                <Box sx={{ mt: 10, textAlign: 'center', opacity: 0.6 }}>
                  <SupportAgentIcon sx={{ fontSize: 64, mb: 2, color: 'primary.main' }} />
                  <Typography variant="h5" sx={{ fontWeight: 700 }} gutterBottom>
                    How can I assist your cluster today?
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Ask about pod status, error spikes, Loki logs, or deployment configurations.
                  </Typography>
                </Box>
              )}

              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    style={{
                      marginBottom: '16px',
                      display: 'flex',
                      justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    }}
                  >
                    <Box
                      sx={{
                        display: 'flex',
                        flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                        alignItems: 'flex-start',
                        gap: 1.5,
                        maxWidth: '90%',
                      }}
                    >
                      <Avatar
                        sx={{
                          bgcolor: msg.role === 'user' ? 'secondary.main' : 'primary.main',
                          width: 32,
                          height: 32,
                          color: '#0a0a0b',
                        }}
                      >
                        {msg.role === 'user' ? (
                          <SupportAgentIcon sx={{ fontSize: 20 }} />
                        ) : (
                          <SmartToyIcon sx={{ fontSize: 20 }} />
                        )}
                      </Avatar>
                      <Paper
                        sx={{
                          p: 2.5,
                          bgcolor:
                            msg.role === 'user'
                              ? 'rgba(255, 64, 129, 0.08)'
                              : 'rgba(0, 229, 255, 0.04)',
                          border: '1px solid',
                          borderColor:
                            msg.role === 'user'
                              ? 'rgba(255, 64, 129, 0.25)'
                              : 'rgba(0, 229, 255, 0.15)',
                          borderRadius: 2.5,
                          backdropFilter: 'blur(8px)',
                          width: '100%',
                        }}
                      >
                        {msg.role === 'agent' ? (
                          <MarkdownView content={msg.content} />
                        ) : (
                          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                            {msg.content}
                          </Typography>
                        )}
                      </Paper>
                    </Box>
                  </motion.div>
                ))}
              </AnimatePresence>

              {isLoadingChat && (
                <Box sx={{ display: 'flex', gap: 1.5, mb: 2 }}>
                  <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32, color: '#0a0a0b' }}>
                    <SmartToyIcon sx={{ fontSize: 20 }} />
                  </Avatar>
                  <Paper
                    sx={{
                      p: 2,
                      bgcolor: 'rgba(0, 229, 255, 0.04)',
                      border: '1px solid rgba(0, 229, 255, 0.12)',
                      borderRadius: 2.5,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 2,
                    }}
                  >
                    <CircularProgress size={16} thickness={5} />
                    <Typography variant="body2" color="text.secondary">
                      Agent is analyzing cluster data via MCP tools...
                    </Typography>
                  </Paper>
                </Box>
              )}
            </Container>
          </Box>

          {/* Input Area */}
          <Box sx={{ p: 2.5, borderTop: '1px solid rgba(255, 255, 255, 0.06)', bgcolor: '#161618' }}>
            <Container maxWidth="md">
              <Box sx={{ position: 'relative' }}>
                <TextField
                  fullWidth
                  multiline
                  maxRows={4}
                  variant="outlined"
                  placeholder="Query cluster state (e.g., 'Check recent errors in node-typescript-app')"
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
                      bgcolor: 'rgba(0, 0, 0, 0.3)',
                      borderRadius: 3,
                      pr: 7,
                    },
                  }}
                />
                <IconButton
                  disabled={isLoadingChat || !query.trim()}
                  onClick={() => handleSend()}
                  sx={{
                    position: 'absolute',
                    right: 8,
                    bottom: 8,
                    bgcolor: 'primary.main',
                    color: '#0a0a0b',
                    '&:hover': { bgcolor: 'primary.light' },
                    '&.Mui-disabled': {
                      bgcolor: 'rgba(255, 255, 255, 0.05)',
                      color: 'rgba(255, 255, 255, 0.2)',
                    },
                  }}
                >
                  {isLoadingChat ? <CircularProgress size={24} color="inherit" /> : <SendIcon />}
                </IconButton>
              </Box>
              <Typography variant="caption" sx={{ mt: 1, display: 'block', opacity: 0.4, textAlign: 'center' }}>
                Powered by LangGraph ReAct Agent with Kubernetes, Grafana, and GitHub MCP Tools.
              </Typography>
            </Container>
          </Box>
        </Box>
      )}
    </Box>
  );
}
