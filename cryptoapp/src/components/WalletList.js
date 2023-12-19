import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const WalletList = () => {
  const [wallets, setWallets] = useState([]);

  useEffect(() => {
    const fetchWallets = async () => {
      try {
        const response = await fetch('http://localhost:5000/wallets');
        const data = await response.json();
        setWallets(data);
      } catch (error) {
        console.error('Error:', error);
      }
    };
    fetchWallets();
  }, []);

  return (
    <div>
      <h1>Wallet List</h1>
      <ul>
        {wallets.map(wallet => (
          <li key={wallet._id}>
            <Link to={`/wallet/${wallet._id}`}>{wallet.address}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default WalletList;
