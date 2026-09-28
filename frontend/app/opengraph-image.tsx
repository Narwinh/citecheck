import { ImageResponse } from "next/og";

export const alt = "CiteCheck: answers you can check";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// System serif keeps the image self-contained (no font fetch at build time).
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
          background: "#f5f1e8",
          color: "#1d1a16",
          fontFamily: "Georgia, serif",
        }}
      >
        <div style={{ display: "flex", fontSize: 26, letterSpacing: 4, color: "#6b6456", fontFamily: "monospace" }}>
          CITECHECK · VERIFIED RESEARCH
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
          <div style={{ fontSize: 96, lineHeight: 1, letterSpacing: -2 }}>Answers you can check.</div>
          <div style={{ display: "flex", fontSize: 34, color: "#585247", lineHeight: 1.35 }}>
            Every sentence cites a source, and a verifier reads it to confirm.
          </div>
        </div>
        <div style={{ display: "flex", gap: 36, fontSize: 24, fontFamily: "monospace", color: "#585247" }}>
          {[
            ["#2a9a60", "supported"],
            ["#e3a91f", "partial"],
            ["#9c2a22", "removed"],
          ].map(([color, label]) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 18, height: 18, borderRadius: 4, background: color }} />
              {label}
            </div>
          ))}
        </div>
      </div>
    ),
    size,
  );
}
