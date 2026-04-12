import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchIssue, createIssue, updateIssue } from '../../api';

export default function IssueForm() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(isEdit);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setFetchLoading(true);
    fetchIssue(id)
      .then((issue) => {
        setName(issue.name);
        setDescription(issue.description ?? '');
      })
      .catch((err) => {
        setSubmitError(err instanceof Error ? err.message : 'Failed to load issue');
      })
      .finally(() => setFetchLoading(false));
  }, [id]);

  function validate(): boolean {
    const newErrors: Record<string, string> = {};
    if (!name.trim()) newErrors.name = 'Name is required';
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
      description: description.trim() || null,
    };

    try {
      if (isEdit && id) {
        await updateIssue(id, data);
      } else {
        await createIssue(data);
      }
      navigate('/admin');
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to save issue');
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
        {isEdit ? 'Edit Issue' : 'New Issue'}
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
            placeholder="e.g. Climate Change"
          />
          {errors.name && <p className="mt-1 text-sm text-[var(--color-danger)]">{errors.name}</p>}
        </div>

        {/* Description */}
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Description
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] transition resize-y"
            placeholder="Optional description of the issue"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition font-medium disabled:opacity-50"
          >
            {loading ? 'Saving...' : isEdit ? 'Update Issue' : 'Create Issue'}
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
