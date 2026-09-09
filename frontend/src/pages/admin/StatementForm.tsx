import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  fetchStatement,
  fetchPoliticians,
  fetchIssues,
  createStatement,
  updateStatement,
  uploadFile,
} from '../../api';
import type { Politician, Issue, Source, SourceInput } from '../../types';
import { useToast } from '../../Toast';
import SourceListEditor from '../../components/SourceListEditor';

const PLATFORMS = ['X', 'Bluesky', 'Truth Social', 'YouTube'];

/** Date inputs use YYYY-MM-DD; the API returns full ISO timestamps. */
function toDateInput(value: string | null | undefined): string {
  return value ? value.slice(0, 10) : '';
}

/** Blank date and text inputs are sent as null, not as empty strings. */
function orNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === '' ? null : trimmed;
}

/**
 * Map an API source onto the form shape, keeping its uid so that saving
 * updates the existing row in place instead of replacing it. Losing the uid
 * would break any citation marker pointing at the source.
 */
function toSourceInput(source: Source): SourceInput {
  return {
    uid: source.uid,
    authors: source.authors ?? [],
    container_title: source.container_title ?? '',
    edition: source.edition ?? '',
    document_type: source.document_type ?? '',
    bill_number: source.bill_number ?? '',
    congress_number:
      source.congress_number === null ? '' : String(source.congress_number),
    congress_session: source.congress_session ?? '',
    committee: source.committee ?? '',
    report_number: source.report_number ?? '',
    source_type: source.source_type,
    title: source.title,
    url: source.url,
    description: source.description ?? '',
    media_type: source.media_type,
    publisher: source.publisher ?? '',
    published_date: toDateInput(source.published_date),
    excerpt: source.excerpt ?? '',
    locator: source.locator ?? '',
    archive_url: source.archive_url ?? '',
    archived_at: toDateInput(source.archived_at),
    retrieved_at: toDateInput(source.retrieved_at),
  };
}

