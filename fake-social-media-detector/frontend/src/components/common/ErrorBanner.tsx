export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div role="alert" className="border border-signal/30 bg-signal/5 px-4 py-3 text-sm text-signal">
      {message}
    </div>
  );
}
