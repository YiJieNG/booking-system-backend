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

# @app.route('/api/bkgSession', methods=['POST'])
# def insert_bkgsession():
#     # Retrieve data from the request
#     data = request.get_json()

#     # Check if required fields are provided
#     bkg_date = data.get('bkg_date')
#     bkg_time = data.get('bkg_time')
#     slot_limit = data.get('slot_limit', 5)  # Default to 0 if not provided

#     # Validate inputs
#     if not bkg_date or not bkg_time:
#         return jsonify({"error": "bkg_date and bkg_time are required"}), 400

#     try:
#         # Connect to the database
#         db = get_db_connection()
#         cur = db.cursor()

#         # Insert the new session into the table
#         query = '''INSERT INTO bkgsession (bkg_date, bkg_time, slot_limit)
#                    VALUES (%s, %s, %s)
#                 '''
#         cur.execute(query, (bkg_date, bkg_time, slot_limit))

#         # Commit the transaction
#         db.commit()
#         cur.close()
#         db.close()

#         # Return success response
#         return jsonify({"message": "Session successfully inserted"}), 201

#     except Exception as e:
#         # Handle any errors that occur during the insertion
#         db.rollback()
#         return jsonify({"error": str(e)}), 500

@app.route('/api/bkgSession', methods=['POST'])
def insert_bkgsession():
    # Retrieve data from the request
    data = request.get_json()
    
    # Check if required fields are provided
    month = data.get('month')
    year = data.get('year')
    slot_limit = data.get('slot_limit', 5)  # Default to 5 if not provided
    
    # Validate inputs
    if not month or not year:
        return jsonify({"error": "month and year are required"}), 400
        
    try:
        # Connect to the database
        db = get_db_connection()
        cur = db.cursor()
        
        # Define the available booking times
        booking_times = ['09:00:00', '10:00:00', '11:00:00', '12:00:00', 
                        '13:00:00', '14:00:00', '15:00:00', '16:00:00', '17:00:00']
        
        # Create a temporary table for storing dates
        cur.execute("""
            CREATE TEMPORARY TABLE temp_dates (date_value DATE);
        """)
        
        # Insert dates for the entire month into temporary table
        cur.execute("""
            INSERT INTO temp_dates (date_value)
            WITH RECURSIVE date_series AS (
                SELECT DATE(CONCAT(%s,'-',%s,'-01')) AS date_value
                UNION ALL
                SELECT date_value + INTERVAL 1 DAY
                FROM date_series
                WHERE date_value < LAST_DAY(DATE(CONCAT(%s,'-',%s,'-01')))
            )
            SELECT date_value FROM date_series;
        """, (year, month, year, month))
        
        # Create a temporary table for times
        cur.execute("""
            CREATE TEMPORARY TABLE temp_times (time_value TIME);
        """)
        
        # Insert the booking times
        for time_value in booking_times:
            cur.execute("""
                INSERT INTO temp_times (time_value) VALUES (%s);
            """, (time_value,))
        
        # Insert booking sessions for each date and time combination
        cur.execute("""
            INSERT IGNORE INTO bkgsession (bkg_date, bkg_time, slot_limit)
            SELECT d.date_value, t.time_value, %s
            FROM temp_dates d
            CROSS JOIN temp_times t;
        """, (slot_limit,))
        
        # Get the number of inserted rows
        cur.execute("SELECT COUNT(*) FROM temp_dates")
        num_days = cur.fetchone()[0]
        rows_inserted = num_days * len(booking_times)
        
        # Clean up temporary tables
        cur.execute("DROP TEMPORARY TABLE IF EXISTS temp_dates")
        cur.execute("DROP TEMPORARY TABLE IF EXISTS temp_times")
        
        # Commit the transaction
        db.commit()
        cur.close()
        db.close()
        
        # Return success response
        return jsonify({
            "message": "Sessions successfully inserted",
            "days_processed": num_days,
            "total_sessions_created": rows_inserted
        }), 201
        
    except Exception as e:
        # Handle any errors that occur during the insertion
        if 'db' in locals():
            db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/getBkgSession', methods=['GET'])
