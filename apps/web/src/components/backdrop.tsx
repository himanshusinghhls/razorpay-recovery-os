/**
 * Fixed ambient layer behind all content.
 *
 * Purely decorative, so it is hidden from assistive tech and never receives
 * pointer events. All motion is CSS-driven and disabled under
 * prefers-reduced-motion (see globals.css).
 */
export function AmbientBackdrop() {
  return (
    <>
      <div className="aurora-field" aria-hidden="true">
        <div className="aurora-blob aurora-blob--brand" />
        <div className="aurora-blob aurora-blob--violet" />
        <div className="aurora-blob aurora-blob--teal" />
      </div>
      <div className="grid-veil" aria-hidden="true" />
    </>
  );
}
