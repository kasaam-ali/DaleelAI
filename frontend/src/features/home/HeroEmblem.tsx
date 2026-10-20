/** CSS 3D statute stack with a verified seal (SPEC §5.1). Decorative; static under reduced motion with the same DOM. */

export default function HeroEmblem() {
  return (
    <div className="emblem" aria-hidden="true" data-testid="hero-emblem">
      <div className="eshadow" />
      <div className="float">
        <div className="stack">
          <div className="sheet" />
          <div className="sheet" />
          <div className="sheet">
            <div className="sec">§ 1XX</div>
            <div className="ln" style={{ marginTop: 16 }} />
            <div className="ln hl" />
            <div className="ln" style={{ width: "70%" }} />
            <div className="ln" />
            <div className="ln" style={{ width: "55%" }} />
            <div className="seal">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3l7 3v5c0 4.4-3 8.3-7 9.5C8 19.3 5 15.4 5 11V6z" />
                <path d="m9 12 2 2 4-4" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