def get_bkg_session():
    # Retrieve data from the request
    data = request.get_json()
    
    # Check if required fields are provided
    month = data.get('month')
    year = data.get('year')
    
    # Validate inputs
    if not month or not year:
        return jsonify({"error": "month and year are required"}), 400

    try:
        # Connect to the database
        db = get_db_connection()
        cur = db.cursor()

        # Insert booking details into the database
        query = '''select * from bkgsession WHERE SUBSTRING(bkg_date, 6, 2) = %s AND SUBSTRING(bkg_date, 1, 4) = %s 
                '''
        cur.execute(query, (month, year,))

        data = cur.fetchall()
        cur.close()
        db.close()
        print(data)

        # Process the result to convert datetime objects to strings
        booking_data = []
        for row in data:
            bkg_date, bkg_time, slot_limit = row
            # Convert datetime to string if necessary
            if isinstance(bkg_date, datetime.date):
                bkg_date = bkg_date.isoformat()  # Convert date to ISO format string
            if isinstance(bkg_time, datetime.timedelta):
                bkg_time = str(bkg_time)  # Convert timedelta to string (e.g., '18:30:00')
            
            booking_data.append({
                "bkg_date": bkg_date,
                "bkg_time": bkg_time,
                "slot_limit": slot_limit,
            })

        # Return success response with formatted data
        return jsonify(booking_data), 200

    except Exception as e:
        # Handle any errors that occur during the insertion
        db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/bookingSummary', methods=['GET'])
def get_booking_summary():
    # Retrieve data from the request
    data = request.get_json()
    
    # Check if required fields are provided
    month = data.get('month')
    year = data.get('year')
    
    # Validate inputs
    if not month or not year:
        return jsonify({"error": "month and year are required"}), 400
        
    try:
        # Connect to the database
        db = get_db_connection()
        cur = db.cursor()

        # Query to get available slots by combining bkgsession and booking
        query = """
            SELECT 
                DATE_FORMAT(bs.bkg_date, '%%d-%%m-%%Y') as formatted_date,
                DATE_FORMAT(bs.bkg_time, '%%H:%%i') as formatted_time,
                bs.slot_limit - COUNT(b.bkg_date) as available_slots
            FROM 
                bkgsession bs
                LEFT JOIN booking b 
                    ON bs.bkg_date = b.bkg_date 
                    AND bs.bkg_time = b.bkg_time
            WHERE 
                MONTH(bs.bkg_date) = %s 
                AND YEAR(bs.bkg_date) = %s
            GROUP BY 
                bs.bkg_date,
                bs.bkg_time,
                bs.slot_limit
            ORDER BY 
                bs.bkg_date,
                bs.bkg_time;
        """

        cur.execute(query, (month, year))
        results = cur.fetchall()

        # Initialize response dictionary
        response = {}
        
        # Process results - Note that results will be tuples, not dictionaries
        for row in results:
            date = row[0]
            time = row[1]
            available = row[2]
            
            # Initialize date entry if it doesn't exist
            if date not in response:
                response[date] = {}
                
            # Add available slots
            response[date][time] = available
        
        cur.close()
        db.close()
        
        return jsonify(response), 200
        
    except Exception as e:
        # Handle any errors
        if 'db' in locals():
            db.rollback()
        return jsonify({"error": str(e)}), 500
    

############# USER WISE ##################
@app.route('/api/makeBooking', methods=['POST'])
def make_booking():
    # Retrieve data from the request
    data = request.get_json()

    # Check if required fields are provided
    bkg_date = data.get('bkg_date')
    bkg_time = data.get('bkg_time')
    phone = data.get('phone')
    email = data.get('email')
    family_name = data.get('family_name')
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
        query = '''INSERT INTO booking (phone, email, bkg_date, bkg_time, family_name, table_num, ref_num)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                '''
        cur.execute(query, (phone, email, bkg_date, bkg_time, family_name, table_num, ref_number))

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
    ref_num = data.get('ref_num')

    # Validate inputs
    if not ref_num:
        return jsonify({"error": "ref_num are required"}), 400

    try:
        # Connect to the database
        db = get_db_connection()
        cur = db.cursor()

        # Insert booking details into the database
        query = '''select phone, email, bkg_date, bkg_time, family_name, table_num from booking WHERE ref_num = %s
                '''
        cur.execute(query, (ref_num,))

        data = cur.fetchall()
        cur.close()
        db.close()
        print(data)

        # Process the result to convert datetime objects to strings
        booking_data = []
        for row in data:
            phone, email, bkg_date, bkg_time, family_name, table_num = row
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
                "family_name": family_name,
                "table_num": table_num
            })

        # Return success response with formatted data
        return jsonify(booking_data), 200

    except Exception as e:
        # Handle any errors that occur during the insertion
        db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/updateBooking', methods=['PUT'])
