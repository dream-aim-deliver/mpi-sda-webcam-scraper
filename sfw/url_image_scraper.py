import argparse  # New import for handling command-line arguments
import torch
from torchvision import transforms, models
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
import requests
from PIL import Image
from io import BytesIO
from collections import Counter
import json

# Step 1: Scrape the Image from the URL with error handling
def fetch_image_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert('RGB')  # Ensure image is in RGB format
        return img
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image from URL: {e}")
        return None

# Step 2: Preprocess the image
def preprocess_image(image):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return transform(image)

# Step 3: Dynamically split the image into an odd number of grids
def split_image(image, grid_size):
    try:
        width, height = image.size

        # Ensure grid size is valid and does not exceed image dimensions
        if width < grid_size or height < grid_size:
            raise ValueError("Grid size is too large for the image dimensions.")

        # Calculate grid width and height to ensure an even split
        grid_width = width // grid_size
        grid_height = height // grid_size

        grids = []
        for i in range(grid_size):
            for j in range(grid_size):
                left = i * grid_width
                upper = j * grid_height
                right = left + grid_width
                lower = upper + grid_height

                # Avoid index out-of-bounds in case of uneven dimensions
                if right > width or lower > height:
                    right, lower = width, height
                
                grid = image.crop((left, upper, right, lower))
                grids.append(grid)

        return grids
    except Exception as e:
        print(f"Error splitting image: {e}")
        return []

# Step 4: Classify each grid and count the results
def classify_weather(image_tensor, model):
    try:
        with torch.no_grad():
            outputs = model(image_tensor.unsqueeze(0))
            _, preds = outputs.max(1)
        return preds.item()
    except Exception as e:
        print(f"Error during weather classification: {e}")
        return None

def map_to_weather_class(imagenet_class, last_weather=None):
    weather_mapping = {
        "cloud": "cloudy",
        "overcast": "cloudy",
        "umbrella": "rainy",
        "rain": "rainy",
        "poncho": "rainy",
        "snowplow": "snowy",
        "parachute": "stormy",
        "sun": "sunny",
        "storm": "stormy",
        "thunderstorm": "stormy",
        "alp": "cloudy",
        "geyser": "cloudy",
        "mountain": "cloudy",
        "fountain": "rainy",
        "missile": "stormy",
        "cloudy": "cloudy",  # Explicitly map "cloudy" to "cloudy"
    }
    
    weather_class = weather_mapping.get(imagenet_class, "Unknown Weather")

    if weather_class == "Unknown Weather" and last_weather:
        return last_weather
    else:
        return weather_class

def main_efficientnet(url, num_grids=3):
    model = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
    model.eval()

    imagenet_labels = load_imagenet_labels()  # Load ImageNet class index
    if not imagenet_labels:
        return "Error: Unable to load ImageNet labels."

    image = fetch_image_from_url(url)
    if image is None:
        return "Error: Unable to fetch image."

    grids = split_image(image, num_grids)
    if not grids:
        return "Error: Unable to split image."

    predictions = []
    last_weather = None  # Initialize last valid weather class

    for grid in grids:
        image_tensor = preprocess_image(grid)
        predicted_class = classify_weather_efficientnet(image_tensor, model, imagenet_labels)
        
        # Map to weather class, using last_weather for fallback
        weather_class = map_to_weather_class(predicted_class, last_weather)
        
        # Update last_weather if a valid (non-"Unknown") class is found
        if weather_class != "Unknown Weather":
            last_weather = weather_class
        
        predictions.append(weather_class)

    # Filter out "Unknown Weather" from predictions
    filtered_predictions = [weather for weather in predictions if weather != "Unknown Weather"]

    # If no valid predictions, return the message
    if not filtered_predictions:
        return "Unable to determine weather: only unknown results."

    # Majority voting on valid weather classes
    majority_class = Counter(filtered_predictions).most_common(1)[0][0]

    return majority_class if majority_class != "Unknown Weather" else last_weather

def load_imagenet_labels():
    try:
        with open("imagenet_class_index_correct.json", "r") as f:
            imagenet_classes = json.load(f)
        return {int(key): value for key, value in imagenet_classes.items()}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        return None

def classify_weather_efficientnet(image_tensor, model, imagenet_labels):
    with torch.no_grad():
        outputs = model(image_tensor.unsqueeze(0))
        _, preds = outputs.max(1)
        
    predicted_class = imagenet_labels[preds.item()]

    # Map the predicted class to a weather condition
    weather_class = map_to_weather_class(predicted_class)
    
    return weather_class


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify the weather based on a webcam image URL.")
    parser.add_argument("--url", type=str, required=True, help="URL of the image to classify")
    args = parser.parse_args()
    weather = main_efficientnet(args.url)
    print(f"The weather is: {weather}")
