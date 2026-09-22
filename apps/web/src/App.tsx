import { useEffect, useState } from 'react'
import { TaskTable } from './components/TaskTable'
import type { Task } from './components/TaskTable'
import { TaskDetails } from './components/TaskDetails'
import { Dashboard } from './components/Dashboard'
import { ActivityFeed } from './components/ActivityFeed'
import './App.css'

function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [health, setHealth] = useState<string>("Checking...")
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [isCreatingGoal, setIsCreatingGoal] = useState(false)
  const [newGoalText, setNewGoalText] = useState("")

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

  useEffect(() => {
    fetch(`${apiUrl}/health`)
      .then(res => res.json())
      .then(data => setHealth(data.status))
      .catch(() => setHealth("Error connecting to API"))

    const fetchTasks = () => {
      fetch(`${apiUrl}/tasks`)
        .then(res => res.json())
        .then(data => setTasks(data))
        .catch(err => console.error(err))
    }

    fetchTasks()
    const intervalId = setInterval(fetchTasks, 5000);
    return () => clearInterval(intervalId);
  }, [apiUrl])

  const submitNewGoal = () => {
    if (!newGoalText.trim()) {
      alert("Goal cannot be empty.");
      return;
    }
    fetch(`${apiUrl}/tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ goal: newGoalText.trim(), risk_level: 1 })
    })
    .then(res => res.json())
    .then(() => {
        setIsCreatingGoal(false);
        setNewGoalText("");
    })
    .catch(err => console.error(err))
  }

  const selectedTask = tasks.find(t => t.id === selectedTaskId)

  return (
    <div className="min-h-screen bg-gray-100 p-8 w-full">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">LinuxPilot Dashboard</h1>
            <p className="text-gray-500">Professional Agent Dashboard (Phase 9)</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-600">API Status:</span>
            <span className={`px-2 py-1 rounded text-sm font-medium ${health === 'ok' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
              {health.toUpperCase()}
            </span>
          </div>
        </header>

        {selectedTask ? (
          <TaskDetails
            task={selectedTask}
            onBack={() => setSelectedTaskId(null)}
            apiUrl={apiUrl}
          />
        ) : (
          <>
            <Dashboard apiUrl={apiUrl} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2">
                <div className="bg-white rounded-lg shadow p-6 mb-8">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-gray-800">Task History</h2>
                    <button
                      onClick={() => setIsCreatingGoal(true)}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium transition-colors"
                    >
                      + Create Goal
                    </button>
                  </div>
                  <TaskTable tasks={tasks} onSelectTask={setSelectedTaskId} />
                </div>
              </div>
              <div className="lg:col-span-1">
                <ActivityFeed apiUrl={apiUrl} />
              </div>
            </div>
          </>
        )}

      </div>

      {isCreatingGoal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full shadow-xl">
            <h3 className="text-xl font-bold mb-4 text-gray-900">Create New Goal</h3>
            <textarea
              className="w-full border rounded p-3 mb-4 h-32 text-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="What would you like LinuxPilot to do?"
              value={newGoalText}
              onChange={(e) => setNewGoalText(e.target.value)}
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setIsCreatingGoal(false); setNewGoalText(""); }}
                className="px-4 py-2 border rounded text-gray-600 hover:bg-gray-100 font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={submitNewGoal}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-medium transition-colors"
              >
                Create Goal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
