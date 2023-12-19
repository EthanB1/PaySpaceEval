import React, { useState } from 'react';

const CreateWallet = () => {
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage(''); // Clear any previous message
    try {
      const response = await fetch('http://localhost:5000/create_wallet', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      const data = await response.json();
      if (data.message) {
        setMessage(data.message); // Display success message
      }
    } catch (error) {
      setMessage('Error: Unable to create wallet.'); // Display error message
    }
  };

  return (
    <div>
      <h1>Create Wallet</h1>
      <form onSubmit={handleSubmit}>
        <button type="submit">Create Wallet</button>
      </form>
      {message && <p>{message}</p>} {/* Display message */}
    </div>
  );
};

export default CreateWallet;
