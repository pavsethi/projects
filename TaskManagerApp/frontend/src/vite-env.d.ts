/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend API origin. Empty in dev (proxied); set to the backend URL in prod. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
