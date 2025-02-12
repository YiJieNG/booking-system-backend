from flask import Flask, jsonify, request
from flask_cors import CORS 
import MySQLdb
import os
import secrets
import string
import datetime
from dotenv import load_dotenv

load_dotenv()


app = Flask(__name__)
CORS(app)

# Configuration for MySQL connection
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DB = os.getenv('MYSQL_DB')
MYSQL_PORT = int(os.getenv('MYSQL_PORT'))

# Function to get a database connection
def get_db_connection():
    try:
        return MySQLdb.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            passwd=MYSQL_PASSWORD,
            db=MYSQL_DB,
            port=MYSQL_PORT
        )
    except Exception as error:
        # handle the exception
        print("An exception occurred:", error)

# Testing connection on start-up
connection = get_db_connection()
if connection is None:
    print("Connection failed")
else:
    print("Connection successful")
    connection.close()

@app.route('/api/bkgSession', methods=['POST'])
def insert_bkgsession():
    # Retrieve data from the request
    data = request.get_json()

    # Check if required fields are provided
    bkg_date = data.get('bkg_date')
    bkg_time = data.get('bkg_time')
    slot_limit = data.get('slot_limit', 0)  # Default to 0 if not provided

    # Validate inputs
    if not bkg_date or not bkg_time:
        return jsonify({"error": "bkg_date and bkg_time are required"}), 400

    try:
        # Connect to the database
        db = get_db_connection()
        cur = db.cursor()

        # Insert the new session into the table
        query = '''INSERT INTO bkgsession (bkg_date, bkg_time, slot_limit)
                   VALUES (%s, %s, %s)
                '''
        cur.execute(query, (bkg_date, bkg_time, slot_limit))

        # Commit the transaction
        db.commit()
        cur.close()
        db.close()

        # Return success response
        return jsonify({"message": "Session successfully inserted"}), 201

    except Exception as e:
        # Handle any errors that occur during the insertion
        db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/makeBooking', methods=['POST'])
def make_booking():
    # Retrieve data from the request
    data = request.get_json()

    # Check if required fields are provided
    bkg_date = data.get('bkg_date')
    bkg_time = data.get('bkg_time')
    phone = data.get('phone')
    email = data.get('email')
    table_num = data.get('table', 0)  # Default to 0 if not provided

    # Validate inputs
    if not bkg_date or not bkg_time:
        return jsonify({"error": "bkg_date and bkg_time are required"}), 400

    if not phone or not email:
        return jsonify({"error": "phone and email are required"}), 400
    
    ref_number = generate_ref_number()

    try:
        # Connect to the database
        db = get_db_connection()
        cur = db.cursor()

        # Insert booking details into the database
        query = '''INSERT INTO booking (phone, email, bkg_date, bkg_time, table_num, ref_num)
                VALUES (%s, %s, %s, %s, %s, %s)
                '''
        cur.execute(query, (phone, email, bkg_date, bkg_time, table_num, ref_number))

        # Commit the transaction
        db.commit()
        cur.close()
        db.close()

        # Return success response
        return jsonify({"message": "Session successfully inserted"}), 201

    except Exception as e:
        # Handle any errors that occur during the insertion
        db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/getBooking', methods=['GET'])
def get_booking():
    # Retrieve data from the request
    data = request.get_json()

    # Check if required fields are provided
    ref_number = data.get('ref_number')

    # Validate inputs
    if not ref_number:
        return jsonify({"error": "ref_number are required"}), 400

    try:
        # Connect to the database
        db = get_db_connection()
        cur = db.cursor()

        # Insert booking details into the database
        query = '''select phone, email, bkg_date, bkg_time, table_num from booking WHERE ref_num = %s
                '''
        cur.execute(query, (ref_number,))

        data = cur.fetchall()
        cur.close()
        db.close()
        print(data)

        # Process the result to convert datetime objects to strings
        booking_data = []
        for row in data:
            phone, email, bkg_date, bkg_time, table_num = row
            # Convert datetime to string if necessary
            if isinstance(bkg_date, datetime.date):
                bkg_date = bkg_date.isoformat()  # Convert date to ISO format string
            if isinstance(bkg_time, datetime.timedelta):
                bkg_time = str(bkg_time)  # Convert timedelta to string (e.g., '18:30:00')
            
            booking_data.append({
                "phone": phone,
                "email": email,
                "bkg_date": bkg_date,
                "bkg_time": bkg_time,
                "table_num": table_num
            })

        # Return success response with formatted data
        return jsonify(booking_data), 200

    except Exception as e:
        # Handle any errors that occur during the insertion
        db.rollback()
        return jsonify({"error": str(e)}), 500




def generate_ref_number(length=12):
    # Create a set of characters (uppercase, lowercase, and digits)
    characters = string.ascii_letters + string.digits
    ref_number = ''.join(secrets.choice(characters) for i in range(length))
    return ref_number

if __name__ == '__main__':
    app.run(debug=True)
