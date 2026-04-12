import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchPoliticians } from '../api';
import type { Politician } from '../types';

function partyBadgeClass(party: string): string {
  const p = party.toLowerCase();
  if (p.includes('democrat')) return 'bg-blue-600 text-white';
  if (p.includes('republican')) return 'bg-red-600 text-white';
  return 'bg-gray-500 text-white';
}

export default function PoliticiansPage() {
  const [politicians, setPoliticians] = useState<Politician[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPoliticians()
      .then(setPoliticians)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load politicians'),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-4 border-[var(--color-border)] border-t-[var(--color-accent)] rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <p className="text-[var(--color-danger)] mb-4">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-3xl font-bold text-[var(--color-text)] mb-8">Politicians</h1>

      {politicians.length === 0 && (
        <p className="text-center text-[var(--color-text-secondary)] text-lg py-16">
          No politicians found.
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {politicians.map((pol) => (
          <Link
            key={pol.id}
            to={`/politicians/${pol.id}`}
            className="group bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl p-5 transition hover:border-[var(--color-accent)] hover:shadow-md"
          >
            <div className="flex items-center gap-4 mb-3">
              {pol.photo_url ? (
                <img
                  src={pol.photo_url}
                  alt={pol.name}
                  className="w-14 h-14 rounded-full object-cover ring-2 ring-[var(--color-border)] group-hover:ring-[var(--color-accent)] transition"
                />
              ) : (
                <div className="w-14 h-14 rounded-full bg-[var(--color-bg-secondary)] flex items-center justify-center ring-2 ring-[var(--color-border)] group-hover:ring-[var(--color-accent)] transition">
                  <span className="text-xl font-bold text-[var(--color-text-secondary)]">
                    {pol.name.charAt(0)}
                  </span>
                </div>
              )}
              <div className="min-w-0">
                <h2 className="font-semibold text-[var(--color-text)] truncate group-hover:text-[var(--color-accent)] transition">
                  {pol.name}
                </h2>
                <span
                  className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full mt-1 ${partyBadgeClass(pol.party)}`}
                >
                  {pol.party}
                </span>
              </div>
            </div>

            <div className="text-sm text-[var(--color-text-secondary)] space-y-0.5">
              {pol.office && <p>{pol.office}</p>}
              {pol.state && <p>{pol.state}</p>}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
