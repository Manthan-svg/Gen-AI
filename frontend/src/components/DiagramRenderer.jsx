import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  fontFamily: 'inherit',
});

function MermaidDiagram({ code, title }) {
  const ref = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const id = `mermaid-${Math.random().toString(36).slice(2)}`;
    mermaid.render(id, code)
      .then(({ svg }) => {
        if (ref.current) ref.current.innerHTML = svg;
      })
      .catch(() => setError('Could not render diagram.'));
  }, [code]);

  if (error) return <p className="text-xs text-red-400">{error}</p>;
  return <div ref={ref} className="overflow-x-auto" />;
}

function PlantUMLDiagram({ imageUrl, code, title }) {
  const [fullscreen, setFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);

  const copyCode = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <>
      <div className="relative group cursor-pointer" onClick={() => setFullscreen(true)}>
        <img
          src={imageUrl}
          alt={title}
          className="max-w-full rounded-lg border border-slate-700 bg-white"
          onError={(e) => { e.target.style.display = 'none'; }}
        />
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 rounded-lg transition flex items-center justify-center opacity-0 group-hover:opacity-100">
          <span className="text-xs text-white bg-black/60 px-2 py-1 rounded">Click to expand</span>
        </div>
      </div>
      <button onClick={copyCode} className="mt-1 text-[10px] text-slate-500 hover:text-slate-300 transition">
        {copied ? '✓ Copied' : 'Copy PlantUML code'}
      </button>

      {fullscreen && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
             onClick={() => setFullscreen(false)}>
          <div className="relative max-w-5xl max-h-full overflow-auto bg-white rounded-xl p-4"
               onClick={e => e.stopPropagation()}>
            <button onClick={() => setFullscreen(false)}
                    className="absolute top-2 right-2 text-slate-500 hover:text-slate-800 text-lg">✕</button>
            <p className="text-xs text-slate-500 mb-2 font-medium">{title}</p>
            <img src={imageUrl} alt={title} className="max-w-full" />
          </div>
        </div>
      )}
    </>
  );
}

export default function DiagramRenderer({ diagrams = [] }) {
  if (!diagrams || diagrams.length === 0) return null;

  return (
    <div className="mt-4 space-y-4">
      {diagrams.map((diagram, i) => (
        <div key={i} className="rounded-xl border border-slate-700 bg-slate-900/60 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 mb-3">
            {diagram.type === 'plantuml' ? 'PlantUML Diagram' : 'Mermaid Diagram'} — {diagram.title}
          </p>
          {diagram.type === 'plantuml' ? (
            <PlantUMLDiagram
              imageUrl={diagram.imageUrl}
              code={diagram.code}
              title={diagram.title}
            />
          ) : (
            <MermaidDiagram code={diagram.code} title={diagram.title} />
          )}
        </div>
      ))}
    </div>
  );
}