import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

const WalletDetails = () => {
  const [wallet, setWallet] = useState(null);
  const { id } = useParams();

  useEffect(() => {
    const fetchWalletDetails = async () => {
      try {
        const response = await fetch(`http://localhost:5000/wallet/${id}`);
        if (response.ok) {
          const data = await response.json();
          setWallet(data);
        } else {
          console.error(`Failed to load wallet details: ${response.status}`);
        }
      } catch (error) {
        console.error('Error:', error);
      }
    };
    fetchWalletDetails();
  }, [id]);

  const renderTransactions = (transactions) => {
    return transactions && transactions.map((tx, index) => {
      const dateString = tx.timestamp['$date'];
      const date = new Date(dateString);
      const formattedDate = date.toLocaleString();

      return (
        <li key={index}>
          Amount: {tx.amount}, Date: {formattedDate}
        </li>
      );
    });
  };

  return (
    <div>
      <h1>Wallet Details</h1>
      {wallet ? (
        <div>
          <p>Address: {wallet.address}</p>
          <p>Private Key: {wallet.private_key}</p>
          <p>Public Key: {wallet.public_key}</p>
          <p>Final Balance: {wallet.final_balance}</p>
          <p>Total Received: {wallet.total_received}</p>
          <p>Total Sent: {wallet.total_sent}</p>
          <img src={`data:image/png;base64,${wallet.qr_code}`} alt="QR Code" />
          <h2>Sent Transactions</h2>
          {wallet.sent_transactions.length > 0 ? (
            <ul>{renderTransactions(wallet.sent_transactions)}</ul>
          ) : (
            <ul><li>No sent transactions</li></ul>
          )}
          <h2>Received Transactions</h2>
          {wallet.received_transactions.length > 0 ? (
            <ul>{renderTransactions(wallet.received_transactions)}</ul>
          ) : (
            <ul><li>No received transactions</li></ul>
          )}
        </div>
      ) : (
        <p>Loading wallet details...</p>
      )}
    </div>
  );
};

export default WalletDetails;
