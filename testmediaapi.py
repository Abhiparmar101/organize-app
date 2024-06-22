import requests
import urllib3

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Define the API URL
api_url = "https://media5.ambicam.com/api/streams"

# Send a GET request to the API with SSL verification disabled
response = requests.get(api_url, verify=False)

# Check if the request was successful
if response.status_code == 200:
    # Get the JSON data from the response
    data = response.json()
    
    # Define the file path
    file_path = "api_data.txt"
    
    # Write the JSON data to a .txt file
    with open(file_path, "w") as file:
        file.write(str(data))
    
    print(f"Data successfully fetched and stored in {file_path}")
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
