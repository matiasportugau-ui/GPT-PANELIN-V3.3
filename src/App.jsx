import React from 'react';
import Header from './components/Header';
import ChatPanel from './components/ChatPanel';
import './styles/App.css';

function App() {
  return (
    <div className="app-container">
      <Header />
      <main className="main-content">
        <ChatPanel />
      </main>
    </div>
  );
}

export default App;
