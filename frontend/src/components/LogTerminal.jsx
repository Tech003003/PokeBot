import React, { useEffect, useRef, useState } from "react";
import { wsLogsUrl, LOG_COLORS } from "@/lib/api";

export default function LogTerminal() {
  const [lines, setLines] = useState([]);
  const boxRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    let retry = 0;
    let alive = true;
    const connect = () => {
      const ws = new WebSocket(wsLogsUrl());
      wsRef.current = ws;
      ws.onmessage = (e) => {
        try {
          const entry = JSON.parse(e.data);
          if (entry.level === "PING") return;
          setLines((p) => {
            const next = [...p, entry];
            return next.length > 400 ? next.slice(-400) : next;
          });
        } catch {}
      };
      ws.onclose = () => {
        if (!alive) return;
        retry = Math.min(retry + 1, 5);
        setTimeout(connect, 500 * retry);
      };
      ws.onerror = () => ws.close();
    };
    connect();
    return () => { alive = false; try { wsRef.current?.close(); } catch {} };
  }, []);

  useEffect(() => {
    if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight;
  }, [lines]);

  return (
    <div
      ref={boxRef}
      data-testid="log-terminal"
      className="bg-[#050505] border border-[#27272a] p-3 font-mono text-[11px] h-[320px] overflow-y-auto flex flex-col gap-[2px]"
      style={{ fontFamily: "'JetBrains Mono', monospace" }}
    >
      {lines.length === 0 && (
        <div className="text-[#52525B]">[ awaiting events — connect Brave and start a watch ]</div>
      )}
      {lines.map((l, i) => (
        <div key={i} className={LOG_COLORS[l.level] || "text-[#A1A1AA]"}>
          <span className="text-[#52525B]">{(l.ts || "").slice(11, 19)}</span>{" "}
          <span className="text-[#3f3f46]">[{l.level}]</span>{" "}
          {l.msg}
        </div>
      ))}
    </div>
  );
}
