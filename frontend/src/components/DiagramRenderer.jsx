import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

//Global Initialization...
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  fontFamily: 'inherit',
});

function MermaidDiagram({ code, title }) {
    const [svg, setSvg] = useState('');
    const [error, setError] = useState(null);
    const [fullscreen, setFullscreen] = useState(false);
    const [scale, setScale] = useState(1);
    const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  
    // Use refs for drag tracking — avoids re-renders during mouse move
    const isDragging = useRef(false);
    const lastMouse = useRef({ x: 0, y: 0 });
  
    useEffect(() => {
      const id = `mermaid-${Math.random().toString(36).slice(2)}`;
      mermaid.render(id, code)
        .then(({ svg: rawSvg }) => {
          const responsive = rawSvg
            .replace(/width="[^"]*"/, 'width="100%"')
            .replace(/height="[^"]*"/, 'height="100%"');
          setSvg(responsive);
        })
        .catch(() => setError('Could not render diagram.'));
    }, [code]);
  
    // Reset zoom + pan when modal closes
    useEffect(() => {
      if (!fullscreen) {
        setScale(1);
        setPanOffset({ x: 0, y: 0 });
      }
    }, [fullscreen]);
  
    const handleMouseDown = (e) => {
      // Only trigger on left click
      if (e.button !== 0) return;
      isDragging.current = true;
      lastMouse.current = { x: e.clientX, y: e.clientY };
      e.preventDefault();
    };
  
    const handleMouseMove = (e) => {
      if (!isDragging.current) return;
      const dx = e.clientX - lastMouse.current.x;
      const dy = e.clientY - lastMouse.current.y;
      lastMouse.current = { x: e.clientX, y: e.clientY };
      setPanOffset(prev => ({ x: prev.x + dx, y: prev.y + dy }));
    };
  
    const handleMouseUp = () => {
      isDragging.current = false;
    };
  
    if (error) return <p className="text-xs text-red-400">{error}</p>;
  
    return (
      <>
        {/* Inline preview */}
        <div
          className="relative group cursor-pointer overflow-x-auto"
          onClick={() => setFullscreen(true)}
        >
          <div
            className="pointer-events-none w-full"
            dangerouslySetInnerHTML={{ __html: svg }}
          />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 rounded-lg transition flex items-center justify-center opacity-0 group-hover:opacity-100">
            <span className="text-xs text-white bg-black/60 px-2 py-1 rounded">
              Click to expand
            </span>
          </div>
        </div>
  
        {/* Fullscreen modal */}
        {fullscreen && (
          <div
            className="fixed inset-0 z-50 bg-black/90 flex flex-col"
            onClick={() => setFullscreen(false)}
          >
            {/* Top bar */}
            <div
              className="flex items-center justify-between px-6 py-3 border-b border-slate-700 shrink-0"
              onClick={(e) => e.stopPropagation()}
            >
              <p className="text-xs text-slate-400 font-medium">{title}</p>
  
              {/* Zoom controls */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setScale(s => Math.max(0.5, +(s - 0.25).toFixed(2)))}
                  className="w-7 h-7 rounded bg-slate-700 hover:bg-slate-600 text-white text-sm font-bold transition flex items-center justify-center"
                >−</button>
                <span className="text-xs text-slate-400 w-10 text-center">
                  {Math.round(scale * 100)}%
                </span>
                <button
                  onClick={() => setScale(s => Math.min(3, +(s + 0.25).toFixed(2)))}
                  className="w-7 h-7 rounded bg-slate-700 hover:bg-slate-600 text-white text-sm font-bold transition flex items-center justify-center"
                >+</button>
                <button
                  onClick={() => { setScale(1); setPanOffset({ x: 0, y: 0 }); }}
                  className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 transition ml-1"
                >Reset</button>
              </div>
  
              <button
                onClick={() => setFullscreen(false)}
                className="text-slate-400 hover:text-white text-lg font-bold leading-none transition"
              >✕</button>
            </div>
  
            {/* Diagram area — pan + zoom */}
            <div
              className="flex-1 overflow-hidden flex items-start justify-center p-8"
              onClick={(e) => e.stopPropagation()}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={(e) => {
                e.preventDefault();
                setScale(s => {
                  const next = s - e.deltaY * 0.001;
                  return Math.min(3, Math.max(0.5, +next.toFixed(2)));
                });
              }}
              style={{
                cursor: isDragging.current ? 'grabbing' : 'grab',
              }}
            >
              <div
                style={{
                  transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${scale})`,
                  transformOrigin: 'top center',
                  transition: isDragging.current ? 'none' : 'transform 0.15s ease',
                  width: '100%',
                  userSelect: 'none',
                }}
                dangerouslySetInnerHTML={{ __html: svg }}
              />
            </div>
  
            {/* Hint bar */}
            <div className="text-center pb-3 shrink-0">
              <span className="text-[11px] text-slate-600">
                Drag to pan · Scroll to zoom · Click outside to close
              </span>
            </div>
          </div>
        )}
      </>
    );
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