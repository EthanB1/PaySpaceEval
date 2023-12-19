import React, { useState } from 'react';

const SendBCY = () => {
  const [senderAddress, setSenderAddress] = useState('');
  const [privateKey, setPrivateKey] = useState('');
  const [recipientAddress, setRecipientAddress] = useState('');
  const [amount, setAmount] = useState('');
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // Replace 'http://localhost:5000' with your Flask server's URL if different
      const response = await fetch('http://localhost:5000/send_bcy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          privkey: privateKey, 
          address_from: senderAddress, 
          address_to: recipientAddress,
          amount: amount 
        }),
      });
      const data = await response.json();
      if(data.message) {
        setMessage(data.message);
      } else if (data.error) {
        setMessage(data.error);
      }
    } catch (error) {
      console.error('Error:', error);
      setMessage('An error occurred while sending BCY.');
    }
  };

  return (
    <div>
      <h1>Send BCY</h1>
      <form onSubmit={handleSubmit}>
        <input type="text" value={senderAddress} onChange={(e) => setSenderAddress(e.target.value)} placeholder="Sender Address" />
        <input type="text" value={privateKey} onChange={(e) => setPrivateKey(e.target.value)} placeholder="Private Key" />
        <input type="text" value={recipientAddress} onChange={(e) => setRecipientAddress(e.target.value)} placeholder="Recipient Address" />
        <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Amount" />
        <button type="submit">Send</button>
      </form>
      {message && <p>{message}</p>}
    </div>
  );
};

export default SendBCY;
