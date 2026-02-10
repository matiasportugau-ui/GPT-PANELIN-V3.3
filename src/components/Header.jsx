import React from 'react';
import '../styles/Header.css';

function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <h1 className="header-title">GPT PANELIN V3.2</h1>
        <nav className="header-nav">
          <button className="nav-button">Dashboard</button>
          <button className="nav-button">Settings</button>
          <button className="nav-button">About</button>
        </nav>
      </div>
    </header>
  );
}

export default Header;
