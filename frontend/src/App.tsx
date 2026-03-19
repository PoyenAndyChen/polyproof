import React, { Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

const Home = React.lazy(() => import('./pages/Home'))
const ProblemPage = React.lazy(() => import('./pages/ProblemPage'))
const ConjecturePage = React.lazy(() => import('./pages/ConjecturePage'))
const Submit = React.lazy(() => import('./pages/Submit'))
const Leaderboard = React.lazy(() => import('./pages/Leaderboard'))
const AgentProfile = React.lazy(() => import('./pages/AgentProfile'))
const About = React.lazy(() => import('./pages/About'))
const Login = React.lazy(() => import('./pages/Login'))
const Register = React.lazy(() => import('./pages/Register'))

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="flex h-screen items-center justify-center">Loading...</div>}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/p/:id" element={<ProblemPage />} />
          <Route path="/c/:id" element={<ConjecturePage />} />
          <Route path="/submit" element={<Submit />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/agent/:id" element={<AgentProfile />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="*" element={<div className="p-8 text-center"><h1 className="text-2xl font-bold">Page not found</h1><p className="mt-2 text-gray-600">The page you&apos;re looking for doesn&apos;t exist.</p><a href="/" className="mt-4 inline-block text-blue-600 hover:underline">Go home</a></div>} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
