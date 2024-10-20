import requests
import json

def predict_letter(json_data, url="http://20.5.25.179:8080/predict"):
    """
    Function to send JSON data to the prediction server and get the response.

    Args:
    json_data (dict): JSON data to send for prediction.
    url (str): URL of the prediction server's endpoint.

    Returns:
    tuple: (str, bool) The predicted letter and a success flag (True/False).
    """
    try:
        # Send a POST request to the server
        response = requests.post(url, json=json_data)

        # Check if the request was successful
        if response.status_code == 200:
            # Extract prediction and confidence from the response
            result = response.json()
            prediction = result.get("prediction", "Uncertain")
            if prediction.lower() == "uncertain":
                # print("Prediction is uncertain")
                return prediction, False
            return prediction, True
        else:
            # If the status code is not 200, return a failure indication
            print(f"Error: Received unexpected status code {response.status_code}")
            return "Uncertain", False

    except requests.exceptions.RequestException as e:
        # Handle exceptions such as connection errors
        print(f"Connection Error: {e}")
        return "Uncertain", False

# Example usage
if __name__ == "__main__":
    # Replace this with your actual JSON data
    with open("saved_data/hand_1728406692841.json", "r") as file:
        test_data = json.load(file)
    
    # Calling the function with JSON data directly
    predicted_letter, success = predict_letter(test_data)
    print(f"Predicted Letter: {predicted_letter}, Success: {success}")
