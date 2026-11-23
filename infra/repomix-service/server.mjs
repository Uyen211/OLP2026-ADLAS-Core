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

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'adlas-repomix-service',
    timestamp: new Date().toISOString()
  });
});

/**
 * Endpoint POST /api/v1/pack
 * Payload:
 *   - source_path?: string (path to directory containing unzipped code)
 *   - git_url?: string (public git repo to clone and pack)
 *   - max_tokens?: number (default: 2000)
 */
app.post('/api/v1/pack', async (req, res) => {
  const { source_path, git_url, max_tokens = 2000 } = req.body;
  let targetDir = source_path;
  let isTempGit = false;

  try {
    if (git_url) {
      // Validate git URL
      if (!git_url.startsWith('http://') && !git_url.startsWith('https://')) {
        return res.status(400).json({ error: 'Invalid git URL. Only HTTP/HTTPS is allowed.' });
      }
      isTempGit = true;
      targetDir = fs.mkdtempSync(path.join(os.tmpdir(), 'repomix-git-'));
      // Shallow clone with depth 1
      execSync(`git clone --depth 1 --single-branch "${git_url}" "${targetDir}"`, {
        timeout: 25000,
        stdio: 'pipe'
      });
    }

    if (!targetDir || !fs.existsSync(targetDir)) {
      return res.status(400).json({ error: `Target directory not found: ${targetDir}` });
    }

    // Try using repomix library pack() function
    let packedContent = '';
    let fileList = [];
    try {
      const { pack } = await import('repomix');
      const packResult = await pack(targetDir, {
        style: 'xml',
        removeComments: true,
        outputShowLineNumbers: false,
        securityCheck: true
      });
      packedContent = packResult?.content || '';
      fileList = packResult?.files || [];
    } catch (packErr) {
      // Fallback: If pack() export signature differs or repomix CLI is present
      try {
        const outXml = path.join(targetDir, 'repomix-output.xml');
        execSync(`npx repomix "${targetDir}" --style xml --remove-comments --output "${outXml}"`, {
          timeout: 30000,
          stdio: 'pipe'
        });
        if (fs.existsSync(outXml)) {
          packedContent = fs.readFileSync(outXml, 'utf-8');
          fs.unlinkSync(outXml);
        }
      } catch (cliErr) {
        // Fallback: Custom lightweight code gatherer if repomix throws
        packedContent = fallbackDirectoryScan(targetDir);
      }
    }

    // Enforce token budget (approx 4 chars per token)
    const charLimit = max_tokens * 4;
    let trimmedContent = packedContent;
    if (trimmedContent.length > charLimit) {
      trimmedContent = trimmedContent.slice(0, charLimit) + '\n<!-- [TRUNCATED DUE TO TOKEN BUDGET LIMIT] -->\n</repository>';
    }

    const estimatedTokens = Math.ceil(trimmedContent.length / 4);

    return res.json({
      success: true,
      file_count: fileList.length,
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
  const ignoreDirs = new Set(['node_modules', '.git', 'venv', '__pycache__', 'dist', 'build', '.idea', '.vscode']);
  const allowedExts = new Set(['.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.java', '.cpp', '.c', '.sql', '.json', '.md']);
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
            result += `  <file path="${path.relative(dirPath, filePath)}">\n${content.slice(0, 1500)}\n  </file>\n`;
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
