import json

# Read the text file
with open("imagenet_class_index.json", "r") as f:
    lines = f.readlines()

# Create a dictionary with indices as keys and class names as values
imagenet_classes = {i: line.strip() for i, line in enumerate(lines)}

# Save it to a new JSON file
with open("imagenet_class_index_correct.json", "w") as f:
    json.dump(imagenet_classes, f)

print("JSON file created successfully.")