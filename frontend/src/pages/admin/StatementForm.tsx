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
import type { Politician, Issue, SourceInput } from '../../types';
import { useToast } from '../../Toast';

const PLATFORMS = ['X', 'Bluesky', 'Truth Social', 'YouTube'];

function emptySource(type: 'post' | 'analysis'): SourceInput {
  return { source_type: type, title: '', url: '', description: '' };
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
            setPostSources(
              stmt.sources
                .filter((s) => s.source_type === 'post')
                .map((s) => ({
                  source_type: 'post' as const,
                  title: s.title,
                  url: s.url,
                  description: s.description ?? '',
                })),
            );
            setAnalysisSources(
              stmt.sources
                .filter((s) => s.source_type === 'analysis')
                .map((s) => ({
                  source_type: 'analysis' as const,
                  title: s.title,
                  url: s.url,
                  description: s.description ?? '',
                })),
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

  function handleSourceChange(
    setter: React.Dispatch<React.SetStateAction<SourceInput[]>>,
    index: number,
    field: 'title' | 'url' | 'description',
    value: string,
  ) {
    setter((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  }

  function addSource(setter: React.Dispatch<React.SetStateAction<SourceInput[]>>, type: 'post' | 'analysis') {
    setter((prev) => [...prev, emptySource(type)]);
  }

  function removeSource(setter: React.Dispatch<React.SetStateAction<SourceInput[]>>, index: number) {
    setter((prev) => prev.filter((_, i) => i !== index));
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

    const allSources = [...postSources, ...analysisSources].filter(
      (s) => s.title.trim() && s.url.trim(),
    );

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
      sources: allSources.length > 0 ? allSources : undefined,
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
          {errors.analysis && (
            <p className="mt-1 text-sm text-[var(--color-danger)]">{errors.analysis}</p>
          )}
        </div>

        {/* Post Sources */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-[var(--color-text)]">
              Post Sources
              <span className="block text-xs font-normal text-[var(--color-text-secondary)]">Citations for the original post</span>
            </label>
            <button
              type="button"
              onClick={() => addSource(setPostSources, 'post')}
              className="px-3 py-1 text-sm bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition font-medium"
            >
              + Add Post Source
            </button>
          </div>

          {postSources.length === 0 && (
            <p className="text-sm text-[var(--color-text-secondary)] italic mb-2">
              No post sources added yet.
            </p>
          )}

          <div className="space-y-4">
            {postSources.map((source, index) => (
              <div
                key={index}
                className="border border-[var(--color-border)] rounded-lg p-4 bg-[var(--color-bg)] space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-[var(--color-text-secondary)]">
                    Post Source {index + 1}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeSource(setPostSources, index)}
                    className="px-3 py-1 text-sm bg-[var(--color-danger)] text-white rounded-lg hover:bg-[var(--color-danger-hover)] transition font-medium"
                  >
                    Remove
                  </button>
                </div>
                <input type="text" placeholder="Source title" value={source.title} onChange={(e) => handleSourceChange(setPostSources, index, 'title', e.target.value)} className={inputClass} />
                <input type="url" placeholder="https://..." value={source.url} onChange={(e) => handleSourceChange(setPostSources, index, 'url', e.target.value)} className={inputClass} />
                <input type="text" placeholder="Brief description (optional)" value={source.description} onChange={(e) => handleSourceChange(setPostSources, index, 'description', e.target.value)} className={inputClass} />
              </div>
            ))}
          </div>
        </div>

        {/* Analysis Sources */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-[var(--color-text)]">
              Analysis Sources
              <span className="block text-xs font-normal text-[var(--color-text-secondary)]">Citations supporting your analysis/response</span>
            </label>
            <button
              type="button"
              onClick={() => addSource(setAnalysisSources, 'analysis')}
              className="px-3 py-1 text-sm bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition font-medium"
            >
              + Add Analysis Source
            </button>
          </div>

          {analysisSources.length === 0 && (
            <p className="text-sm text-[var(--color-text-secondary)] italic mb-2">
              No analysis sources added yet.
            </p>
          )}

          <div className="space-y-4">
            {analysisSources.map((source, index) => (
              <div
                key={index}
                className="border border-[var(--color-border)] rounded-lg p-4 bg-[var(--color-bg)] space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-[var(--color-text-secondary)]">
                    Analysis Source {index + 1}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeSource(setAnalysisSources, index)}
                    className="px-3 py-1 text-sm bg-[var(--color-danger)] text-white rounded-lg hover:bg-[var(--color-danger-hover)] transition font-medium"
                  >
                    Remove
                  </button>
                </div>
                <input type="text" placeholder="Source title" value={source.title} onChange={(e) => handleSourceChange(setAnalysisSources, index, 'title', e.target.value)} className={inputClass} />
                <input type="url" placeholder="https://..." value={source.url} onChange={(e) => handleSourceChange(setAnalysisSources, index, 'url', e.target.value)} className={inputClass} />
                <input type="text" placeholder="Brief description (optional)" value={source.description} onChange={(e) => handleSourceChange(setAnalysisSources, index, 'description', e.target.value)} className={inputClass} />
              </div>
            ))}
          </div>
        </div>

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
