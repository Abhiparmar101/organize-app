from flask import Flask, request, jsonify
from flask_cors import CORS
import utils
from langchain_experimental.sql.base import SQLDatabaseChain
from langchain.chains.llm import LLMChain
from langchain_community.utilities.sql_database import SQLDatabase
import json
import os
app = Flask(__name__)
CORS(app)  # This will allow all CORS requests

# Initialize session state
session_state = {
    'history': [],
    'generated': ["Hello! I am here to provide answers to questions fetched from the Database."],
    'past': ["Hello Buddy!"]
}

def beautify_sql_result(sql_result):
    """Beautify the SQL result."""
    return json.dumps(sql_result, indent=4, sort_keys=True)

@app.route('/initialize', methods=['POST'])
def initialize():
    global session_state
    session_state = {
        'history': [],
        'generated': ["Hello! I am here to provide answers to questions fetched from the Database."],
        'past': ["Hello Buddy!"]
    }
    return jsonify({"message": "Session state initialized", "session_state": session_state})

@app.route('/generate_query', methods=['POST'])
def generate_response():
    global session_state
    session_state = {
        'history': [],
        'generated': ["Hello! I am here to provide answers to questions fetched from the Database."],
        'past': ["Hello Buddy!"]
    }
    data = request.json
    user_input = data.get("user_input")
    customer_id= data.get("customer_id")
    if not customer_id:
        return jsonify({"error": "Customer ID is required"}), 400
    # Initialize LLM and database
    db_chain, chain = utils.create_conversational_chain(customer_id)
    
    # Call the chain with user input
    result = db_chain({"query": user_input})
    
    # Get SQL result
    sql_result = result["result"]
    beautified_sql_result = beautify_sql_result(sql_result)
    
    # Update session state
    session_state['past'].append(user_input)
    session_state['generated'].append(sql_result)
    
    response = {
        "user_input": user_input,
        "beautified_sql_result": beautified_sql_result[3:-4],
    }
    return jsonify(response), 200, {'Content-Type': 'application/json; charset=utf-8'}

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(session_state)

if __name__ == "__main__":
    cert_path = "/home/torqueai/gituhub/organize-app/ambicam.crt"
    key_path = "/home/torqueai/gituhub/organize-app/ambicam.key"

    # # Use the SSL certificate and private key in the app.run method
    app.run(debug=True, host="0.0.0.0", port=5000, ssl_context=(cert_path, key_path))
    # app.run(host='0.0.0.0',port=5000,debug=True)
