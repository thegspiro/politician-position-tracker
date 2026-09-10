import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  fetchPoliticians,
  fetchIssues,
  fetchStatements,
  deletePolitician,
  deleteIssue,
  deleteStatement,
  exportData,
  importData,
} from '../../api';
import type { Politician, Issue, Statement } from '../../types';
import { useAuth } from '../../AuthContext';
import { useToast } from '../../Toast';
import LoginPage from './LoginPage';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { isLoggedIn, logout, session } = useAuth();
  const { toast } = useToast();
  const [politicians, setPoliticians] = useState<Politician[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [statements, setStatements] = useState<Statement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [polsRes, issRes, stmtsRes] = await Promise.all([
        fetchPoliticians(),
        fetchIssues(),
        fetchStatements(),
      ]);
      setPoliticians(polsRes.items);
      setIssues(issRes.items);
      setStatements(stmtsRes.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isLoggedIn) {
      loadData();
    }
  }, [loadData, isLoggedIn]);

  async function handleDeletePolitician(id: number, name: string) {
    const stmtCount = statements.filter((s) => s.politician_id === id).length;
    const message =
      stmtCount > 0
        ? `Delete politician "${name}"? This will also delete ${stmtCount} statement${stmtCount === 1 ? '' : 's'}. Are you sure?`
        : `Delete politician "${name}"? This cannot be undone.`;
    if (!window.confirm(message)) return;
    try {
      await deletePolitician(id);
      toast(`Politician "${name}" deleted successfully`, 'success');
      await loadData();
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to delete politician', 'error');
    }
  }

  async function handleDeleteIssue(id: number, name: string) {
    const stmtCount = statements.filter((s) =>
      s.issues.some((iss) => iss.id === id),
    ).length;
    const message =
      stmtCount > 0
        ? `Delete issue "${name}"? ${stmtCount} statement${stmtCount === 1 ? '' : 's'} tagged with this issue will be affected. Are you sure?`
        : `Delete issue "${name}"? This cannot be undone.`;
    if (!window.confirm(message)) return;
    try {
      await deleteIssue(id);
      toast(`Issue "${name}" deleted successfully`, 'success');
      await loadData();
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to delete issue', 'error');
    }
  }

  async function handleDeleteStatement(id: number, title: string) {
    if (!window.confirm(`Delete statement "${title}"? This cannot be undone.`)) return;
    try {
      await deleteStatement(id);
      toast(`Statement "${title}" deleted successfully`, 'success');
      await loadData();
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to delete statement', 'error');
    }
  }

  async function handleExport() {
    try {
      const data = await exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `politician-tracker-backup-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast('Data exported successfully', 'success');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to export data', 'error');
    }
  }

  function handleImport() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        if (!data.politicians && !data.issues && !data.statements) {
          toast('Invalid backup file format. Expected politicians, issues, and statements keys.', 'error');
          return;
        }
        if (!window.confirm('Import data from backup? This will merge with existing data (duplicates are skipped).')) {
          return;
        }
        const result = await importData(data);
        toast(
          `Import complete: ${result.imported.politicians} politicians, ${result.imported.issues} issues, ${result.imported.statements} statements, ${result.imported.sources} sources`,
          'success',
        );
        await loadData();
      } catch (err) {
        toast(err instanceof Error ? err.message : 'Failed to import data', 'error');
      }
    };
    input.click();
  }

  if (!isLoggedIn) {
    return <LoginPage />;
  }

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
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-[var(--color-text)]">Admin Dashboard</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={handleImport}
            className="px-4 py-2 bg-[var(--color-bg-secondary)] text-[var(--color-text)] border border-[var(--color-border)] rounded-lg hover:bg-[var(--color-border)] transition text-sm font-medium"
          >
            Import Backup
          </button>
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-[var(--color-bg-secondary)] text-[var(--color-text)] border border-[var(--color-border)] rounded-lg hover:bg-[var(--color-border)] transition text-sm font-medium"
          >
            Export Backup
          </button>
          <Link
            to="/admin/users"
            className="px-4 py-2 bg-[var(--color-bg-secondary)] text-[var(--color-text)] border border-[var(--color-border)] rounded-lg hover:bg-[var(--color-border)] transition text-sm font-medium"
          >
            Accounts
          </Link>
          <button
            onClick={logout}
            className="px-4 py-2 bg-[var(--color-danger)] text-white rounded-lg hover:opacity-90 transition text-sm font-medium"
          >
            {session ? `Sign out ${session.username}` : 'Logout'}
          </button>
        </div>
      </div>

      {/* Politicians Section */}
      <section className="mb-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-[var(--color-text)]">
            Politicians
            <span className="ml-2 text-sm font-normal text-[var(--color-text-secondary)]">
              ({politicians.length})
            </span>
          </h2>
          <button
            onClick={() => navigate('/admin/politicians/new')}
            className="px-4 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition text-sm font-medium"
          >
            + New Politician
          </button>
        </div>
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-text-secondary)]">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-text-secondary)]">Party</th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-text-secondary)]">Office</th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-text-secondary)]">State</th>
                  <th className="text-right px-4 py-3 font-medium text-[var(--color-text-secondary)]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {politicians.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-[var(--color-text-secondary)]">
                      No politicians yet.
                    </td>
                  </tr>
                )}
                {politicians.map((pol) => (
                  <tr key={pol.id} className="border-b border-[var(--color-border)] last:border-b-0">
                    <td className="px-4 py-3 text-[var(--color-text)] font-medium">{pol.name}</td>
                    <td className="px-4 py-3 text-[var(--color-text-secondary)]">{pol.party}</td>
                    <td className="px-4 py-3 text-[var(--color-text-secondary)]">{pol.office}</td>
                    <td className="px-4 py-3 text-[var(--color-text-secondary)]">{pol.state ?? '—'}</td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/admin/politicians/${pol.id}/edit`}
                        className="text-[var(--color-accent)] hover:underline mr-3"
                      >
                        Edit
                      </Link>
                      <button
                        onClick={() => handleDeletePolitician(pol.id, pol.name)}
                        className="text-[var(--color-danger)] hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Issues Section */}
      <section className="mb-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-[var(--color-text)]">
            Issues
            <span className="ml-2 text-sm font-normal text-[var(--color-text-secondary)]">
              ({issues.length})
            </span>
          </h2>
          <button
            onClick={() => navigate('/admin/issues/new')}
            className="px-4 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition text-sm font-medium"
          >
            + New Issue
          </button>
        </div>
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-text-secondary)]">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-text-secondary)]">Description</th>
                  <th className="text-right px-4 py-3 font-medium text-[var(--color-text-secondary)]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {issues.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-[var(--color-text-secondary)]">
                      No issues yet.
                    </td>
                  </tr>
                )}
                {issues.map((issue) => (
                  <tr key={issue.id} className="border-b border-[var(--color-border)] last:border-b-0">
                    <td className="px-4 py-3 text-[var(--color-text)] font-medium">{issue.name}</td>
                    <td className="px-4 py-3 text-[var(--color-text-secondary)] max-w-xs truncate">
                      {issue.description ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/admin/issues/${issue.id}/edit`}
                        className="text-[var(--color-accent)] hover:underline mr-3"
                      >
                        Edit
                      </Link>
                      <button
                        onClick={() => handleDeleteIssue(issue.id, issue.name)}
                        className="text-[var(--color-danger)] hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Statements Section */}
      <section className="mb-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-[var(--color-text)]">
            Statements
            <span className="ml-2 text-sm font-normal text-[var(--color-text-secondary)]">
              ({statements.length})
            </span>
          </h2>
          <button
            onClick={() => navigate('/admin/statements/new')}
            className="px-4 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition text-sm font-medium"
          >
            + New Statement
          </button>
        </div>
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-text-secondary)]">Title</th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-text-secondary)]">Politician</th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-text-secondary)]">Issues</th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-text-secondary)]">Date</th>
                  <th className="text-right px-4 py-3 font-medium text-[var(--color-text-secondary)]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {statements.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-[var(--color-text-secondary)]">
                      No statements yet.
                    </td>
                  </tr>
                )}
                {statements.map((stmt) => (
                  <tr key={stmt.id} className="border-b border-[var(--color-border)] last:border-b-0">
                    <td className="px-4 py-3 text-[var(--color-text)] font-medium max-w-xs truncate">
                      {stmt.title}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-text-secondary)]">
                      {stmt.politician?.name ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-text-secondary)]">
                      {stmt.issues.length > 0
                        ? stmt.issues.map((iss) => iss.name).join(', ')
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-text-secondary)]">
                      {stmt.post_date
                        ? new Date(stmt.post_date).toLocaleDateString()
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/admin/statements/${stmt.id}/edit`}
                        className="text-[var(--color-accent)] hover:underline mr-3"
                      >
                        Edit
                      </Link>
                      <button
                        onClick={() => handleDeleteStatement(stmt.id, stmt.title)}
                        className="text-[var(--color-danger)] hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
