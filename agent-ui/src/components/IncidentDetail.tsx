'use client';

import * as React from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Tabs,
  Tab,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import ChatIcon from '@mui/icons-material/Chat';
import DnsIcon from '@mui/icons-material/Dns';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import MarkdownView from './MarkdownView';
import { Incident } from '@/types/incident';

interface IncidentDetailProps {
  incident: Incident;
  onBack: () => void;
  onDiscussInChat: (incident: Incident) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export default function IncidentDetail({
  incident,
  onBack,
  onDiscussInChat,
  onRefresh,
  isRefreshing,
}: IncidentDetailProps) {
  const [tabValue, setTabValue] = React.useState<number>(0);
  const [copied, setCopied] = React.useState<boolean>(false);

  const handleCopyReport = () => {
    const text = incident.response || incident.summary || 'No report available.';
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTimestamp = (secOrMs?: number | string) => {
    if (!secOrMs) return 'N/A';
    const date =
      typeof secOrMs === 'number'
        ? new Date(secOrMs > 1e11 ? secOrMs : secOrMs * 1000)
        : new Date(secOrMs);
    return (
      date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
      ' on ' +
      date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
    );
  };

  return (
    <Box sx={{ width: '100%', py: 1 }}>
      {/* Top Navigation Bar */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 2.5,
          flexWrap: 'wrap',
          gap: 1.5,
        }}
      >
        <Button
          id="back-to-incidents-btn"
          startIcon={<ArrowBackIcon />}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onBack();
          }}
          sx={{
            color: 'text.secondary',
            bgcolor: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            cursor: 'pointer',
            zIndex: 10,
            '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.08)', color: '#f1f5f9' },
          }}
        >
          Back to Incidents
        </Button>

        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
          {incident.status === 'INVESTIGATING' && (
            <Button
              size="small"
              onClick={onRefresh}
              disabled={isRefreshing}
              startIcon={isRefreshing ? <CircularProgress size={14} color="inherit" /> : null}
              sx={{
                bgcolor: 'rgba(234, 179, 8, 0.1)',
                color: '#eab308',
                border: '1px solid rgba(234, 179, 8, 0.3)',
                '&:hover': { bgcolor: 'rgba(234, 179, 8, 0.2)' },
              }}
            >
              {isRefreshing ? 'Checking...' : 'Check Status'}
            </Button>
          )}

          <Button
            size="small"
            startIcon={copied ? <CheckIcon /> : <ContentCopyIcon />}
            onClick={handleCopyReport}
            disabled={!incident.response}
            sx={{
              bgcolor: 'rgba(255, 255, 255, 0.04)',
              color: copied ? '#10b981' : 'text.primary',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.08)' },
            }}
          >
            {copied ? 'Copied' : 'Copy Report'}
          </Button>

          <Button
            size="small"
            variant="contained"
            startIcon={<ChatIcon />}
            onClick={() => onDiscussInChat(incident)}
            sx={{
              bgcolor: 'primary.main',
              color: '#0a0a0b',
              fontWeight: 650,
              '&:hover': { bgcolor: 'primary.light' },
            }}
          >
            Ask Agent in Chat
          </Button>
        </Box>
      </Box>

      {/* Main Incident Overview Header Card */}
      <Paper
        sx={{
          p: 3,
          bgcolor: 'rgba(22, 22, 24, 0.8)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 3,
          mb: 3,
          backdropFilter: 'blur(10px)',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: 2,
            flexWrap: 'wrap',
          }}
        >
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1, flexWrap: 'wrap' }}>
              <Chip
                size="small"
                label={incident.status}
                sx={{
                  bgcolor:
                    incident.status === 'COMPLETED'
                      ? 'rgba(16, 185, 129, 0.15)'
                      : incident.status === 'INVESTIGATING'
                      ? 'rgba(234, 179, 8, 0.15)'
                      : 'rgba(239, 68, 68, 0.15)',
                  color:
                    incident.status === 'COMPLETED'
                      ? '#10b981'
                      : incident.status === 'INVESTIGATING'
                      ? '#eab308'
                      : '#ef4444',
                  border: '1px solid',
                  borderColor:
                    incident.status === 'COMPLETED'
                      ? 'rgba(16, 185, 129, 0.3)'
                      : incident.status === 'INVESTIGATING'
                      ? 'rgba(234, 179, 8, 0.3)'
                      : 'rgba(239, 68, 68, 0.3)',
                  fontWeight: 700,
                  fontSize: '0.75rem',
                }}
              />
              <Chip
                size="small"
                icon={<DnsIcon sx={{ fontSize: '13px !important' }} />}
                label={incident.service}
                sx={{
                  bgcolor: 'rgba(0, 229, 255, 0.08)',
                  color: '#00e5ff',
                  border: '1px solid rgba(0, 229, 255, 0.2)',
                  fontWeight: 600,
                }}
              />
              <Typography
                variant="caption"
                sx={{
                  fontFamily: 'monospace',
                  color: 'rgba(255, 255, 255, 0.4)',
                  fontSize: '0.8rem',
                }}
              >
                ID: {incident.id}
              </Typography>
            </Box>

            <Typography variant="h5" sx={{ fontWeight: 700, color: '#f8fafc', mb: 0.8 }}>
              {incident.alertname}
            </Typography>

            <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: 750 }}>
              {incident.summary || incident.description}
            </Typography>
          </Box>

          <Box sx={{ textAlign: { xs: 'left', sm: 'right' } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8, color: 'text.secondary', mb: 0.5 }}>
              <AccessTimeIcon sx={{ fontSize: 16 }} />
              <Typography variant="caption">Started: {formatTimestamp(incident.starts_at || incident.created_at)}</Typography>
            </Box>
            {incident.updated_at && incident.updated_at !== incident.created_at && (
              <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.4)', display: 'block' }}>
                Report completed: {formatTimestamp(incident.updated_at)}
              </Typography>
            )}
          </Box>
        </Box>
      </Paper>

      {/* Status Alert Banner */}
      {incident.status === 'INVESTIGATING' && (
        <Paper
          sx={{
            p: 3,
            bgcolor: 'rgba(234, 179, 8, 0.08)',
            border: '1px solid rgba(234, 179, 8, 0.25)',
            borderRadius: 2.5,
            mb: 3,
            display: 'flex',
            alignItems: 'center',
            gap: 2.5,
          }}
        >
          <CircularProgress size={32} sx={{ color: '#eab308', flexShrink: 0 }} />
          <Box>
            <Typography variant="subtitle2" sx={{ color: '#fef08a', fontWeight: 700 }}>
              Autonomous Investigation In Progress
            </Typography>
            <Typography variant="body2" sx={{ color: '#fef9c3', opacity: 0.85, mt: 0.3 }}>
              The AI agent is querying Prometheus metrics, inspecting Loki error logs, analyzing Kubernetes pod health, and cross-referencing repository code. Live polling is active.
            </Typography>
          </Box>
        </Paper>
      )}

      {incident.status === 'FAILED' && (
        <Paper
          sx={{
            p: 3,
            bgcolor: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            borderRadius: 2.5,
            mb: 3,
            display: 'flex',
            alignItems: 'flex-start',
            gap: 2,
          }}
        >
          <ErrorOutlineIcon sx={{ color: '#ef4444', fontSize: 28, mt: 0.2 }} />
          <Box>
            <Typography variant="subtitle2" sx={{ color: '#fca5a5', fontWeight: 700 }}>
              Investigation Encountered An Error
            </Typography>
            <Typography variant="body2" sx={{ color: '#fecaca', opacity: 0.85, mt: 0.5, fontFamily: 'monospace' }}>
              {incident.error || 'Agent execution failed to complete.'}
            </Typography>
          </Box>
        </Paper>
      )}

      {/* Tabs */}
      <Box sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)', mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={(_, newVal) => setTabValue(newVal)}
          sx={{
            '& .MuiTab-root': {
              color: 'text.secondary',
              textTransform: 'none',
              fontWeight: 600,
              fontSize: '0.9rem',
              '&.Mui-selected': { color: '#00e5ff' },
            },
            '& .MuiTabs-indicator': {
              bgcolor: '#00e5ff',
            },
          }}
        >
          <Tab icon={<SmartToyIcon sx={{ fontSize: 18 }} />} iconPosition="start" label="AI Diagnostic Report" />
          <Tab icon={<WarningAmberIcon sx={{ fontSize: 18 }} />} iconPosition="start" label="Alert Trigger Context" />
        </Tabs>
      </Box>

      {/* Tab Panels */}
      {tabValue === 0 && (
        <Paper
          sx={{
            p: { xs: 2.5, sm: 4 },
            bgcolor: 'rgba(22, 22, 24, 0.7)',
            border: '1px solid rgba(255, 255, 255, 0.07)',
            borderRadius: 3,
            backdropFilter: 'blur(8px)',
          }}
        >
          {incident.response ? (
            <MarkdownView content={incident.response} />
          ) : incident.status === 'INVESTIGATING' ? (
            <Box sx={{ py: 6, textAlign: 'center' }}>
              <CircularProgress size={40} sx={{ color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" sx={{ color: '#f1f5f9' }}>
                Analyzing Telemetry & Code...
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: 460, mx: 'auto', mt: 1 }}>
                The agent is currently correlating Prometheus metrics and Loki logs to trace the root cause. This view will automatically populate when the diagnosis is ready.
              </Typography>
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No diagnostic report generated.
            </Typography>
          )}
        </Paper>
      )}

      {tabValue === 1 && (
        <Paper
          sx={{
            p: 3,
            bgcolor: 'rgba(22, 22, 24, 0.7)',
            border: '1px solid rgba(255, 255, 255, 0.07)',
            borderRadius: 3,
          }}
        >
          <Typography variant="subtitle2" sx={{ color: '#00e5ff', fontWeight: 700, mb: 1 }}>
            Investigation Query / Prompt Dispatched:
          </Typography>
          <Box
            component="pre"
            sx={{
              p: 2,
              borderRadius: 2,
              bgcolor: '#090a0f',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              overflowX: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.85rem',
              color: '#cbd5e1',
              whiteSpace: 'pre-wrap',
            }}
          >
            {incident.query}
          </Box>
        </Paper>
      )}
    </Box>
  );
}
