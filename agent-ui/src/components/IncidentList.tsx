'use client';

import * as React from 'react';
import {
  Box,
  Typography,
  Paper,
  Chip,
  IconButton,
  TextField,
  Button,
  CircularProgress,
  Tooltip,
  Switch,
  FormControlLabel,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import DnsIcon from '@mui/icons-material/Dns';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import SearchIcon from '@mui/icons-material/Search';
import { motion, AnimatePresence } from 'framer-motion';
import { Incident } from '@/types/incident';

interface IncidentListProps {
  incidents: Incident[];
  isLoading: boolean;
  onRefresh: () => void;
  onSelectIncident: (incident: Incident) => void;
  autoRefresh: boolean;
  onToggleAutoRefresh: (val: boolean) => void;
}

export default function IncidentList({
  incidents,
  isLoading,
  onRefresh,
  onSelectIncident,
  autoRefresh,
  onToggleAutoRefresh,
}: IncidentListProps) {
  const [filterStatus, setFilterStatus] = React.useState<string>('ALL');
  const [searchQuery, setSearchQuery] = React.useState<string>('');

  const filteredIncidents = React.useMemo(() => {
    return incidents.filter((inc) => {
      const matchesStatus =
        filterStatus === 'ALL' || inc.status.toUpperCase() === filterStatus;
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        inc.alertname.toLowerCase().includes(q) ||
        inc.service.toLowerCase().includes(q) ||
        (inc.summary && inc.summary.toLowerCase().includes(q)) ||
        (inc.description && inc.description.toLowerCase().includes(q));
      return matchesStatus && matchesSearch;
    });
  }, [incidents, filterStatus, searchQuery]);

  const activeCount = React.useMemo(() => {
    return incidents.filter((i) => i.status === 'INVESTIGATING').length;
  }, [incidents]);

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'INVESTIGATING':
        return (
          <Chip
            size="small"
            icon={<CircularProgress size={12} color="inherit" sx={{ mr: 0.5 }} />}
            label="INVESTIGATING"
            sx={{
              bgcolor: 'rgba(234, 179, 8, 0.15)',
              color: '#eab308',
              border: '1px solid rgba(234, 179, 8, 0.3)',
              fontWeight: 700,
              fontSize: '0.72rem',
              letterSpacing: 0.5,
              animation: 'pulse 2s infinite',
              '@keyframes pulse': {
                '0%, 100%': { opacity: 1 },
                '50%': { opacity: 0.6 },
              },
            }}
          />
        );
      case 'COMPLETED':
        return (
          <Chip
            size="small"
            icon={<CheckCircleOutlineIcon sx={{ fontSize: '14px !important', color: '#10b981' }} />}
            label="DIAGNOSIS READY"
            sx={{
              bgcolor: 'rgba(16, 185, 129, 0.12)',
              color: '#10b981',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              fontWeight: 700,
              fontSize: '0.72rem',
            }}
          />
        );
      case 'FAILED':
        return (
          <Chip
            size="small"
            icon={<ErrorOutlineIcon sx={{ fontSize: '14px !important', color: '#ef4444' }} />}
            label="FAILED"
            sx={{
              bgcolor: 'rgba(239, 68, 68, 0.12)',
              color: '#ef4444',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              fontWeight: 700,
              fontSize: '0.72rem',
            }}
          />
        );
      default:
        return (
          <Chip
            size="small"
            label={status}
            sx={{
              bgcolor: 'rgba(148, 163, 184, 0.1)',
              color: '#94a3b8',
              border: '1px solid rgba(148, 163, 184, 0.2)',
              fontWeight: 600,
              fontSize: '0.72rem',
            }}
          />
        );
    }
  };

  const formatTimestamp = (secOrMs: number | string) => {
    if (!secOrMs) return 'N/A';
    const date = typeof secOrMs === 'number' ? new Date(secOrMs > 1e11 ? secOrMs : secOrMs * 1000) : new Date(secOrMs);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' ' + date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <Box sx={{ width: '100%', py: 1 }}>
      {/* Action Controls & Filters Bar */}
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 2,
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 3,
        }}
      >
        {/* Status Filters */}
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {[
            { key: 'ALL', label: `All (${incidents.length})` },
            { key: 'INVESTIGATING', label: `Investigating (${activeCount})` },
            { key: 'COMPLETED', label: 'Completed' },
            { key: 'FAILED', label: 'Failed' },
          ].map((tab) => (
            <Chip
              key={tab.key}
              label={tab.label}
              clickable
              onClick={() => setFilterStatus(tab.key)}
              sx={{
                bgcolor:
                  filterStatus === tab.key
                    ? 'rgba(0, 229, 255, 0.15)'
                    : 'rgba(255, 255, 255, 0.04)',
                color: filterStatus === tab.key ? '#00e5ff' : 'text.secondary',
                border: '1px solid',
                borderColor:
                  filterStatus === tab.key
                    ? 'rgba(0, 229, 255, 0.3)'
                    : 'rgba(255, 255, 255, 0.08)',
                fontWeight: 600,
                fontSize: '0.8rem',
                '&:hover': {
                  bgcolor: 'rgba(0, 229, 255, 0.2)',
                },
              }}
            />
          ))}
        </Box>

        {/* Controls: Search + Refresh + Auto-Refresh */}
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
          <TextField
            size="small"
            placeholder="Search service, alert..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: <SearchIcon sx={{ fontSize: 18, color: 'text.secondary', mr: 1 }} />,
            }}
            sx={{
              width: { xs: 160, sm: 220 },
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(0, 0, 0, 0.25)',
                borderRadius: 2,
                fontSize: '0.85rem',
              },
            }}
          />

          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={autoRefresh}
                onChange={(e) => onToggleAutoRefresh(e.target.checked)}
                sx={{
                  '& .MuiSwitch-switchBase.Mui-checked': {
                    color: 'primary.main',
                  },
                }}
              />
            }
            label={
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 500 }}>
                Live (4s)
              </Typography>
            }
            sx={{ m: 0 }}
          />

          <Tooltip title="Refresh incidents">
            <IconButton
              size="small"
              onClick={onRefresh}
              disabled={isLoading}
              sx={{
                bgcolor: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.1)' },
              }}
            >
              {isLoading ? (
                <CircularProgress size={18} color="inherit" />
              ) : (
                <RefreshIcon sx={{ fontSize: 18 }} />
              )}
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Incidents List Cards */}
      {filteredIncidents.length === 0 ? (
        <Paper
          sx={{
            p: 6,
            textAlign: 'center',
            bgcolor: 'rgba(22, 22, 24, 0.5)',
            border: '1px dashed rgba(255, 255, 255, 0.1)',
            borderRadius: 3,
          }}
        >
          <HourglassEmptyIcon sx={{ fontSize: 48, color: 'text.secondary', opacity: 0.4, mb: 1.5 }} />
          <Typography variant="h6" sx={{ color: '#e2e8f0', fontWeight: 650 }}>
            No Incidents Found
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: 420, mx: 'auto', mt: 0.5 }}>
            {incidents.length === 0
              ? 'When Grafana detects error spikes or alerts fire, the AI Triage Agent will autonomously capture the alert and begin diagnostics here.'
              : 'No incidents match your current filter or search criteria.'}
          </Typography>
        </Paper>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <AnimatePresence>
            {filteredIncidents.map((incident) => (
              <motion.div
                key={incident.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
              >
                <Paper
                  onClick={() => onSelectIncident(incident)}
                  sx={{
                    p: 2.5,
                    bgcolor: 'rgba(22, 22, 24, 0.7)',
                    border: '1px solid',
                    borderColor:
                      incident.status === 'INVESTIGATING'
                        ? 'rgba(234, 179, 8, 0.3)'
                        : 'rgba(255, 255, 255, 0.07)',
                    borderRadius: 2.5,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    backdropFilter: 'blur(8px)',
                    '&:hover': {
                      bgcolor: 'rgba(30, 30, 34, 0.9)',
                      borderColor: 'rgba(0, 229, 255, 0.3)',
                      transform: 'translateY(-2px)',
                      boxShadow: '0 6px 20px rgba(0, 0, 0, 0.4)',
                    },
                  }}
                >
                  {/* Card Header */}
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      mb: 1.5,
                      gap: 1.5,
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, flexWrap: 'wrap' }}>
                      {getStatusChip(incident.status)}
                      <Chip
                        size="small"
                        icon={<DnsIcon sx={{ fontSize: '13px !important' }} />}
                        label={incident.service}
                        sx={{
                          bgcolor: 'rgba(0, 229, 255, 0.08)',
                          color: '#00e5ff',
                          border: '1px solid rgba(0, 229, 255, 0.2)',
                          fontWeight: 600,
                          fontSize: '0.75rem',
                        }}
                      />
                      <Typography
                        variant="caption"
                        sx={{
                          fontFamily: 'monospace',
                          color: 'rgba(255, 255, 255, 0.4)',
                          fontSize: '0.75rem',
                        }}
                      >
                        {incident.id}
                      </Typography>
                    </Box>

                    <Typography
                      variant="caption"
                      sx={{ color: 'text.secondary', whiteSpace: 'nowrap', fontSize: '0.78rem' }}
                    >
                      {formatTimestamp(incident.created_at)}
                    </Typography>
                  </Box>

                  {/* Alert Title & Summary */}
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#f1f5f9', mb: 0.5 }}>
                    {incident.alertname}
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      color: 'text.secondary',
                      mb: 1.5,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                    }}
                  >
                    {incident.summary || incident.description || 'Grafana metric threshold breached.'}
                  </Typography>

                  {/* Card Footer */}
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      pt: 1.2,
                      borderTop: '1px solid rgba(255, 255, 255, 0.05)',
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        color: incident.status === 'COMPLETED' ? '#10b981' : 'text.secondary',
                        fontWeight: 500,
                      }}
                    >
                      {incident.status === 'COMPLETED'
                        ? '✓ Root cause and remediation available'
                        : incident.status === 'INVESTIGATING'
                        ? 'Agent is inspecting Loki logs & Kubernetes state...'
                        : 'Review failure details'}
                    </Typography>

                    <Button
                      size="small"
                      endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
                      sx={{
                        color: '#00e5ff',
                        fontWeight: 650,
                        fontSize: '0.8rem',
                        p: 0,
                        '&:hover': { bgcolor: 'transparent', color: '#67e8f9' },
                      }}
                    >
                      View Report
                    </Button>
                  </Box>
                </Paper>
              </motion.div>
            ))}
          </AnimatePresence>
        </Box>
      )}
    </Box>
  );
}
