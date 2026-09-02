
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