def update_booking():
    # Retrieve data from the request
    data = request.get_json()

    # Check if required fields are provided
    bkg_date = data.get('bkg_date')
    bkg_time = data.get('bkg_time')
    phone = data.get('phone')
    email = data.get('email')
    family_name = data.get('family_name')
    table_num = data.get('table', 0)  # Default to 0 if not provided
    ref_num = data.get('ref_num')

    # Validate inputs
    if not ref_num:
        return jsonify({"error": "ref_number are required"}), 400
    
    if not bkg_date and not bkg_time and not phone and not email and not table_num:
        return jsonify({"error": "at least one parameter to update is required"}), 400

    try:
        # Connect to the database
        db = get_db_connection()
        cur = db.cursor()

        # query = '''INSERT INTO booking (phone, email, bkg_date, bkg_time, table_num, ref_num)
        #         VALUES (%s, %s, %s, %s, %s, %s)
        #         '''
        query = "UPDATE booking SET "
        params = []

        if email:
            query += "email = %s, "
            params.append(email)
        if phone:
            query += "phone = %s, "
            params.append(phone)
        if table_num:
            query += "table_num = %s, "
            params.append(table_num)
        if bkg_date:
            query += "bkg_date = %s, "
            params.append(bkg_date)
        if bkg_time:
            query += "bkg_time = %s, "
            params.append(bkg_time)
        if family_name:
            query += "family_name = %s, "
            params.append(family_name)

        query = query.rstrip(', ') # Remove the last comma and space
        query += " WHERE ref_num = %s"
        params.append(ref_num)
        print(query)
        print(params)
            
        # Execute the update query
        cur.execute(query, tuple(params))

        # Commit the transaction
        db.commit()

        # Return success response
        return jsonify({"message": "Booking successfully updated"}), 201

    except Exception as e:
        # Handle any errors that occur during the insertion
        db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/cancelBooking', methods=['DELETE'])
def cancel_booking():
    # Retrieve data from the request
    data = request.get_json()

    # Check if required fields are provided
    ref_num = data.get('ref_num')

    # Validate inputs
    if not ref_num:
        return jsonify({"error": "ref_num is required"}), 400

    try:
        # Connect to the database
        db = get_db_connection()
        cur = db.cursor()
        # Check if the booking exists
        query = '''SELECT * FROM booking WHERE ref_num = %s'''
        cur.execute(query, (ref_num,))
        booking = cur.fetchone()

        if not booking:
            # If no booking found with the provided reference number
            return jsonify({"error": "Booking not found"}), 404

        # If the booking exists, proceed to delete it
        delete_query = '''DELETE FROM booking WHERE ref_num = %s'''
        cur.execute(delete_query, (ref_num,))

        # Commit the changes
        db.commit()
        cur.close()
        db.close()

        # Return a success message
        return jsonify({"message": f"Booking with reference number {ref_num} has been deleted."}), 200
    except Exception as e:
        # Handle any errors that occur during the insertion
        db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/getSlotLimit', methods=['GET'])
def get_slot_limit():
    # Retrieve data from the request
    data = request.get_json()

    # Check if required fields are provided
    bkg_date = data.get('bkg_date')
    bkg_time = data.get('bkg_time')

    # Validate inputs
    if not bkg_date or not bkg_time:
        return jsonify({"error": "bkg_date and bkg_time are required"}), 400

    try:
        # Connect to the database
        db = get_db_connection()
        cur = db.cursor()

        # Insert booking details into the database
        query = '''select slot_limit from bkgsession WHERE bkg_date = %s AND bkg_time = %s 
                '''
        cur.execute(query, (bkg_date, bkg_time,))

        data = cur.fetchall()
        cur.close()
        db.close()
        print(data)

        # Process the result to convert datetime objects to strings
        response = []
        for row in data:
            slot_limit = row
            response.append({
                "slot_limit": slot_limit,
            })

        # Return success response with formatted data
        return jsonify(response), 200

    except Exception as e:
        # Handle any errors that occur during the insertion
        db.rollback()
        return jsonify({"error": str(e)}), 500


def generate_ref_number(length=6):
    # Create a set of characters (uppercase, lowercase, and digits)
    characters = string.ascii_letters + string.digits
    ref_number = ''.join(secrets.choice(characters) for i in range(length))
    return ref_number

if __name__ == '__main__':
    app.run(debug=True)
