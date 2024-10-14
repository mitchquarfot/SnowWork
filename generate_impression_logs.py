import os
import requests
from datetime import datetime

# Define your Mockaroo API key and schema name
api_key = '647272f0'  # Replace with your actual Mockaroo API key
schema_name = 'impression_logs'  # Replace with your actual schema name

# Directory to save the files (update this to your local directory path)
save_directory = '/Users/mquarfot/Desktop/mockaroo_test'  # Example: 'C:/Users/YourName/MockarooData/'

# Function to generate CSV and save it to the specified local directory
def generate_csv():
    # Construct the URL to call the existing schema (with .csv extension)
    url = f'https://api.mockaroo.com/api/generate.csv?key={api_key}&schema={schema_name}'

    # Specify the number of records you want to generate
    params = {
        'count': 10  # Adjust this number to the amount of data records you need
    }

    # Send the GET request to generate data from your saved schema
    response = requests.get(url, params=params)

    # Check if the request was successful and write the CSV data to a file
    if response.status_code == 200:
        # Create the directory if it doesn't exist
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        # Create a filename with the current timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f'mockaroo_data_{timestamp}.csv'
        file_path = os.path.join(save_directory, file_name)

        # Write the content of the response (CSV data) to the file
        with open(file_path, 'wb') as file:
            file.write(response.content)

        print(f'CSV file successfully created: {file_path}')
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}, Message: {response.text}")

# Call the function to generate the CSV and save it locally
generate_csv()
