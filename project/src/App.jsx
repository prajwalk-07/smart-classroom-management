import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// Import your components
import Login from './components/Login';
import StudentDashboard from './components/Dashboard/StudentDashboard/StudentDashboard';
function App() {
  return (
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/student/*" element={<StudentDashboard />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
  );
}

export default App;