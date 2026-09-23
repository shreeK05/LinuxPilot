import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthModal } from './components/AuthModal'
import { Layout } from './components/Layout'
import { Home } from './components/Home'
import { TaskHistory, type Task } from './components/TaskHistory'
import { ApprovalQueue } from './components/ApprovalQueue'
import { TaskDetails } from './components/TaskDetails'
import { fetchWithAuth } from './utils/api'

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [health, setHealth] = useState<string>("Checking...")
  const [tasks, setTasks] = useState<Task[]>([])

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

  useEffect(() => {
    fetchWithAuth(`${apiUrl}/health`)
      .then(res => res.json())
      .then(data => setHealth(data.status))
      .catch(() => setHealth("Error connecting to API"))

    const fetchTasks = () => {
      if (!token) return;
      fetchWithAuth(`${apiUrl}/tasks`)
        .then(res => {
            if (res.ok) return res.json();
            throw new Error("Failed to fetch");
        })
        .then(data => setTasks(data))
        .catch(err => console.error(err))
    }

    fetchTasks()
    const intervalId = setInterval(fetchTasks, 5000);

    const handleAuthError = () => setToken(null);
    window.addEventListener('auth-error', handleAuthError);

    return () => {
        clearInterval(intervalId);
        window.removeEventListener('auth-error', handleAuthError);
    };
  }, [apiUrl, token])

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  if (!token) {
    return <AuthModal apiUrl={apiUrl} onLoginSuccess={(t) => {
        localStorage.setItem('token', t);
        setToken(t);
    }} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout health={health} onLogout={handleLogout} />}>
          <Route index element={<Home apiUrl={apiUrl} />} />
          <Route path="tasks" element={<TaskHistory tasks={tasks} />} />
          <Route path="tasks/:id" element={<TaskDetails apiUrl={apiUrl} />} />
          <Route path="approvals" element={<ApprovalQueue tasks={tasks} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
