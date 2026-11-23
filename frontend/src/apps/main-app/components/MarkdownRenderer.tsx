/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = "" }) => {
  if (!content) return null;

  const lines = content.split("\n");
  const renderedElements: React.ReactNode[] = [];
  let currentList: { type: "ul" | "ol"; items: string[] } | null = null;
  let elementKey = 0;

  const flushList = () => {
    if (!currentList) return;
    const ListTag = currentList.type;
    renderedElements.push(
      <ListTag
        key={`list-${elementKey++}`}
        className={ListTag === "ul" ? "list-disc pl-5 space-y-1 my-3 text-sm text-[#374151]" : "list-decimal pl-5 space-y-1 my-3 text-sm text-[#374151]"}
      >
        {currentList.items.map((item, idx) => (
          <li key={idx} dangerouslySetInnerHTML={{ __html: formatInline(item) }} />
        ))}
      </ListTag>
    );
    currentList = null;
  };

  const formatInline = (text: string): string => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-mm-dark">$1</strong>')
      .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-gray-100 text-xs font-mm-mono text-mm-dark border border-gray-200">$1</code>');
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (!line) {
      flushList();
      continue;
    }

    // Check headings
    if (line.startsWith("### ")) {
      flushList();
      renderedElements.push(
        <h3 key={`h3-${elementKey++}`} className="font-mm-display text-base font-semibold text-mm-dark mt-5 mb-2">
          {line.replace("### ", "")}
        </h3>
      );
      continue;
    }

    if (line.startsWith("## ")) {
      flushList();
      renderedElements.push(
        <h2 key={`h2-${elementKey++}`} className="font-mm-display text-lg font-bold text-mm-dark mt-6 mb-2.5 pb-1 border-b border-gray-100">
          {line.replace("## ", "")}
        </h2>
      );
      continue;
    }

    if (line.startsWith("# ")) {
      flushList();
      renderedElements.push(
        <h1 key={`h1-${elementKey++}`} className="font-mm-display text-xl font-bold text-mm-dark mt-6 mb-3">
          {line.replace("# ", "")}
        </h1>
      );
      continue;
    }

    // Check unordered list
    if (line.startsWith("- ") || line.startsWith("* ")) {
      const itemText = line.substring(2).trim();
      if (!currentList || currentList.type !== "ul") {
        flushList();
        currentList = { type: "ul", items: [itemText] };
      } else {
        currentList.items.push(itemText);
      }
      continue;
    }

    // Check ordered list
    const numMatch = line.match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      const itemText = numMatch[2].trim();
      if (!currentList || currentList.type !== "ol") {
        flushList();
        currentList = { type: "ol", items: [itemText] };
      } else {
        currentList.items.push(itemText);
      }
      continue;
    }

    // Regular paragraph
    flushList();
    renderedElements.push(
      <p
        key={`p-${elementKey++}`}
        className="my-2.5 text-sm leading-relaxed text-[#374151]"
        dangerouslySetInnerHTML={{ __html: formatInline(line) }}
      />
    );
  }

  flushList();

  return <div className={`font-mm-ui ${className}`}>{renderedElements}</div>;
};
