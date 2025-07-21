import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';

// Components
import Login from './components/Login';
import ProfileForm from './components/ProfileForm';
import Agents from './components/Agents';
import Navbar from './components/Navbar';
import Signup from './components/Signup';
import Footer from './components/Footer';

// User interface definition
interface User {
  user_id: number;
  first_name: string;
  has_profile: boolean;
}

const AppContent: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const navigate = useNavigate();

  // On initial load, check for a user session in localStorage
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  /**
   * Handles the login process by calling the backend API,
   * setting the user state, and navigating to the correct page.
   */
  const handleLogin = async (phoneNumber: string, nationalCode: string, password: string) => {
    try {
      const response = await axios.post('http://localhost:5000/api/login', {
        phoneNumber,
        nationalCode,
        password,
      });
      const userData: User = response.data;
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
      navigate(userData.has_profile ? '/agents' : '/profile');
    } catch (error) {
      console.error('Login error:', error);
      alert('Login failed. Please check your credentials.');
    }
  };

  /**
   * Handles user logout by clearing state and localStorage, then navigating to login.
   */
  const handleLogout = () => {
    localStorage.removeItem('user');
    setUser(null);
    navigate('/login');
  };

  /**
   * Called when the profile form is successfully saved.
   * Updates the user's state and navigates to the agents page.
   */
  const handleProfileSaved = () => {
    if (user) {
      const updatedUser = { ...user, has_profile: true };
      localStorage.setItem('user', JSON.stringify(updatedUser));
      setUser(updatedUser);
      navigate('/agents');
    }
  };

  return (
    // Flex container to ensure the footer sticks to the bottom
    <div className="flex flex-col min-h-screen bg-gray-50">
      {user && <Navbar firstName={user.first_name} onLogout={handleLogout} />}
      
      {/* Main content area that grows to fill available space */}
      <main className="flex-grow">
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={!user ? <Login onLogin={handleLogin} /> : <Navigate to="/" />} />
          <Route path="/signup" element={!user ? <Signup /> : <Navigate to="/" />} />

          {/* Protected Routes */}
          <Route 
            path="/profile" 
            element={user ? <ProfileForm onSave={handleProfileSaved} userId={user.user_id} /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/agents" 
            element={
              user && user.has_profile ? (
                <Agents userId={user.user_id} />
              ) : (
                <Navigate to={user ? '/profile' : '/login'} />
              )
            } 
          />
          
          {/* Default route to redirect users based on their status */}
          <Route 
            path="/" 
            element={
              user ? (
                <Navigate to={user.has_profile ? '/agents' : '/profile'} />
              ) : (
                <Navigate to="/login" />
              )
            } 
          />

          {/* Catch-all for any undefined routes */}
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
      
      <Footer />
    </div>
  );
};

/**
 * The main App component that sets up the Router.
 */
const App: React.FC = () => {
  return (
    <Router>
      <AppContent />
    </Router>
  );
};

export default App;