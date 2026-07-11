import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { AuthGuard } from '@/components/auth/AuthGuard';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Toaster } from '@/components/ui/toaster';
import { QueryProvider } from '@/providers/QueryProvider';
import { Router } from '@/router';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryProvider>
        <AuthGuard>
          <Router />
          <Toaster />
        </AuthGuard>
      </QueryProvider>
    </ErrorBoundary>
  </StrictMode>
);
