// Tailwind only generates classes it can see as full strings, so keep these literal (no template-built class names).
const STYLES = {
  HIGH:   'bg-red-100 text-red-800 ring-red-600/20',
  MEDIUM: 'bg-amber-100 text-amber-800 ring-amber-600/20',
  LOW:    'bg-emerald-100 text-emerald-800 ring-emerald-600/20',
};

/** Colour + text label, so the level is never conveyed by colour alone. */
export default function RiskBadge({ level }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${STYLES[level] ?? STYLES.LOW}`}>
      {level}
    </span>
  );
}
