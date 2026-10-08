import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { LoginPage } from './pages/LoginPage';
import { SubmitPage } from './pages/SubmitPage';
import { ControlOverviewPage } from './pages/ControlOverviewPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { WorkspacePage } from './pages/WorkspacePage';
import { VerifyPassportPage } from './pages/VerifyPassportPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public authentication and passport verification routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/verify/:token" element={<VerifyPassportPage />} />

        {/* Application Shell Routes */}
        <Route
          path="/submit"
          element={
            <AppShell>
              <SubmitPage />
            </AppShell>
          }
        />

        <Route
          path="/control"
          element={
            <AppShell>
              <ControlOverviewPage />
            </AppShell>
          }
        />

        <Route
          path="/control/queue"
          element={
            <AppShell>
              <ReviewQueuePage />
            </AppShell>
          }
        />

        <Route
          path="/control/workspace/:auditId"
          element={
            <AppShell>
              <WorkspacePage />
            </AppShell>
          }
        />

        {/* Supporting navigation destination aliases for Control Center */}
        <Route
          path="/control/audits"
          element={
            <AppShell>
              <ReviewQueuePage />
            </AppShell>
          }
        />

        <Route
          path="/control/sources"
          element={
            <AppShell>
              <ControlOverviewPage />
            </AppShell>
          }
        />

        <Route
          path="/control/policies"
          element={
            <AppShell>
              <ControlOverviewPage />
            </AppShell>
          }
        />

        <Route
          path="/control/metrics"
          element={
            <AppShell>
              <ControlOverviewPage />
            </AppShell>
          }
        />

        <Route
          path="/control/admin"
          element={
            <AppShell>
              <ControlOverviewPage />
            </AppShell>
          }
        />

        {/* Default redirect to Control Overview */}
        <Route path="/" element={<Navigate to="/control" replace />} />
        <Route path="*" element={<Navigate to="/control" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
