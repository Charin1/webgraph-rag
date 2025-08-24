// src/components/MyNavbar.jsx

import React from 'react';
import { Link } from 'react-router-dom';

// Basic styling for the navbar. In a real app, you'd use a CSS file.
const navStyle = {
  backgroundColor: '#333',
  padding: '1rem',
  display: 'flex',
  gap: '1rem',
};

const linkStyle = {
  color: 'white',
  textDecoration: 'none',
  fontSize: '1.1rem',
};

function MyNavbar() {
  return (
    <nav style={navStyle}>
      <Link to="/" style={linkStyle}>
        Home
      </Link>
      <Link to="/about" style={linkStyle}>
        About
      </Link>
      <Link to="/dashboard" style={linkStyle}>
        Dashboard
      </Link>
    </nav>
  );
}

export default MyNavbar;