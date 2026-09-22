import { useEffect, useState } from 'react'
import './App.css'

interface Task {
  id: string
  goal: string
  status: string
  risk_level: number
  created_at: string
}

function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [health, setHealth] = useState<string>("Checking...")
  
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

  useEffect(() => {
    fetch(`${apiUrl}/health`)
      .then(res => res.json())
      .then(data => setHealth(data.status))
      .catch(() => setHealth("Error connecting to API"))

    fetchTasks()
  }, [apiUrl])

  const fetchTasks = () => {
    fetch(`${apiUrl}/tasks`)
      .then(res => res.json())
      .then(data => setTasks(data))
      .catch(err => console.error(err))
  }

  const createTask = () => {
    fetch(`${apiUrl}/tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ goal: 'New test task from Dashboard', risk_level: 0 })
    })
    .then(res => res.json())
    .then(() => fetchTasks())
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8 w-full">
      <div className="max-w-4xl mx-auto">
        <header className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">LinuxPilot Dashboard</h1>
            <p className="text-gray-500">High-End Production Architecture</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-600">API Status:</span>
            <span className={`px-2 py-1 rounded text-sm font-medium ${health === 'ok' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
              {health.toUpperCase()}
            </span>
          </div>
        </header>

        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-800">Active Tasks</h2>
            <button 
              onClick={createTask}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium transition-colors"
            >
              + Create Test Task
            </button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-200 text-gray-600 text-sm">
                  <th className="pb-3 pr-4 font-medium">Task ID</th>
                  <th className="pb-3 pr-4 font-medium">Goal</th>
                  <th className="pb-3 pr-4 font-medium">Status</th>
                  <th className="pb-3 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {tasks.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-gray-500">
                      No tasks found. Create one to get started.
                    </td>
                  </tr>
                ) : (
                  tasks.map(task => (
                    <tr key={task.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 pr-4 text-xs font-mono text-gray-500">
                        {task.id.split('-')[0]}
                      </td>
                      <td className="py-3 pr-4 font-medium text-gray-900">
                        {task.goal}
                      </td>
                      <td className="py-3 pr-4">
                        <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-medium">
                          {task.status}
                        </span>
                      </td>
                      <td className="py-3 text-sm text-gray-500">
                        {new Date(task.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
