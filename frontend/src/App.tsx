import { BrowserRouter, Routes, Route, NavLink, Link } from 'react-router-dom';
import { useState } from 'react';
import { ThemeProvider, useTheme } from './ThemeContext';
import TimelinePage from './pages/TimelinePage';
import PoliticiansPage from './pages/PoliticiansPage';
import PoliticianDetailPage from './pages/PoliticianDetailPage';
import IssuesPage from './pages/IssuesPage';
import IssueDetailPage from './pages/IssueDetailPage';
import StatementDetailPage from './pages/StatementDetailPage';
import AdminDashboard from './pages/admin/AdminDashboard';
import PoliticianForm from './pages/admin/PoliticianForm';
import IssueForm from './pages/admin/IssueForm';
import StatementForm from './pages/admin/StatementForm';

// ── Theme toggle button ──────────────────────────────────────

function ThemeToggle() {
  const { isDark, toggleTheme } = useTheme();
  return (
    <button
      onClick={toggleTheme}
      aria-label="Toggle dark mode"
      className="p-2 rounded-lg hover:bg-[var(--color-bg-secondary)] transition-colors"
    >
      {isDark ? (
        /* Sun icon */
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5 text-[var(--color-text)]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 3v1m0 16v1m8.66-13.66l-.71.71M4.05 19.95l-.71.71M21 12h-1M4 12H3m16.66 7.66l-.71-.71M4.05 4.05l-.71-.71M16 12a4 4 0 11-8 0 4 4 0 018 0z"
          />
        </svg>
      ) : (
        /* Moon icon */
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5 text-[var(--color-text)]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z"
          />
        </svg>
      )}
    </button>
  );
}

// ── Navigation ───────────────────────────────────────────────

const NAV_LINKS = [
  { to: '/', label: 'Timeline' },
  { to: '/politicians', label: 'Politicians' },
  { to: '/issues', label: 'Issues' },
  { to: '/admin', label: 'Admin' },
] as const;

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return [
    'px-3 py-2 rounded-lg text-sm font-medium transition-colors',
    isActive
      ? 'bg-[var(--color-accent)] text-white'
      : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg-secondary)]',
  ].join(' ');
}

function Header() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-border)] bg-[var(--color-bg)] backdrop-blur supports-[backdrop-filter]:bg-[var(--color-bg)]/95">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo / title */}
          <Link
            to="/"
            className="text-xl font-bold text-[var(--color-text)] hover:text-[var(--color-accent)] transition-colors"
          >
            Politician Tracker
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map((link) => (
              <NavLink key={link.to} to={link.to} end={link.to === '/'} className={navLinkClass}>
                {link.label}
              </NavLink>
            ))}
            <ThemeToggle />
          </nav>

          {/* Mobile hamburger */}
          <div className="flex items-center md:hidden gap-2">
            <ThemeToggle />
            <button
              onClick={() => setMenuOpen((o) => !o)}
              aria-label="Toggle menu"
              className="p-2 rounded-lg hover:bg-[var(--color-bg-secondary)] transition-colors"
            >
              {menuOpen ? (
                /* X icon */
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-6 w-6 text-[var(--color-text)]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                /* Hamburger icon */
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-6 w-6 text-[var(--color-text)]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile menu dropdown */}
        {menuOpen && (
          <nav className="md:hidden pb-4 flex flex-col gap-1">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === '/'}
                className={navLinkClass}
                onClick={() => setMenuOpen(false)}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        )}
      </div>
    </header>
  );
}

// ── App ──────────────────────────────────────────────────────

function AppRoutes() {
  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <Header />
      <main>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<TimelinePage />} />
          <Route path="/politicians" element={<PoliticiansPage />} />
          <Route path="/politicians/:id" element={<PoliticianDetailPage />} />
          <Route path="/issues" element={<IssuesPage />} />
          <Route path="/issues/:id" element={<IssueDetailPage />} />
          <Route path="/statements/:id" element={<StatementDetailPage />} />

          {/* Admin routes */}
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/politicians/new" element={<PoliticianForm />} />
          <Route path="/admin/politicians/:id/edit" element={<PoliticianForm />} />
          <Route path="/admin/issues/new" element={<IssueForm />} />
          <Route path="/admin/issues/:id/edit" element={<IssueForm />} />
          <Route path="/admin/statements/new" element={<StatementForm />} />
          <Route path="/admin/statements/:id/edit" element={<StatementForm />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ThemeProvider>
  );
}
