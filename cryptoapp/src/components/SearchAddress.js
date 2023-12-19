import React, { useState } from 'react';

const SearchAddress = () => {
  const [address, setAddress] = useState('');
  const [addressDetails, setAddressDetails] = useState(null);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:5000/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });
      const data = await response.json();
      if(data.error) {
        setMessage(data.error);
        setAddressDetails(null);
      } else {
        setAddressDetails(data);
        setMessage('');
      }
    } catch (error) {
      console.error('Error:', error);
      setMessage('An error occurred during the search.');
    }
  };

  return (
    <div>
      <h1>Search Address</h1>
      <form onSubmit={handleSubmit}>
        <input type="text" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Wallet Address" />
        <button type="submit">Search</button>
      </form>
      {message && <p>{message}</p>}
      {addressDetails && (
        <div>
          <p>Address: {addressDetails.address}</p>
          <p>Final Balance: {addressDetails.final_balance}</p>
          <p>Total Received: {addressDetails.total_received}</p>
          <p>Total Sent: {addressDetails.total_sent}</p>
          <p>Last Updated: {new Date(addressDetails.last_updated).toLocaleString()}</p>
          {addressDetails.qr_code && (
            <img src={`data:image/png;base64,${addressDetails.qr_code}`} alt="QR Code" />
          )}
        </div>
      )}
    </div>
  );
};

export default SearchAddress;
