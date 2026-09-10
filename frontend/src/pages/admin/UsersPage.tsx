import { useCallback, useEffect, useState } from 'react';
import {
  changeOwnPassword,
  createUser,
  deleteUser,
  fetchUsers,
  updateUser,
} from '../../api';
import { useAuth } from '../../AuthContext';
import { useToast } from '../../Toast';
import { ROLES, ROLE_LABELS } from '../../types';
import type { Role, User } from '../../types';

const inputClass =
  'w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]';

function formatDate(value: string | null): string {
  if (!value) return 'Never';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? 'Unknown'
    : parsed.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
}

/** Turn an API error into something an admin can act on. */
function message(err: unknown, fallback: string): string {
  if (!(err instanceof Error)) return fallback;
  const match = /"detail":"([^"]+)"/.exec(err.message);
  if (match) return match[1];
  // Pydantic reports field errors in a nested shape; surface the first one.
  const validation = /"msg":"([^"]+)"/.exec(err.message);
  return validation ? validation[1] : fallback;
}

function ChangePasswordCard() {
  const { toast } = useToast();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (next !== confirm) {
      toast('The new passwords do not match', 'error');
      return;
    }
    setBusy(true);
    try {
      await changeOwnPassword(current, next);
      toast('Password changed', 'success');
      setCurrent('');
      setNext('');
      setConfirm('');
    } catch (err) {
      toast(message(err, 'Could not change password'), 'error');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl p-5 mb-8"
    >
      <h2 className="text-lg font-semibold text-[var(--color-text)] mb-3">
        Change your password
      </h2>
      <div className="grid gap-3 sm:grid-cols-3">
        <input
          type="password"
          autoComplete="current-password"
          placeholder="Current password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          className={inputClass}
        />
        <input
          type="password"
          autoComplete="new-password"
          placeholder="New password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          className={inputClass}
        />
        <input
          type="password"
          autoComplete="new-password"
          placeholder="Confirm new password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className={inputClass}
        />
      </div>
      <button
        type="submit"
        disabled={busy || !current || !next}
        className="mt-3 px-4 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition font-medium disabled:opacity-50"
      >
        {busy ? 'Saving...' : 'Change password'}
      </button>
    </form>
  );
}

function NewUserForm({ onCreated }: { onCreated: () => void }) {
  const { toast } = useToast();
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<Role>('editor');
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await createUser({
        username: username.trim(),
        display_name: displayName.trim() || null,
        password,
        role,
      });
      toast('Account created', 'success');
      setUsername('');
      setDisplayName('');
      setPassword('');
      setRole('editor');
      onCreated();
    } catch (err) {
      toast(message(err, 'Could not create the account'), 'error');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl p-5 mb-8"
    >
      <h2 className="text-lg font-semibold text-[var(--color-text)] mb-3">
        Add an account
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className={inputClass}
        />
        <input
          type="text"
          placeholder="Display name (optional)"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className={inputClass}
        />
        <input
          type="password"
          autoComplete="new-password"
          placeholder="Password (at least 12 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={inputClass}
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as Role)}
          className={inputClass}
        >
          {ROLES.map((value) => (
            <option key={value} value={value}>
              {ROLE_LABELS[value]}
            </option>
          ))}
        </select>
      </div>
      <p className="text-xs text-[var(--color-text-secondary)] mt-2">
        Editors can manage all content. Only owners can manage accounts.
      </p>
      <button
        type="submit"
        disabled={busy || !username.trim() || !password}
        className="mt-3 px-4 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent-hover)] transition font-medium disabled:opacity-50"
      >
        {busy ? 'Creating...' : 'Create account'}
      </button>
    </form>
  );
}

export default function UsersPage() {
  const { isOwner, session } = useAuth();
  const { toast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Deliberately does not raise the loading flag: it starts true for the first
  // fetch, and a reload after a change swaps the rows in place rather than
  // blanking the table. Setting it here would also mean a synchronous setState
  // inside the effect below.
  const load = useCallback(() => {
    fetchUsers()
      .then((result) => {
        setUsers(result);
        setError(null);
      })
      .catch((err) => setError(message(err, 'Could not load accounts')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // Non-owners never see the account table, so there is nothing to load and
    // no loading state to clear.
    if (isOwner) load();
  }, [isOwner, load]);

  async function change(user: User, patch: Parameters<typeof updateUser>[1]) {
    try {
      await updateUser(user.uid, patch);
      toast('Account updated', 'success');
      load();
    } catch (err) {
      toast(message(err, 'Could not update the account'), 'error');
    }
  }

  async function remove(user: User) {
    if (
      !window.confirm(
        `Delete the account "${user.username}"? Statements and sources they created are kept, but will no longer show an author.`,
      )
    ) {
      return;
    }
    try {
      await deleteUser(user.uid);
      toast('Account deleted', 'success');
      load();
    } catch (err) {
      toast(message(err, 'Could not delete the account'), 'error');
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-3xl font-bold text-[var(--color-text)] mb-6">Accounts</h1>

      <ChangePasswordCard />

      {!isOwner && (
        <p className="text-sm text-[var(--color-text-secondary)]">
          Only owner accounts can manage other accounts.
        </p>
      )}

      {isOwner && (
        <>
          <NewUserForm onCreated={load} />

          {loading && (
            <p className="text-sm text-[var(--color-text-secondary)]">Loading...</p>
          )}
          {error && <p className="text-sm text-[var(--color-danger)]">{error}</p>}

          {!loading && !error && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                    <th className="py-2 pr-3 font-medium">Username</th>
                    <th className="py-2 pr-3 font-medium">Name</th>
                    <th className="py-2 pr-3 font-medium">Role</th>
                    <th className="py-2 pr-3 font-medium">Last login</th>
                    <th className="py-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => {
                    const isSelf = user.username === session?.username;
                    return (
                      <tr
                        key={user.uid}
                        className="border-b border-[var(--color-border)]"
                      >
                        <td className="py-3 pr-3 text-[var(--color-text)]">
                          {user.username}
                          {isSelf && (
                            <span className="ml-2 text-xs text-[var(--color-text-secondary)]">
                              (you)
                            </span>
                          )}
                          {!user.is_active && (
                            <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-[var(--color-badge-bg)] text-[var(--color-badge-text)]">
                              Deactivated
                            </span>
                          )}
                        </td>
                        <td className="py-3 pr-3 text-[var(--color-text-secondary)]">
                          {user.display_name ?? '--'}
                        </td>
                        <td className="py-3 pr-3">
                          <select
                            value={user.role}
                            onChange={(e) =>
                              change(user, { username: user.username, role: e.target.value })
                            }
                            className="px-2 py-1 rounded border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)]"
                          >
                            {ROLES.map((value) => (
                              <option key={value} value={value}>
                                {ROLE_LABELS[value]}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="py-3 pr-3 text-[var(--color-text-secondary)]">
                          {formatDate(user.last_login_at)}
                        </td>
                        <td className="py-3">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() =>
                                change(user, {
                                  username: user.username,
                                  is_active: !user.is_active,
                                })
                              }
                              disabled={isSelf}
                              className="px-2 py-1 text-xs rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              {user.is_active ? 'Deactivate' : 'Reactivate'}
                            </button>
                            <button
                              type="button"
                              onClick={() => remove(user)}
                              disabled={isSelf}
                              className="px-2 py-1 text-xs rounded border border-[var(--color-border)] text-[var(--color-danger)] hover:border-[var(--color-danger)] transition disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
