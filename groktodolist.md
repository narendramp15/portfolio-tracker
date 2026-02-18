# Portfolio Tracker Bugs and Todo List

## Backend Linting Issues
- **Description**: Numerous whitespace errors (blank lines with trailing spaces), deprecated typing imports (`typing.Dict` → `dict`, `typing.List` → `list`, `typing.Optional` → `X | None`), unused imports, and use of `timezone.utc` instead of `datetime.UTC`.
- **Impact**: Code quality issues, potential type checking failures, and non-compliance with modern Python standards.
- **Files Affected**: `portfolio_tracker/services/symbol_mapper.py`, `portfolio_tracker/services/tax_calculator.py`, `portfolio_tracker/services/technical_indicators.py`, etc.
- **Fix**: Run `uv run ruff check --fix portfolio_tracker` and `uv run black portfolio_tracker` to auto-fix most issues. Manually update deprecated imports and timezone usage.

## Frontend Fast Refresh Issues
- **Description**: Provider files export both the provider component and hook functions, violating React Fast Refresh rules (files should export only components for hot reloading).
- **Impact**: Development experience degraded; hot reload may not work properly for these files.
- **Files Affected**: `frontend/src/providers/auth/AuthProvider.tsx`, `frontend/src/providers/theme/ThemeProvider.tsx`
- **Fix**: Move hooks (`useAuth`, `useTheme`) to separate files (e.g., `hooks/useAuth.ts`, `hooks/useTheme.ts`) and import them into the providers.

## ThemeProvider setState in useEffect
- **Description**: `useEffect` calls `setModeState` synchronously, which can trigger cascading renders and hurt performance. React docs recommend avoiding setState in effects unless synchronizing with external systems.
- **Impact**: Potential performance issues and unnecessary re-renders during theme initialization.
- **File Affected**: `frontend/src/providers/theme/ThemeProvider.tsx`
- **Fix**: Initialize theme state directly in `useState` based on localStorage and media query, avoiding `setState` in `useEffect`. Use a lazy initializer for `useState`.

## Missing JWT Token Refresh Logic
- **Description**: The Axios API client (`frontend/src/lib/api.ts`) adds auth headers but has no response interceptor to handle 401 errors (expired tokens). No automatic token refresh or redirect to login on auth failure.
- **Impact**: Users get silent failures or errors when JWT expires; must manually re-login. Poor UX for long sessions.
- **File Affected**: `frontend/src/lib/api.ts`
- **Fix**: Add Axios response interceptor to catch 401s, attempt token refresh if possible (though backend lacks refresh endpoint), or redirect to `/login`. Consider implementing refresh tokens in backend if needed.

## API Client Error Handling
- **Description**: No global error handling for API responses (e.g., network errors, server errors). Errors are handled ad-hoc in components.
- **Impact**: Inconsistent error UX; users may see raw error messages or crashes.
- **File Affected**: `frontend/src/lib/api.ts`
- **Fix**: Add response interceptor in `api.ts` for global error handling (e.g., show toast notifications for 500s, redirect on 401s).

## Potential Security Issue in Token Extraction
- **Description**: `get_access_token` logs full request headers on failure, which could leak sensitive info in logs.
- **Impact**: Information disclosure if logs are exposed.
- **File Affected**: `portfolio_tracker/deps.py`
- **Fix**: Sanitize logged headers (e.g., redact Authorization header).

## Test Suite Interruptions
- **Description**: Running `pytest` hangs or gets interrupted, preventing validation of functionality.
- **Impact**: Unable to verify bug fixes or regressions.
- **Fix**: Investigate test setup (e.g., database connections, async issues). Run individual test files or use `--tb=short` for better error visibility.