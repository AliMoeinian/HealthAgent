import React from 'react';

interface NavbarProps {
  firstName: string;
  onLogout: () => void;
}

const Navbar: React.FC<NavbarProps> = ({ firstName, onLogout }) => {
  return (
    <nav className="bg-green-600 p-4 text-white flex justify-between items-center">
      <div>
        <h1 className="text-xl font-bold">HealthSync</h1>
      </div>
      <div>
        <span className="mr-4">Hi {firstName}, welcome ❤🖐</span>
        <button
          onClick={onLogout}
          className="px-4 py-2 bg-red-500 rounded-md hover:bg-red-600 transition"
        >
          Logout
        </button>
      </div>
    </nav>
  );
};

export default Navbar;