import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import WalletList from './components/WalletList';
import WalletDetails from './components/WalletDetails';
import SendBCY from './components/SendBCY';
import SearchAddress from './components/SearchAddress';
import CreateWallet from './components/CreateWallet';

function App() {
  return (
    <Router>
      <div>
        <nav>
          <ul>
            <li>
              <Link to="/">Wallet List</Link>
            </li>
            <li>
              <Link to="/send">Send BCY</Link>
            </li>
            <li>
              <Link to="/search">Search Address</Link>
            </li>
            <li>
              <Link to="/create">Create Wallet</Link>
            </li>
          </ul>
        </nav>
        <Routes>
          <Route path="/" element={<WalletList />} />
          <Route path="/wallet/:id" element={<WalletDetails />} />
          <Route path="/send" element={<SendBCY />} />
          <Route path="/search" element={<SearchAddress />} />
          <Route path="/create" element={<CreateWallet />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
