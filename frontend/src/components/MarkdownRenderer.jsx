import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DiagramRenderer from './DiagramRenderer';

function truncateExcerpt(text, limit = 100) {
  const value = String(text ?? '').trim().replace(/\s+/g, ' ');
  if (!value) return '';
  if (value.length <= limit) return value;
  return `${value.slice(0, limit).trimEnd()}...`;
}

function groupCitationsBySource(citations) {
  const groups = [];
  const bySource = new Map();

  for (const citation of Array.isArray(citations) ? citations : []) {
    const sourceName = String(citation?.sourceName ?? 'Unknown source').trim() || 'Unknown source';
    const existing = bySource.get(sourceName);

    if (!existing) {
      const group = {
        index: groups.length + 1,
        sourceName,
        pages: Number.isInteger(citation?.page) ? [citation.page] : [],
        excerpt: truncateExcerpt(citation?.snippet),
        count: 1,
        rawIndexes: [citation?.index].filter(Number.isInteger),
      };
      bySource.set(sourceName, group);
      groups.push(group);
      continue;
    }

    existing.count += 1;
    if (Number.isInteger(citation?.index)) {
      existing.rawIndexes.push(citation.index);
    }
    if (Number.isInteger(citation?.page) && !existing.pages.includes(citation.page)) {
      existing.pages.push(citation.page);
    }
    if (!existing.excerpt && citation?.snippet) {
      existing.excerpt = truncateExcerpt(citation.snippet);
    }
  }

  return groups;
}

function remapCitationMarkers(content, groups) {
  const indexMap = new Map();

  for (const group of groups) {
    for (const rawIndex of group.rawIndexes) {
      indexMap.set(String(rawIndex), String(group.index));
    }
  }

  return String(content ?? '').replace(/\[(\d+)\]/g, (match, index) => {
    if (!indexMap.has(index)) return match;
    return `[${indexMap.get(index)}]`;
  });
}

function formatPages(pages) {
  if (!Array.isArray(pages) || pages.length === 0) return null;
  const sorted = [...pages].sort((a, b) => a - b);
  if (sorted.length === 1) return `Page ${sorted[0]}`;
  return `Pages ${sorted.join(', ')}`;
}

export default function MarkdownRenderer({ content, citations = [],diagrams= [] }) {
  const sourceCitations = groupCitationsBySource(citations);
  const text = remapCitationMarkers(content, sourceCitations).trim();
  const hasText = Boolean(text);
  const hasDiagrams = Array.isArray(diagrams) && diagrams.length > 0;
  const hasSources = sourceCitations.length > 0;

  if (!hasText && !hasDiagrams && !hasSources) return null;

  return (
    <div className="markdown-content text-sm leading-relaxed text-slate-200">
      {hasText && (
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="mb-4 border-b border-slate-700 pb-2 text-xl font-semibold text-white">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="mb-3 mt-5 border-b border-slate-700 pb-2 text-lg font-semibold text-white">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="mb-3 mt-4 text-base font-semibold text-white">
                {children}
              </h3>
            ),
            p: ({ children }) => (
              <p className="mb-3 whitespace-pre-wrap last:mb-0">
                {children}
              </p>
            ),
            ul: ({ children }) => (
              <ul className="mb-3 list-disc space-y-1 pl-5 marker:text-slate-400 last:mb-0">
                {children}
              </ul>
            ),
            ol: ({ children }) => (
              <ol className="mb-3 list-decimal space-y-1 pl-5 marker:text-slate-400 last:mb-0">
                {children}
              </ol>
            ),
            li: ({ children }) => (
              <li className="pl-1">
                {children}
              </li>
            ),
            blockquote: ({ children }) => (
              <blockquote className="mb-3 border-l-4 border-slate-600 pl-4 italic text-slate-300 last:mb-0">
                {children}
              </blockquote>
            ),
            a: ({ href, children }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-sky-300 underline underline-offset-2 transition hover:text-sky-200"
              >
                {children}
              </a>
            ),
            hr: () => <hr className="my-4 border-slate-700" />,
            strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
            em: ({ children }) => <em className="italic text-slate-100">{children}</em>,
            pre: ({ children }) => (
              <pre className="mb-3 overflow-x-auto rounded-xl bg-slate-950 p-4 text-[13px] text-slate-100 last:mb-0">
                {children}
              </pre>
            ),
            code: ({ inline, children }) =>
              inline ? (
                <code className="rounded-md bg-slate-900 px-1.5 py-0.5 font-mono text-[13px] text-sky-200">
                  {children}
                </code>
              ) : (
                <code className="font-mono text-[13px] text-slate-100">
                  {children}
                </code>
              ),
            table: ({ children }) => (
              <div className="mb-3 overflow-x-auto last:mb-0">
                <table className="min-w-full border-collapse text-left text-sm">
                  {children}
                </table>
              </div>
            ),
            thead: ({ children }) => <thead className="bg-slate-900/80">{children}</thead>,
            tbody: ({ children }) => <tbody className="divide-y divide-slate-700">{children}</tbody>,
            tr: ({ children }) => <tr className="align-top even:bg-slate-900/30">{children}</tr>,
            th: ({ children }) => (
              <th className="border border-slate-700 px-3 py-2 font-semibold text-white">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="border border-slate-700 px-3 py-2 text-slate-200">
                {children}
              </td>
            ),
          }}
        >
          {text}
        </ReactMarkdown>
      )}

      <DiagramRenderer diagrams={diagrams} />

      {hasSources && (
        <div className="mt-4 rounded-xl border border-slate-700/80 bg-slate-900/60 p-3">
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
            Sources
          </p>
          <div className="space-y-3">
            {sourceCitations.map((citation) => {
              const pageLabel = formatPages(citation.pages);
              return (
                <div
                  key={`${citation.index}-${citation.sourceName}`}
                  className="rounded-lg border border-slate-700/60 bg-slate-950/60 p-3"
                >
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300">
                    <p className="font-medium text-slate-200">
                      [{citation.index}] {citation.sourceName}
                    </p>
                    {pageLabel ? (
                      <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-400">
                        {pageLabel}
                      </span>
                    ) : null}
                    <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-400">
                      {citation.count} {citation.count === 1 ? 'passage' : 'passages'}
                    </span>
                  </div>
                  {citation.excerpt && (
                    <p className="mt-2 text-xs leading-relaxed text-slate-400">
                      "{citation.excerpt}"
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
