import numpy as np
import tensorflow as tf
import string
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Load the .h5 model.
model_path = "models/asl_alphabet_neuralnetwork.h5"
model = tf.keras.models.load_model(model_path)

# Define the confidence threshold
CONFIDENCE_THRESHOLD = 0.7  # Set to 70% confidence threshold

# Initialize FastAPI app
app = FastAPI()

# Define Pydantic models for request and response
class Landmark(BaseModel):
    x: float
    y: float
    z: float

class HandData(BaseModel):
    handedness: str
    landmarks: list[Landmark]

class PredictionResponse(BaseModel):
    prediction: str
    confidence: float

# Function to extract landmarks from JSON data and prepare them for model input
def get_landmarks_from_json(json_data):
    # Check if the JSON has the expected structure
    if not json_data or "landmarks" not in json_data[0]:
        print("Invalid data format")
        return None

    # Read handedness (Right/Left) and set up flipping
    is_right = json_data[0]["handedness"] == "Right"
    landmarks = json_data[0]["landmarks"]

    # Create the landmark tensor, flipping the x-coordinates if necessary
    landmark_tensor = []
    for lm in landmarks:
        x = lm["x"] if is_right else 1 - lm["x"]
        y = lm["y"]
        z = lm["z"]
        landmark_tensor.extend([x, y, z])  # Append each coordinate to the list

    # Convert to numpy array of shape (1, 63)
    return np.array(landmark_tensor).reshape(1, -1)

# Function to predict the gesture using the .h5 model
def predict(input_data):
    # Predict and get the probabilities for all classes
    output_data = model.predict(input_data)

    # Get the index and value of the highest probability
    max_confidence = np.max(output_data[0])
    predicted_index = np.argmax(output_data[0])

    # Check if the maximum confidence is above the threshold
    if max_confidence >= CONFIDENCE_THRESHOLD:
        return string.ascii_uppercase[predicted_index], max_confidence
    else:
        return "Uncertain", max_confidence

# Define the prediction endpoint
@app.post("/predict", response_model=PredictionResponse)
async def make_prediction(hand_data_list: list[HandData]):
    # Convert Pydantic models to dictionaries
    json_data = [hand_data.dict() for hand_data in hand_data_list]

    # Extract landmarks from the JSON data
    landmark_tensor = get_landmarks_from_json(json_data)

    # Make a prediction if the landmarks are valid
    if landmark_tensor is not None:
        prediction, confidence = predict(landmark_tensor)
        return PredictionResponse(prediction=prediction, confidence=confidence)
    else:
        raise HTTPException(status_code=400, detail="No valid landmarks found.")

# if __name__ == "__main__":
#     uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
