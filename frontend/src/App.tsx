import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import SocialTasks from './pages/SocialTasks';
import CreateSocialTask from './pages/SocialTasks/CreateTask';
import SocialTaskDetail from './pages/SocialTasks/Detail';
import SocialLeads from './pages/SocialLeads';
import B2BTasks from './pages/B2BTasks';
import CreateB2BTask from './pages/B2BTasks/CreateTask';
import B2BTaskDetail from './pages/B2BTasks/Detail';
import B2BLeads from './pages/B2BLeads';
import Settings from './pages/Settings';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="social-tasks" element={<SocialTasks />} />
          <Route path="social-tasks/create" element={<CreateSocialTask />} />
          <Route path="social-tasks/:id" element={<SocialTaskDetail />} />
          <Route path="social-leads" element={<SocialLeads />} />
          <Route path="b2b-tasks" element={<B2BTasks />} />
          <Route path="b2b-tasks/create" element={<CreateB2BTask />} />
          <Route path="b2b-tasks/:id" element={<B2BTaskDetail />} />
          <Route path="b2b-leads" element={<B2BLeads />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
