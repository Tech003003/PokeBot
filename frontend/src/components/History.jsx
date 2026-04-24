import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

const OUTCOME_COLOR = {
  NOTIFIED: "text-[#A1A1AA] border-white/10",
  IN_CART: "text-[#007AFF] border-[#007AFF]/30",
  CHECKOUT_READY: "text-[#FFCC00] border-[#FFCC00]/30",
  PURCHASED: "text-[#00FF66] border-[#00FF66]/30",
  DROP_HIT: "text-[#00FF66] border-[#00FF66]/30",
  PRICE_SKIP: "text-[#FFCC00] border-[#FFCC00]/30",
  WAITLISTED: "text-[#FFCC00] border-[#FFCC00]/30",
  FAILED: "text-[#FF3B30] border-[#FF3B30]/30",
};

export default function History() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    const load = () => api.get("/history").then((r) => setRows(r.data));
    load(); const t = setInterval(load, 4000); return () => clearInterval(t);
  }, []);
  return (
    <div className="bg-[#121214] border border-[#27272a] rounded-none">
      <div className="p-4 border-b border-[#27272a]">
        <h3 className="text-xs font-black tracking-[0.2em] uppercase text-[#A1A1AA]" style={{fontFamily:"'Chivo', sans-serif"}}>Purchase History · {rows.length}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] font-black tracking-[0.1em] text-[#A1A1AA] uppercase border-b border-[#27272a]">
              <th className="text-left p-3">When</th><th className="text-left p-3">Product</th><th className="text-left p-3">Site</th><th className="text-right p-3">Price</th><th className="text-left p-3">Outcome</th><th className="text-left p-3">Note</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={6} className="p-6 text-center text-[#52525B]">No history yet.</td></tr>}
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-[#27272a]/50">
                <td className="p-3 font-mono text-[11px] text-[#A1A1AA]">{new Date(r.created_at).toLocaleString()}</td>
                <td className="p-3">{r.name}</td>
                <td className="p-3 font-mono text-xs text-[#A1A1AA]">[ {r.site} ]</td>
                <td className="p-3 font-mono text-right text-white">{r.price ? `$${Number(r.price).toFixed(2)}` : "—"}</td>
                <td className="p-3"><span className={`inline-flex px-2 py-0.5 border text-[10px] font-black uppercase tracking-wider ${OUTCOME_COLOR[r.outcome] || "text-[#A1A1AA] border-white/10"}`}>{r.outcome}</span></td>
                <td className="p-3 text-xs text-[#A1A1AA]">{r.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
