import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DiagramRenderer from './DiagramRenderer';

export default function MarkdownRenderer({ content, diagrams= [] }) {
  const text = String(content ?? '').trim();
  const hasText = Boolean(text);
  const hasDiagrams = Array.isArray(diagrams) && diagrams.length > 0;

  if (!hasText && !hasDiagrams) return null;

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
    </div>
  );
}
