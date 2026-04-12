import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchPolitician, createPolitician, updatePolitician } from '../../api';
import { useToast } from '../../Toast';

const PARTIES = ['Democrat', 'Republican', 'Independent', 'Libertarian', 'Green', 'Other'];

const US_STATES = [
  'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut',
  'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
  'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan',
  'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire',
  'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio',
  'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
  'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia',
  'Wisconsin', 'Wyoming',
];

export default function PoliticianForm() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const { toast } = useToast();

  const [name, setName] = useState('');
  const [party, setParty] = useState('');
  const [office, setOffice] = useState('');
  const [state, setState] = useState('');
  const [photoUrl, setPhotoUrl] = useState('');

  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(isEdit);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setFetchLoading(true);
    fetchPolitician(id)
      .then((pol) => {
        setName(pol.name);
        setParty(pol.party);
        setOffice(pol.office);
        setState(pol.state ?? '');
        setPhotoUrl(pol.photo_url ?? '');
      })
      .catch((err) => {
        setSubmitError(err instanceof Error ? err.message : 'Failed to load politician');
      })
      .finally(() => setFetchLoading(false));
  }, [id]);

  function validate(): boolean {
    const newErrors: Record<string, string> = {};
    if (!name.trim()) newErrors.name = 'Name is required';
    if (!party) newErrors.party = 'Party is required';
    if (!office.trim()) newErrors.office = 'Office is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setSubmitError(null);

    const data = {
      name: name.trim(),
      party,
      office: office.trim(),
      state: state || null,
      photo_url: photoUrl.trim() || null,
    };

    try {
      if (isEdit && id) {
        await updatePolitician(id, data);
      } else {
        await createPolitician(data);
      }
      toast('Politician saved successfully', 'success');
      navigate('/admin');
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to save politician');
    } finally {
      setLoading(false);
    }
  }

  if (fetchLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-4 border-[var(--color-border)] border-t-[var(--color-accent)] rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-3xl font-bold text-[var(--color-text)] mb-8">
        {isEdit ? 'Edit Politician' : 'New Politician'}
      </h1>

      <form
        onSubmit={handleSubmit}
        className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl p-6 space-y-5"
      >
        {submitError && (
          <div className="p-3 bg-[var(--color-danger)]/10 border border-[var(--color-danger)] rounded-lg text-[var(--color-danger)] text-sm">
            {submitError}
          </div>
        )}

        {/* Name */}
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Name <span className="text-[var(--color-danger)]">*</span>
          </label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] transition"
            placeholder="e.g. John Smith"
          />
          {errors.name && <p className="mt-1 text-sm text-[var(--color-danger)]">{errors.name}</p>}
        </div>

        {/* Party */}
        <div>
          <label htmlFor="party" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Party <span className="text-[var(--color-danger)]">*</span>
          </label>
          <select
            id="party"
            value={party}
            onChange={(e) => setParty(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] transition"
          >
            <option value="">Select a party</option>
            {PARTIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          {errors.party && <p className="mt-1 text-sm text-[var(--color-danger)]">{errors.party}</p>}
        </div>

        {/* Office */}
        <div>
          <label htmlFor="office" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Office <span className="text-[var(--color-danger)]">*</span>
          </label>
          <input
            id="office"
            type="text"
            value={office}
            onChange={(e) => setOffice(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] transition"
            placeholder="e.g. U.S. Senator"
          />
          {errors.office && <p className="mt-1 text-sm text-[var(--color-danger)]">{errors.office}</p>}
        </div>

        {/* State */}
        <div>
          <label htmlFor="state" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            State
          </label>
          <select
            id="state"
            value={state}
            onChange={(e) => setState(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] transition"
          >
            <option value="">None</option>
            {US_STATES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Photo URL */}
        <div>
          <label htmlFor="photoUrl" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Photo URL
          </label>
          <input
            id="photoUrl"
            type="url"
            value={photoUrl}
            onChange={(e) => setPhotoUrl(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] transition"
            placeholder="https://example.com/photo.jpg"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition font-medium disabled:opacity-50"
          >
            {loading ? 'Saving...' : isEdit ? 'Update Politician' : 'Create Politician'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/admin')}
            className="px-5 py-2 bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] rounded-lg hover:bg-[var(--color-border)] transition font-medium"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
