// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import express from 'express';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { execSync } from 'child_process';

const app = express();
app.use(express.json({ limit: '50mb' }));

const PORT = process.env.PORT || 3000;

const DEFAULT_IGNORE_PATTERNS = [
  '**/node_modules/**',
  '**/.git/**',
  '**/venv/**',
  '**/__pycache__/**',
  '**/dist/**',
  '**/build/**',
  '**/coverage/**',
  '**/package-lock.json',
  '**/pnpm-lock.yaml',
  '**/yarn.lock',
  '**/*.lock',
  '**/*.css',
  '**/*.scss',
  '**/*.svg',
  '**/*.png',
  '**/*.jpg',
  '**/migrations/**',
  '**/tests/**',
  '**/*.test.*',
  '**/*.spec.*'
];

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'adlas-repomix-service',
    timestamp: new Date().toISOString()
  });
});

/**
 * Keep <directory_structure> and select most-active files from the bottom of Repomix output
 * (since Repomix sorts files in ascending order of git change count).
 */
function trimXmlKeepingActiveFiles(rawXml, maxTokens) {
  const cleaned = rawXml
    .replace(/<file_summary>[\s\S]*?<\/file_summary>\s*/i, '')
    .replace(/^This file is a merged representation[\s\S]*?(?=<directory_structure>|<files>|<repository>)/i, '')
    .trim();

  const charLimit = maxTokens * 4;
  if (cleaned.length <= charLimit) {
    return cleaned;
  }

  const dirMatch = cleaned.match(/<directory_structure>[\s\S]*?<\/directory_structure>/i);
  const dirBlock = dirMatch ? dirMatch[0] + '\n\n' : '';
  const fileMatches = cleaned.match(/<file\s+path="[^"]+">[\s\S]*?<\/file>/g) || [];

  if (fileMatches.length === 0) {
    return cleaned.slice(0, charLimit) + '\n<!-- [TRUNCATED DUE TO TOKEN BUDGET] -->';
  }

  // Reverse order so files with highest Git change counts are prioritized first
  const selected = [];
  let usedChars = dirBlock.length + 64;
  for (let i = fileMatches.length - 1; i >= 0; i--) {
    const block = fileMatches[i];
    if (usedChars + block.length + 2 <= charLimit) {
      selected.unshift(block);
      usedChars += block.length + 2;
    } else if (selected.length === 0) {
      const available = Math.max(500, charLimit - usedChars);
      selected.unshift(block.slice(0, available) + '\n<!-- [TRUNCATED] -->\n</file>');
      break;
    }
  }

  return `${dirBlock}<files>\n${selected.join('\n')}\n</files>`;
}

/**
 * Endpoint POST /api/v1/pack
 * Payload:
 *   - source_path?: string (path to directory containing unzipped code)
 *   - git_url?: string (public git repo to clone and pack)
 *   - max_tokens?: number (default: 45000)
 */
app.post('/api/v1/pack', async (req, res) => {
  const { source_path, git_url, max_tokens = 45000 } = req.body;
  let targetDir = source_path;
  let isTempGit = false;

  try {
    if (git_url) {
      if (!git_url.startsWith('http://') && !git_url.startsWith('https://')) {
        return res.status(400).json({ error: 'Invalid git URL. Only HTTP/HTTPS is allowed.' });
      }
      isTempGit = true;
      targetDir = fs.mkdtempSync(path.join(os.tmpdir(), 'repomix-git-'));
      execSync(`git clone --depth 50 --single-branch "${git_url}" "${targetDir}"`, {
        timeout: 30000,
        stdio: 'pipe'
      });
    }

    if (!targetDir || !fs.existsSync(targetDir)) {
      return res.status(400).json({ error: `Target directory not found: ${targetDir}` });
    }

    let packedContent = '';
    let totalFiles = 0;

    try {
      const { runCli } = await import('repomix');
      const outXml = path.join(os.tmpdir(), `repomix-${Date.now()}-${Math.random().toString(36).slice(2)}.xml`);
      const cliRes = await runCli([targetDir], process.cwd(), {
        output: outXml,
        style: 'xml',
        compress: true,
        removeComments: true,
        removeEmptyLines: true,
        securityCheck: true,
        ignore: DEFAULT_IGNORE_PATTERNS.join(','),
        quiet: true
      });
      if (fs.existsSync(outXml)) {
        packedContent = fs.readFileSync(outXml, 'utf-8');
        fs.unlinkSync(outXml);
      }
      totalFiles = cliRes?.packResult?.totalFiles || (packedContent.match(/<file\s+path="/g) || []).length;
    } catch (packErr) {
      try {
        const outXml = path.join(os.tmpdir(), `repomix-cli-${Date.now()}.xml`);
        execSync(
          `npx repomix "${targetDir}" --style xml --compress --remove-comments --remove-empty-lines --ignore "${DEFAULT_IGNORE_PATTERNS.join(',')}" --output "${outXml}"`,
          { timeout: 45000, stdio: 'pipe' }
        );
        if (fs.existsSync(outXml)) {
          packedContent = fs.readFileSync(outXml, 'utf-8');
          fs.unlinkSync(outXml);
        }
        totalFiles = (packedContent.match(/<file\s+path="/g) || []).length;
      } catch (cliErr) {
        packedContent = fallbackDirectoryScan(targetDir);
        totalFiles = (packedContent.match(/<file\s+path="/g) || []).length;
      }
    }

    const trimmedContent = trimXmlKeepingActiveFiles(packedContent, max_tokens);
    const estimatedTokens = Math.ceil(trimmedContent.length / 4);

    return res.json({
      success: true,
      file_count: totalFiles,
      estimated_tokens: estimatedTokens,
      packed_xml: trimmedContent
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      error: err.message || 'Error occurred while packing source code.'
    });
  } finally {
    if (isTempGit && targetDir && fs.existsSync(targetDir)) {
      try {
        fs.rmSync(targetDir, { recursive: true, force: true });
      } catch (_) {
        // ignore cleanup error
      }
    }
  }
});

function fallbackDirectoryScan(dirPath) {
  const ignoreDirs = new Set(['node_modules', '.git', 'venv', '__pycache__', 'dist', 'build', '.idea', '.vscode', 'tests']);
  const allowedExts = new Set(['.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.sql', '.go']);
  let result = '<repository>\n';

  function walk(current) {
    const entries = fs.readdirSync(current, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.isDirectory()) {
        if (!ignoreDirs.has(entry.name)) {
          walk(path.join(current, entry.name));
        }
      } else if (entry.isFile()) {
        const ext = path.extname(entry.name).toLowerCase();
        if (allowedExts.has(ext)) {
          const filePath = path.join(current, entry.name);
          try {
            const content = fs.readFileSync(filePath, 'utf-8');
            result += `  <file path="${path.relative(dirPath, filePath)}">\n${content.slice(0, 3000)}\n  </file>\n`;
          } catch (_) {}
        }
      }
    }
  }

  try {
    walk(dirPath);
  } catch (_) {}

  result += '</repository>';
  return result;
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Repomix Container Microservice running on port ${PORT}`);
});
