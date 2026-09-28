import Dashboard from "@/components/Dashboard";

export const metadata = {
  title: "LinuxPilot Dashboard",
  description: "Trust-First OS Agent for Linux",
};

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-950 text-gray-100">
      <Dashboard />
    </main>
  );
}
