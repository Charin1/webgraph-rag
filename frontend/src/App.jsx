import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ToastContainer } from 'react-toastify'; // <-- Import ToastContainer
import 'react-toastify/dist/ReactToastify.css'; // <-- Import the CSS for toastify

import MyNavbar from './components/MyNavbar';
import HomePage from './pages/HomePage';
import SourcesPage from './pages/SourcesPage';
import NotFoundPage from './pages/NotFoundPage';

function App() {
  return (
    <BrowserRouter>
      {/* Add the ToastContainer here, it's invisible until a toast is triggered */}
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
      
      <div className="min-h-screen bg-gray-100">
        <MyNavbar />
        <main className="container mx-auto p-4">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/sources" element={<SourcesPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;