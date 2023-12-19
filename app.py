from flask import Flask, request, jsonify
from flask_cors import CORS
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
CORS(app)

@app.route('/wallet/<wallet_id>')
def wallet_details(wallet_id):
    wallet = db.addresses.find_one({'_id': ObjectId(wallet_id)})
    if wallet:
        # Convert MongoDB ObjectId to string for JSON serialization
        wallet['_id'] = str(wallet['_id'])
        #QR code generation
        qr_code = pyqrcode.create(wallet['address'])
        wallet['qr_code'] = qr_code.png_as_base64_str(scale=5)
        return jsonify(wallet)
    else:
        return jsonify({"error": "Wallet not found"}), 404


@app.route('/wallets')
def wallets_list():
    wallets = list(db.addresses.find({}))
    # Convert MongoDB ObjectId to string for JSON serialization
    wallets = [{**wallet, '_id': str(wallet['_id'])} for wallet in wallets]
    return jsonify(wallets)
    
@app.route('/send_bcy', methods=['POST'])
def send_bcy():
    data = request.json
    privkey = data.get("privkey")
    address_from = data.get("address_from")
    address_to = data.get("address_to")
    amount = data.get("amount")

    if not all([privkey, address_from, address_to, amount]):
        return jsonify({"error": "Missing data"}), 400

    try:
        # Convert amount to integer
        amount_int = int(amount)

        sender_info = blockcypher.get_address_overview(address_from, coin_symbol='bcy')
        if sender_info["balance"] < amount_int:
            return jsonify({"error": "Not enough funds for this transaction."}), 400

        tx_ref = blockcypher.simple_spend(from_privkey=privkey, to_address=address_to, to_satoshis=amount_int, coin_symbol='bcy', api_key=API_TOKEN)
        time.sleep(25)

        transaction_details = blockcypher.get_transaction_details(tx_ref, coin_symbol='bcy')
        status = 'confirmed' if transaction_details['confirmations'] >= 1 else 'pending'

        transaction = {
            'sender': address_from,
            'receiver': address_to,
            'amount': amount_int,
            'status': status,
            'tx_ref': tx_ref,
            'timestamp': datetime.utcnow(),
            'confirmations': transaction_details['confirmations']
        }
        db.transactions.update_one({'tx_ref': tx_ref}, {'$set': transaction}, upsert=True)

        if status == 'confirmed':
            update_address_data(address_from)
            update_address_data(address_to)

        return jsonify({"message": f"Transaction successful. TX Hash: {tx_ref}, Status: {status}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def update_address_data(address):
    address_info = blockcypher.get_address_overview(address, coin_symbol='bcy')
    update_data = {
        'final_balance': address_info['final_balance'],
        'total_received': address_info['total_received'],
        'total_sent': address_info['total_sent']
    }
    db.addresses.update_one({'address': address}, {'$set': update_data})

@app.route('/search', methods=['POST'])
def search_address():
    data = request.json
    address = data.get('address')

    if not address:
        return jsonify({"error": "Address is required"}), 400

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
            existing_address = updated_record
            existing_address['_id'] = str(existing_address['_id'])  # Convert ObjectId to string
        else:
            # Convert ObjectId to string for the existing record
            existing_address['_id'] = str(existing_address['_id'])

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
        inserted_address = db.public_addresses.insert_one(existing_address)
        existing_address['_id'] = str(inserted_address.inserted_id)  # Convert ObjectId to string

    # Generate QR code
    qr_code = pyqrcode.create(address)
    existing_address['qr_code'] = qr_code.png_as_base64_str(scale=5)

    return jsonify(existing_address)



@app.route('/create_wallet', methods=['POST'])
def create_wallet():
    # Generate new wallet using BlockCypher
    wallet_info = blockcypher.generate_new_address(coin_symbol='bcy', api_key=API_TOKEN)
    address = wallet_info['address']
    private_key = wallet_info['private']
    public_key = wallet_info['public']

    # Create wallet record
    wallet_record = {
        'address': address,
        'private_key': private_key,  
        'public_key': public_key,
        'final_balance': 0,
        'total_received': 0,
        'total_sent': 0
    }

    # Insert into MongoDB
    db.addresses.insert_one(wallet_record)

    return jsonify({"message": "Wallet created successfully", "wallet_id": str(wallet_record['_id'])})


if __name__ == '__main__':
    app.run(debug=True)