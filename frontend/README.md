# Navee Frontend

React + Vite + TypeScript + Tailwind CSS dashboard for the Navee backend.

## Setup

```bash
cd frontend
npm install
```

## Run (dev)

```bash
npm run dev
```

Opens at http://localhost:5173. The dev server proxies `/api/*` to the backend
at http://localhost:8000 (see `vite.config.ts`), so start the backend first.

## Build / preview

```bash
npm run build     # type-check (tsc) + bundle to dist/
npm run preview   # serve the production build locally
```

## Notes

- Standard Vite `react-ts` setup with the JSX transform (`"jsx": "react-jsx"`).
- Tailwind CSS v4 via the `@tailwindcss/vite` plugin (no separate PostCSS
  config needed).
