'use client';

import * as React from 'react';
import { Box, Typography, IconButton, Tooltip } from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';

interface MarkdownViewProps {
  content: string;
}

export default function MarkdownView({ content }: MarkdownViewProps) {
  const [copiedIndex, setCopiedIndex] = React.useState<number | null>(null);

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Parse lines into tokens: headings, code blocks, bullet points, horizontal rules, paragraphs
  const elements = React.useMemo(() => {
    const lines = content.split('\n');
    const result: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeLanguage = '';
    let codeLines: string[] = [];
    let codeBlockIndex = 0;

    const renderInline = (text: string): React.ReactNode[] => {
      // Split on inline code (`...`) and bold (**...**)
      const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
      return parts.map((part, i) => {
        if (part.startsWith('`') && part.endsWith('`')) {
          return (
            <Box
              key={i}
              component="code"
              sx={{
                bgcolor: 'rgba(0, 229, 255, 0.1)',
                color: '#00e5ff',
                px: 0.8,
                py: 0.2,
                borderRadius: 1,
                fontSize: '0.85em',
                fontFamily: 'monospace',
                border: '1px solid rgba(0, 229, 255, 0.2)',
              }}
            >
              {part.slice(1, -1)}
            </Box>
          );
        }
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <strong key={i} style={{ color: '#f1f5f9', fontWeight: 650 }}>
              {part.slice(2, -2)}
            </strong>
          );
        }
        return part;
      });
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Code block start / end
      if (line.trim().startsWith('```')) {
        if (!inCodeBlock) {
          inCodeBlock = true;
          codeLanguage = line.trim().slice(3).trim() || 'text';
          codeLines = [];
        } else {
          inCodeBlock = false;
          const fullCode = codeLines.join('\n');
          const currentIndex = codeBlockIndex++;
          result.push(
            <Box
              key={`code-${currentIndex}`}
              sx={{
                my: 2,
                borderRadius: 2,
                bgcolor: '#090a0f',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                overflow: 'hidden',
              }}
            >
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  px: 2,
                  py: 0.8,
                  bgcolor: 'rgba(255, 255, 255, 0.03)',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    fontFamily: 'monospace',
                    textTransform: 'uppercase',
                    color: 'rgba(255, 255, 255, 0.5)',
                    fontSize: '0.72rem',
                    letterSpacing: 0.5,
                  }}
                >
                  {codeLanguage}
                </Typography>
                <Tooltip title={copiedIndex === currentIndex ? 'Copied!' : 'Copy Code'}>
                  <IconButton
                    size="small"
                    onClick={() => handleCopy(fullCode, currentIndex)}
                    sx={{ color: copiedIndex === currentIndex ? '#4caf50' : 'rgba(255, 255, 255, 0.4)' }}
                  >
                    {copiedIndex === currentIndex ? (
                      <CheckIcon sx={{ fontSize: 16 }} />
                    ) : (
                      <ContentCopyIcon sx={{ fontSize: 16 }} />
                    )}
                  </IconButton>
                </Tooltip>
              </Box>
              <Box
                component="pre"
                sx={{
                  p: 2,
                  m: 0,
                  overflowX: 'auto',
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  lineHeight: 1.5,
                  color: '#cbd5e1',
                }}
              >
                <code>{fullCode}</code>
              </Box>
            </Box>
          );
        }
        continue;
      }

      if (inCodeBlock) {
        codeLines.push(line);
        continue;
      }

      // Horizontal rule
      if (line.trim() === '---' || line.trim() === '***') {
        result.push(
          <Box
            key={`hr-${i}`}
            sx={{ my: 2.5, borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}
          />
        );
        continue;
      }

      // Headers
      if (line.startsWith('### ')) {
        result.push(
          <Typography
            key={`h3-${i}`}
            variant="h6"
            sx={{ mt: 2.5, mb: 1, color: '#38bdf8', fontWeight: 650, letterSpacing: -0.3 }}
          >
            {renderInline(line.slice(4))}
          </Typography>
        );
        continue;
      }
      if (line.startsWith('## ')) {
        result.push(
          <Typography
            key={`h2-${i}`}
            variant="h5"
            sx={{ mt: 3, mb: 1.5, color: '#f8fafc', fontWeight: 700 }}
          >
            {renderInline(line.slice(3))}
          </Typography>
        );
        continue;
      }
      if (line.startsWith('# ')) {
        result.push(
          <Typography
            key={`h1-${i}`}
            variant="h4"
            sx={{ mt: 3, mb: 2, color: '#00e5ff', fontWeight: 800 }}
          >
            {renderInline(line.slice(2))}
          </Typography>
        );
        continue;
      }

      // Lists
      if (line.trim().startsWith('* ') || line.trim().startsWith('- ')) {
        const itemContent = line.trim().slice(2);
        result.push(
          <Box key={`li-${i}`} sx={{ display: 'flex', gap: 1.5, my: 0.6, pl: 1 }}>
            <Box
              sx={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                bgcolor: 'primary.main',
                mt: 1.1,
                flexShrink: 0,
              }}
            />
            <Typography variant="body2" sx={{ color: '#cbd5e1', lineHeight: 1.6 }}>
              {renderInline(itemContent)}
            </Typography>
          </Box>
        );
        continue;
      }

      // Numbered lists
      const numMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
      if (numMatch) {
        result.push(
          <Box key={`nli-${i}`} sx={{ display: 'flex', gap: 1.5, my: 0.6, pl: 1 }}>
            <Typography
              variant="body2"
              sx={{ color: 'primary.main', fontWeight: 700, minWidth: 20 }}
            >
              {numMatch[1]}.
            </Typography>
            <Typography variant="body2" sx={{ color: '#cbd5e1', lineHeight: 1.6 }}>
              {renderInline(numMatch[2])}
            </Typography>
          </Box>
        );
        continue;
      }

      // Regular paragraph / blank line
      if (!line.trim()) {
        result.push(<Box key={`space-${i}`} sx={{ height: 8 }} />);
      } else {
        result.push(
          <Typography
            key={`p-${i}`}
            variant="body2"
            sx={{ color: '#cbd5e1', lineHeight: 1.6, my: 0.5 }}
          >
            {renderInline(line)}
          </Typography>
        );
      }
    }

    return result;
  }, [content, copiedIndex]);

  return <Box sx={{ width: '100%' }}>{elements}</Box>;
}
