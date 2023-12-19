from flask import Flask, request, render_template, jsonify
from datetime import datetime, timedelta
from pymongo import MongoClient
import time
import blockcypher
import pyqrcode
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
API_TOKEN = os.getenv('BLOCKCYPHER_API_TOKEN')

# MongoDB setup
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI, tls=True)
db = client.cryptodb

app = Flask(__name__)

@app.route('/wallet/<wallet_id>')
def wallet_details(wallet_id):
    # Retrieve wallet details by its MongoDB ObjectId
    wallet = db.addresses.find_one({'_id': ObjectId(wallet_id)})
    if wallet:
        qr_code = pyqrcode.create(wallet['address'])  
        wallet['qr_code'] = qr_code.png_as_base64_str(scale=5)
        wallet['_id'] = str(wallet['_id'])
        return render_template('wallet_details.html', wallet=wallet)
    else:
        return "Wallet not found", 404

@app.route('/wallets')
def wallets_list():
    # List all wallets in the database
    wallets = list(db.addresses.find({}))
    for wallet in wallets:
        wallet['_id'] = str(wallet['_id'])
    return render_template('wallets_list.html', wallets=wallets)


@app.route('/send_bcy', methods=['GET', 'POST'])
def send_bcy():
    if request.method == 'POST':
        data = request.json
        privkey = data["privkey"]
        address_from = data["address_from"]
        address_to = data["address_to"]
        amount = data["amount"]

        # Get balance from BlockCypher for the sender
        sender_info = blockcypher.get_address_overview(address_from, coin_symbol='bcy')
        sender_balance = sender_info["balance"]

        if sender_balance < amount:
            return jsonify(message="Not enough funds for this transaction.")

        try:
            tx_ref = blockcypher.simple_spend(from_privkey=privkey, to_address=address_to, to_satoshis=amount, coin_symbol='bcy', api_key=API_TOKEN)

            # Delay to allow transaction to propagate
            time.sleep(25)  

            # Check for confirmations
            transaction_details = blockcypher.get_transaction_details(tx_ref, coin_symbol='bcy')
            confirmations = transaction_details['confirmations']

            # Update transaction status based on confirmations
            status = 'confirmed' if confirmations >= 1 else 'pending'

            # Insert or update transaction in MongoDB
            transaction = {
                'sender': address_from,
                'receiver': address_to,
                'amount': amount,
                'status': status,
                'tx_ref': tx_ref,
                'timestamp': datetime.utcnow(),
                'confirmations': confirmations
            }
            db.transactions.update_one({'tx_ref': tx_ref}, {'$set': transaction}, upsert=True)

            if status == 'confirmed':
                # Update sender and receiver address details in MongoDB
                update_address_data(address_from)
                update_address_data(address_to)

            return jsonify(message=f"Transaction successful. TX Hash: {tx_ref}, Status: {status}")
        except Exception as e:
            return jsonify(message=f"Transaction failed: {str(e)}")
    else:
        # Render the form for GET requests
        return render_template('send_bcy.html')

def update_address_data(address):
    # Fetch latest address data from BlockCypher
    address_info = blockcypher.get_address_overview(address, coin_symbol='bcy')

    # Prepare the update data
    update_data = {
        'final_balance': address_info['final_balance'],
        'total_received': address_info['total_received'],
        'total_sent': address_info['total_sent']
    }

    # Update the address document in the MongoDB database
    db.addresses.update_one({'address': address}, {'$set': update_data})

@app.route('/search', methods=['GET', 'POST'])
def search_address():
    if request.method == 'POST':
        address = request.form['address']
        existing_address = db.public_addresses.find_one({'address': address})

        # Check if data exists and if it's older than 30 minutes
        if existing_address:
            if datetime.utcnow() - existing_address.get('last_updated', datetime.utcfromtimestamp(0)) > timedelta(minutes=30):
                # Data is older than 30 minutes, fetch new data and update
                address_data = blockcypher.get_address_overview(address, coin_symbol='bcy')
                updated_record = {
                    'address': address,
                    'final_balance': address_data['final_balance'],
                    'total_received': address_data['total_received'],
                    'total_sent': address_data['total_sent'],
                    'last_updated': datetime.utcnow()
                }
                db.public_addresses.update_one({'address': address}, {'$set': updated_record})
                existing_address = updated_record  # Update the local variable for rendering

        else:
            # Address not found in DB, fetch and insert new data
            address_data = blockcypher.get_address_overview(address, coin_symbol='bcy')
            existing_address = {
                'address': address,
                'final_balance': address_data['final_balance'],
                'total_received': address_data['total_received'],
                'total_sent': address_data['total_sent'],
                'last_updated': datetime.utcnow()
            }
            db.public_addresses.insert_one(existing_address)

        # Generate QR code
        qr_code = pyqrcode.create(address)
        existing_address['qr_code'] = qr_code.png_as_base64_str(scale=5)

        return render_template('address_details.html', address=existing_address)
    else:
        return render_template('search.html')

@app.route('/create_wallet', methods=['GET', 'POST'])
def create_wallet():
    if request.method == 'POST':
        # Generate new wallet using BlockCypher
        wallet_info = blockcypher.generate_new_address(coin_symbol='bcy', api_key=API_TOKEN)
        address = wallet_info['address']
        private_key = wallet_info['private']
        public_key = wallet_info['public']

        # Create wallet record
        wallet_record = {
            'address': address,
            'private_key': private_key,  # Note: In a real app, don't store private keys
            'public_key': public_key,
            'final_balance': 0,
            'total_received': 0,
            'total_sent': 0
        }

        # Insert into MongoDB
        db.addresses.insert_one(wallet_record)

        return jsonify({"message": "Wallet created successfully", "wallet_id": str(wallet_record['_id'])})
    else:
        return render_template('create_wallet.html')

if __name__ == '__main__':
    app.run(debug=True)