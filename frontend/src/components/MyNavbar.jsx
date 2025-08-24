import React from 'react';
import { NavLink } from 'react-router-dom';

function MyNavbar() {
  const activeLinkStyle = {
    color: '#10B981',
    textDecoration: 'underline',
    textUnderlineOffset: '4px',
  };

  return (
    <nav className="bg-white shadow-md sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* App Title/Logo Updated */}
          <div className="text-xl font-bold text-gray-800">
            WebGraph RAG
          </div>
          
          {/* Navigation Links Updated */}
          <div className="flex items-center space-x-8 text-lg">
            <NavLink 
              to="/"
              style={({ isActive }) => (isActive ? activeLinkStyle : undefined)}
              className="text-gray-600 hover:text-blue-600 transition-colors duration-200"
            >
              Chat
            </NavLink>
            
            <NavLink 
              to="/sources"
              style={({ isActive }) => (isActive ? activeLinkStyle : undefined)}
              className="text-gray-600 hover:text-blue-600 transition-colors duration-200"
            >
              Sources
            </NavLink>
            
            {/* The "About" NavLink has been removed */}
          </div>
        </div>
      </div>
    </nav>
  );
}

export default MyNavbar;