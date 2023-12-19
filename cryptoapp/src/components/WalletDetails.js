import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

const WalletDetails = () => {
  const [wallet, setWallet] = useState(null);
  const { id } = useParams();

  useEffect(() => {
    const fetchWalletDetails = async () => {
      try {
        const response = await fetch(`http://localhost:5000/wallet/${id}`);
        const data = await response.json();
        setWallet(data);
      } catch (error) {
        console.error('Error:', error);
      }
    };
    fetchWalletDetails();
  }, [id]);

  return (
    <div>
      <h1>Wallet Details</h1>
      {wallet && (
        <div>
          <p>Address: {wallet.address}</p>
          <p>Private Key: {wallet.private_key}</p>
          <p>Public Key: {wallet.public_key}</p>
          <p>Final Balance: {wallet.final_balance}</p>
          <p>Total Received: {wallet.total_received}</p>
          <p>Total Sent: {wallet.total_sent}</p>
          <img src={`data:image/png;base64,${wallet.qr_code}`} alt="QR Code" />
        </div>
      )}
    </div>
  );
};

export default WalletDetails;
