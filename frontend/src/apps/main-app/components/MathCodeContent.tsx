/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useMemo } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";
import { clsx } from "clsx";

export interface MathCodeContentProps {
  content: string;
  className?: string;
  inline?: boolean;
}

type Segment =
  | { type: "text"; value: string }
  | { type: "code-block"; lang: string; value: string }
  | { type: "inline-code"; value: string }
  | { type: "math-block"; value: string }
  | { type: "math-inline"; value: string };

/**
 * Tokenize markdown-like content containing fenced code blocks (```...```),
 * display math ($$...$$), inline code (`...`), and inline math ($...$).
 */
function parseSegments(source: string): Segment[] {
  const segments: Segment[] = [];
  const tokenRegex =
    /```([a-zA-Z0-9_-]*)\n?([\s\S]*?)```|\$\$([\s\S]+?)\$\$|`([^`\n]+)`|\$([^\s$](?:[^$\n]*?[^\s$])?)\$/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = tokenRegex.exec(source)) !== null) {
    if (match.index > lastIndex) {
      segments.push({
        type: "text",
        value: source.slice(lastIndex, match.index),
      });
    }

    if (match[2] !== undefined) {
      segments.push({
        type: "code-block",
        lang: match[1] || "",
        value: match[2].replace(/\n$/, ""),
      });
    } else if (match[3] !== undefined) {
      segments.push({
        type: "math-block",
        value: match[3].trim(),
      });
    } else if (match[4] !== undefined) {
      segments.push({
        type: "inline-code",
        value: match[4],
      });
    } else if (match[5] !== undefined) {
      segments.push({
        type: "math-inline",
        value: match[5].trim(),
      });
    }

    lastIndex = tokenRegex.lastIndex;
  }

  if (lastIndex < source.length) {
    segments.push({
      type: "text",
      value: source.slice(lastIndex),
    });
  }

  return segments;
}

function renderKatexHtml(expr: string, displayMode: boolean): string {
  try {
    return katex.renderToString(expr, {
      displayMode,
      throwOnError: false,
      strict: false,
    });
  } catch {
    return expr;
  }
}

export const MathCodeContent: React.FC<MathCodeContentProps> = ({
  content,
  className,
  inline = false,
}) => {
  const segments = useMemo(() => parseSegments(content ?? ""), [content]);

  const Wrapper = inline ? "span" : "div";

  return (
    <Wrapper
      className={clsx(
        "font-mm-ui text-mm-text break-words",
        !inline && "space-y-2 leading-relaxed",
        className
      )}
    >
      {segments.map((seg, idx) => {
        if (seg.type === "text") {
          return (
            <span key={idx} className="whitespace-pre-wrap">
              {seg.value}
            </span>
          );
        }

        if (seg.type === "inline-code") {
          return (
            <code
              key={idx}
              className="rounded-mm-tag bg-mm-divider px-1.5 py-0.5 font-mm-mono text-[0.875em] text-mm-heading"
            >
              {seg.value}
            </code>
          );
        }

        if (seg.type === "code-block") {
          return (
            <div
              key={idx}
              className="my-2 overflow-hidden rounded-mm-panel border border-mm-border bg-[#f8fafc]"
            >
              {seg.lang && (
                <div className="border-b border-mm-divider bg-mm-divider/60 px-3 py-1 font-mm-mono text-[11px] uppercase tracking-wide text-mm-text-muted">
                  {seg.lang}
                </div>
              )}
              <pre className="overflow-x-auto p-3.5 font-mm-mono text-xs leading-6 text-mm-heading">
                <code>{seg.value}</code>
              </pre>
            </div>
          );
        }

        if (seg.type === "math-block") {
          const html = renderKatexHtml(seg.value, true);
          return (
            <div
              key={idx}
              className="my-2 overflow-x-auto py-1"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          );
        }

        const html = renderKatexHtml(seg.value, false);
        return (
          <span
            key={idx}
            className="inline-block align-middle"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        );
      })}
    </Wrapper>
  );
};
