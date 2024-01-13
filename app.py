from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError
import time
import blockcypher
import pyqrcode
from bson import json_util
from bson.objectid import ObjectId
from dotenv import load_dotenv
import logging
import os
import re


load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
API_TOKEN = os.getenv('BLOCKCYPHER_API_TOKEN')

# MongoDB setup
client = MongoClient(MONGO_URI, tls=True)
db = client.cryptodb

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Functions to sanitize input for send_bcy and search route
def is_valid_address(address):
    return re.match(r"^[a-zA-Z0-9]{27,35}$", address) is not None

def is_valid_privkey(privkey):
    return re.match(r"^[A-Fa-f0-9]{64}$", privkey) is not None

@app.route('/wallet/<wallet_id>')
def wallet_details(wallet_id):
    try:
        oid = ObjectId(wallet_id)
        wallet = db.addresses.find_one({'_id': oid})
        if not wallet:
            return jsonify({"error": "Wallet not found"}), 404

        wallet['_id'] = str(wallet['_id'])
        qr_code = pyqrcode.create(wallet['address'])
        wallet['qr_code'] = qr_code.png_as_base64_str(scale=5)

        # Fetch transactions, ensuring to convert ObjectId to strings
        wallet['sent_transactions'] = list(db.transactions.find({"sender": wallet['address']}).sort("timestamp", DESCENDING))
        for transaction in wallet['sent_transactions']:
            transaction['_id'] = str(transaction['_id'])

        wallet['received_transactions'] = list(db.transactions.find({"receiver": wallet['address']}).sort("timestamp", DESCENDING))
        for transaction in wallet['received_transactions']:
            transaction['_id'] = str(transaction['_id'])

        # Use json_util.dumps to correctly serialize MongoDB documents
        return json_util.dumps(wallet), 200, {'ContentType': 'application/json'}

    except ConnectionFailure:
        logger.error("Database connection failed", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 503
    except PyMongoError as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 500
    
@app.route('/wallets')
def wallets_list():
    try:
        # Fetching all wallets from the database
        wallets = list(db.addresses.find({}))

        # Convert MongoDB ObjectId to string for JSON serialization
        wallets = [{**wallet, '_id': str(wallet['_id'])} for wallet in wallets]

        return jsonify(wallets)
    except ConnectionFailure:
        logger.error("Database connection failed", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 503
    except PyMongoError as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 500

@app.route('/send_bcy', methods=['POST'])
def send_bcy():
    try:
        # Retrieve data from the POST request
        data = request.json
        privkey, address_from, address_to, amount = data.get("privkey"), data.get("address_from"), data.get("address_to"), data.get("amount")

        # Check if all required fields are provided
        if not all([privkey, address_from, address_to, amount]):
            return jsonify({"error": "Missing required fields"}), 400
        # Validate address and private key formats
        if not is_valid_address(address_from) or not is_valid_address(address_to):
            return jsonify({"error": "Invalid address format"}), 400
        if not is_valid_privkey(privkey):
            return jsonify({"error": "Invalid private key format"}), 400

        # Convert and validate the transaction amount
        try:
            amount_int = int(amount)
            if amount_int <= 0:
                raise ValueError("Amount must be positive")
        except ValueError as ve:
            logger.error(f"Value error: {str(ve)}", exc_info=True)
            return jsonify({"error": "Not a valid amount. Please enter a number in digits e.g. 2500"}), 400

        # Retrieve sender's wallet information
        try:
            sender_info = blockcypher.get_address_overview(address_from, coin_symbol='bcy')
        except Exception as e:
            logger.error(f"Failed to retrieve wallet info: {str(e)}", exc_info=True)
            return jsonify({"error": "An error occurred processing the transaction. Please try again later."}), 500

        if sender_info["balance"] < amount_int:
            return jsonify({"error": "The sending address has insufficient funds for the transaction"}), 400

        # Creating and sending the transaction
        try:
            tx_ref = blockcypher.simple_spend(from_privkey=privkey, to_address=address_to, to_satoshis=amount_int, coin_symbol='bcy', api_key=API_TOKEN)
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}", exc_info=True)
            return jsonify({"error": "An error occurred while processing the transaction. Please try again later."}), 500

        time.sleep(25)  # Allowing time for the transaction to propagate

        # Checking the status of the transaction
        transaction_details = blockcypher.get_transaction_details(tx_ref, coin_symbol='bcy')
        status = 'confirmed' if transaction_details['confirmations'] >= 1 else 'pending'

        # Record the transaction in the database
        transaction = {'sender': address_from, 'receiver': address_to, 'amount': amount_int, 'status': status, 'tx_ref': tx_ref, 'timestamp': datetime.utcnow(), 'confirmations': transaction_details['confirmations']}
        db.transactions.update_one({'tx_ref': tx_ref}, {'$set': transaction}, upsert=True)

        if status == 'confirmed':
            update_address_data(address_from)
            update_address_data(address_to)

        return jsonify({"message": f"Transaction successful. TX Hash: {tx_ref}, Status: {status}"})
    except ConnectionFailure:
        logger.error("Database connection failed", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 503
    except PyMongoError as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 500

# Function to update address data in the database
def update_address_data(address):
    address_info = blockcypher.get_address_overview(address, coin_symbol='bcy')
    update_data = {'final_balance': address_info['final_balance'], 'total_received': address_info['total_received'], 'total_sent': address_info['total_sent']}
    db.addresses.update_one({'address': address}, {'$set': update_data})


@app.route('/search', methods=['POST'])
def search_address():
    try:
        data = request.json
        address = data.get('address')

        # Validate address format
        if not address or not is_valid_address(address):
            return jsonify({"error": "Invalid or missing address"}), 400

        existing_address = db.public_addresses.find_one({'address': address})

        # Check if data exists and if it's older than 30 minutes, or if it doesn't exist at all
        if not existing_address or datetime.utcnow() - existing_address.get('last_updated', datetime.utcfromtimestamp(0)) > timedelta(minutes=30):
            try:
                address_data = blockcypher.get_address_overview(address, coin_symbol='bcy')
                record_to_update = {
                    'address': address,
                    'final_balance': address_data['final_balance'],
                    'total_received': address_data['total_received'],
                    'total_sent': address_data['total_sent'],
                    'last_updated': datetime.utcnow()
                }

                # Update the existing record, or insert a new one if it doesn't exist
                db.public_addresses.update_one({'address': address}, {'$set': record_to_update}, upsert=True)
                existing_address = record_to_update
                if '_id' not in existing_address:
                    existing_address['_id'] = str(db.public_addresses.find_one({'address': address})['_id'])
            except Exception as e:
                logger.error(f"Error updating or inserting address data: {str(e)}", exc_info=True)
                return jsonify({"error": "An error occurred. Please try again later."}), 500

        else:
            # Convert ObjectId to string for the existing record
            existing_address['_id'] = str(existing_address['_id'])

        # Generate QR code
        qr_code = pyqrcode.create(address)
        existing_address['qr_code'] = qr_code.png_as_base64_str(scale=5)

        return jsonify(existing_address)

    except ConnectionFailure:
        logger.error("Database connection failed", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 503
    except PyMongoError as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 500

@app.route('/create_wallet', methods=['POST'])
def create_wallet():
    try:
        # Generate new wallet using BlockCypher
        try:
            wallet_info = blockcypher.generate_new_address(coin_symbol='bcy', api_key=API_TOKEN)
        except Exception as e:
            logging.error("BlockCypher API error", exc_info=True)
            return jsonify({"error": "Error generating wallet. Please try again later."}), 500

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
    
    except ConnectionFailure:
        logger.error("Database connection failed", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 503
    except PyMongoError as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred. Please try again later."}), 500

if __name__ == '__main__':
    app.run(debug=True)