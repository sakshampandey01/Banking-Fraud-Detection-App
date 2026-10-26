/** Shows what is wrong when the backend is up but cannot score yet (model/preprocessing/database). */
export default function HealthBanner({ health }) {
  if (!health || health.ready_for_scoring) return null;
  return (
    <div role="alert" className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <p className="font-semibold">Predictions are not available yet</p>
      <ul className="mt-1 list-disc space-y-1 pl-5">
        {health.issues.map((i) => <li key={i.code}>{i.message}</li>)}
      </ul>
    </div>
  );
}