export default function StatementForm() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const { toast } = useToast();

  // Dropdown data
  const [politicians, setPoliticians] = useState<Politician[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);

  // Form fields
  const [politicianId, setPoliticianId] = useState('');
  const [issueIds, setIssueIds] = useState<string[]>([]);
  const [title, setTitle] = useState('');
  const [postUrl, setPostUrl] = useState('');
  const [postPlatform, setPostPlatform] = useState('');
  const [postContent, setPostContent] = useState('');
  const [screenshotUrl, setScreenshotUrl] = useState('');
  const [postDate, setPostDate] = useState('');
  const [analysis, setAnalysis] = useState('');
  const [postSources, setPostSources] = useState<SourceInput[]>([]);
  const [analysisSources, setAnalysisSources] = useState<SourceInput[]>([]);

  // Upload state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  // UI state
  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    async function loadData() {
      try {
        const [polsRes, issRes] = await Promise.all([fetchPoliticians(), fetchIssues()]);
        setPoliticians(polsRes.items);
        setIssues(issRes.items);

        if (id) {
          const stmt = await fetchStatement(id);
          setPoliticianId(String(stmt.politician_id));
          setIssueIds(stmt.issues.map((i) => String(i.id)));
          setTitle(stmt.title);
          setPostUrl(stmt.post_url);
          setPostPlatform(stmt.post_platform);
          setPostContent(stmt.post_content ?? '');
          setScreenshotUrl(stmt.screenshot_url ?? '');
          setPostDate(stmt.post_date ? stmt.post_date.slice(0, 10) : '');
          setAnalysis(stmt.analysis);
          if (stmt.sources && stmt.sources.length > 0) {
            const ordered = [...stmt.sources].sort(
              (a, b) => a.sort_order - b.sort_order || a.id - b.id,
            );
            setPostSources(
              ordered.filter((s) => s.source_type === 'post').map(toSourceInput),
            );
            setAnalysisSources(
              ordered.filter((s) => s.source_type === 'analysis').map(toSourceInput),
            );
          }
        }
      } catch (err) {
        toast(err instanceof Error ? err.message : 'Failed to load data', 'error');
      } finally {
        setFetchLoading(false);
      }
    }
    loadData();
  }, [id, toast]);

  function toggleIssue(issueId: string) {
    setIssueIds((prev) =>
      prev.includes(issueId) ? prev.filter((i) => i !== issueId) : [...prev, issueId],
    );
  }

  function validate(): boolean {
    const newErrors: Record<string, string> = {};
    if (!politicianId) newErrors.politicianId = 'Politician is required';
    if (issueIds.length === 0) newErrors.issueIds = 'At least one issue is required';
    if (!title.trim()) newErrors.title = 'Title is required';
    if (!postUrl.trim()) newErrors.postUrl = 'Post URL is required';
    if (!postPlatform) newErrors.postPlatform = 'Post Platform is required';
    if (!analysis.trim()) newErrors.analysis = 'Analysis is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleUpload() {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const result = await uploadFile(file);
      setScreenshotUrl(result.url);
      toast('File uploaded successfully', 'success');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to upload file', 'error');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);

    const allSources = [...postSources, ...analysisSources]
      .filter((s) => s.title.trim() && s.url.trim())
      .map((s) => ({
        uid: s.uid,
        source_type: s.source_type,
        title: s.title.trim(),
        url: s.url.trim(),
        description: orNull(s.description),
        media_type: s.media_type,
        publisher: orNull(s.publisher),
        published_date: orNull(s.published_date),
        excerpt: orNull(s.excerpt),
        locator: orNull(s.locator),
        archive_url: orNull(s.archive_url),
        archived_at: orNull(s.archived_at),
        retrieved_at: orNull(s.retrieved_at),
        // Blank name rows are dropped rather than rejected by the API.
        authors: s.authors.filter(
          (a) =>
            (a.given ?? '').trim() ||
            (a.family ?? '').trim() ||
            (a.literal ?? '').trim(),
        ),
        container_title: orNull(s.container_title),
        edition: orNull(s.edition),
        document_type: s.document_type === '' ? null : s.document_type,
        bill_number: orNull(s.bill_number),
        congress_number:
          s.congress_number.trim() === '' ? null : Number(s.congress_number),
        congress_session: orNull(s.congress_session),
        committee: orNull(s.committee),
        report_number: orNull(s.report_number),
      }));

    const data = {
      politician_id: Number(politicianId),
      issue_ids: issueIds.map(Number),
      title: title.trim(),
      post_url: postUrl.trim(),
      post_platform: postPlatform,
      post_content: postContent.trim() || null,
      screenshot_url: screenshotUrl.trim() || null,
      post_date: postDate || null,
      analysis: analysis.trim(),
      sources: allSources,
    };

    try {
      if (isEdit && id) {
        await updateStatement(id, data);
      } else {
        await createStatement(data);
      }
      toast('Statement saved!', 'success');
      navigate('/admin');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to save statement', 'error');
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

  const inputClass =
    'w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] transition';

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-3xl font-bold text-[var(--color-text)] mb-8">
        {isEdit ? 'Edit Statement' : 'New Statement'}
      </h1>

      <form
        onSubmit={handleSubmit}
        className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl p-6 space-y-5"
      >
        {/* Politician */}
        <div>
          <label htmlFor="politicianId" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Politician <span className="text-[var(--color-danger)]">*</span>
          </label>
          <select
            id="politicianId"
            value={politicianId}
            onChange={(e) => setPoliticianId(e.target.value)}
            className={inputClass}
          >
            <option value="">Select a politician</option>
            {politicians.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.party})
              </option>
            ))}
          </select>
          {errors.politicianId && (
            <p className="mt-1 text-sm text-[var(--color-danger)]">{errors.politicianId}</p>
          )}
        </div>

        {/* Issues (multi-select) */}
        <div>
          <label className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Issues <span className="text-[var(--color-danger)]">*</span>
          </label>
          <div className="flex flex-wrap gap-2">
            {issues.map((iss) => {
              const selected = issueIds.includes(String(iss.id));
              return (
                <button
                  key={iss.id}
                  type="button"
                  onClick={() => toggleIssue(String(iss.id))}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition ${
                    selected
                      ? 'bg-[var(--color-accent)] text-white border-[var(--color-accent)]'
                      : 'bg-[var(--color-bg)] text-[var(--color-text-secondary)] border-[var(--color-border)] hover:border-[var(--color-accent)]'
                  }`}
                >
                  {iss.name}
                </button>
              );
            })}
          </div>
          {issues.length === 0 && (
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              No issues available. Create one first.
            </p>
          )}
          {errors.issueIds && (
            <p className="mt-1 text-sm text-[var(--color-danger)]">{errors.issueIds}</p>
          )}
        </div>

        {/* Title */}
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Title <span className="text-[var(--color-danger)]">*</span>
          </label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={inputClass}
            placeholder="e.g. Senator calls for new climate legislation"
          />
          {errors.title && <p className="mt-1 text-sm text-[var(--color-danger)]">{errors.title}</p>}
        </div>

        {/* Post URL */}
        <div>
          <label htmlFor="postUrl" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Post URL <span className="text-[var(--color-danger)]">*</span>
          </label>
          <input
            id="postUrl"
            type="url"
            value={postUrl}
            onChange={(e) => setPostUrl(e.target.value)}
            className={inputClass}
            placeholder="https://x.com/user/status/123"
          />
          {errors.postUrl && (
            <p className="mt-1 text-sm text-[var(--color-danger)]">{errors.postUrl}</p>
          )}
        </div>

        {/* Post Platform */}
        <div>
          <label htmlFor="postPlatform" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Post Platform <span className="text-[var(--color-danger)]">*</span>
          </label>
          <select
            id="postPlatform"
            value={postPlatform}
            onChange={(e) => setPostPlatform(e.target.value)}
            className={inputClass}
          >
            <option value="">Select a platform</option>
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          {errors.postPlatform && (
            <p className="mt-1 text-sm text-[var(--color-danger)]">{errors.postPlatform}</p>
          )}
        </div>

        {/* Post Content */}
        <div>
          <label htmlFor="postContent" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Post Content
          </label>
          <textarea
            id="postContent"
            value={postContent}
            onChange={(e) => setPostContent(e.target.value)}
            rows={4}
            className={`${inputClass} resize-y`}
            placeholder="Quote or paste the original post text"
          />
        </div>

        {/* Screenshot URL + Upload */}
        <div>
          <label htmlFor="screenshotUrl" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Screenshot URL
          </label>
          <div className="flex gap-2">
            <input
              id="screenshotUrl"
              type="url"
              value={screenshotUrl}
              onChange={(e) => setScreenshotUrl(e.target.value)}
              className={inputClass}
              placeholder="https://example.com/screenshot.png"
            />
          </div>
          <div className="flex items-center gap-2 mt-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="text-sm text-[var(--color-text-secondary)] file:mr-2 file:py-1 file:px-3 file:rounded-lg file:border file:border-[var(--color-border)] file:bg-[var(--color-bg-secondary)] file:text-[var(--color-text)] file:text-sm file:font-medium file:cursor-pointer hover:file:bg-[var(--color-border)] file:transition"
            />
            <button
              type="button"
              onClick={handleUpload}
              disabled={uploading}
              className="px-3 py-1 text-sm bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition font-medium disabled:opacity-50 whitespace-nowrap"
            >
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </div>

        {/* Post Date */}
        <div>
          <label htmlFor="postDate" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Post Date
          </label>
          <input
            id="postDate"
            type="date"
            value={postDate}
            onChange={(e) => setPostDate(e.target.value)}
            className={inputClass}
          />
        </div>

        {/* Analysis */}
        <div>
          <label htmlFor="analysis" className="block text-sm font-medium text-[var(--color-text)] mb-1">
            Analysis <span className="text-[var(--color-danger)]">*</span>
          </label>
          <textarea
            id="analysis"
            value={analysis}
            onChange={(e) => setAnalysis(e.target.value)}
            rows={6}
            className={`${inputClass} resize-y`}
            placeholder="Provide analysis of the statement and its significance"
          />
          <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
            Cite a source with a marker like <code>[^1]</code>, using the number
            shown on its card below. Markers link to that source.
          </p>
          {errors.analysis && (
            <p className="mt-1 text-sm text-[var(--color-danger)]">{errors.analysis}</p>
          )}
        </div>

        <SourceListEditor
          legend="Post Sources"
          blurb="Primary sources for the original post"
          addLabel="+ Add Post Source"
          emptyLabel="No post sources added yet."
          sourceType="post"
          sources={postSources}
          onChange={setPostSources}
          numberOffset={0}
        />

        <SourceListEditor
          legend="Analysis Sources"
          blurb="Primary sources supporting your analysis"
          addLabel="+ Add Analysis Source"
          emptyLabel="No analysis sources added yet."
          sourceType="analysis"
          sources={analysisSources}
          onChange={setAnalysisSources}
          numberOffset={postSources.length}
        />

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition font-medium disabled:opacity-50"
          >
            {loading ? 'Saving...' : isEdit ? 'Update Statement' : 'Create Statement'}
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
