"""
ECOSORT AI - MODEL TRAINING
Run with: python train_model.py
"""

import torch
import torch.nn as nn
from torch.optim import Adam
from torchvision import transforms, models
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
import os
from tqdm import tqdm
import matplotlib.pyplot as plt
import json

print("""
╔════════════════════════════════════════════════════════════════════╗
║                 ECOSORT AI - MODEL TRAINING                       ║
║            Training ResNet50 on waste classification               ║
╚════════════════════════════════════════════════════════════════════╝
""")

# Configuration
BATCH_SIZE = 16
LEARNING_RATE = 0.001
EPOCHS = 15
IMAGE_SIZE = 224
DATA_PATH = "data/raw"
MODEL_PATH = "models/waste_classifier.pth"

# Device
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}\n")

# Load data
print(f"Loading data from {DATA_PATH}...")
transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(15),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

dataset = ImageFolder(DATA_PATH, transform=transform)
print(f"✅ Loaded {len(dataset)} images")
print(f"✅ Classes: {dataset.classes}\n")

# Split data
train_size = int(0.8 * len(dataset))
test_size = len(dataset) - train_size
train_dataset, test_dataset = torch.utils.data.random_split(dataset, [train_size, test_size])

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

print(f"Training set: {len(train_dataset)}")
print(f"Test set: {len(test_dataset)}\n")

# Create model
print("Building model...")
model = models.resnet50(pretrained=True)

# Freeze early layers
for param in list(model.parameters())[:-10]:
    param.requires_grad = False

# Replace final layer
num_features = model.fc.in_features
model.fc = nn.Sequential(
    nn.Linear(num_features, 512),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(512, 256),
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(256, len(dataset.classes))
)

model = model.to(device)
print(f"✅ Model ready\n")

# Training
criterion = nn.CrossEntropyLoss()
optimizer = Adam([p for p in model.parameters() if p.requires_grad], lr=LEARNING_RATE)

history = {"train_loss": [], "train_acc": [], "test_loss": [], "test_acc": []}
best_acc = 0

print("=" * 70)
print("🔥 TRAINING STARTED")
print("=" * 70 + "\n")

for epoch in range(EPOCHS):
    print(f"Epoch {epoch + 1}/{EPOCHS}")
    
    # Train
    model.train()
    train_loss = 0
    train_correct = 0
    train_total = 0
    
    for images, labels in tqdm(train_loader, desc="Training", leave=False):
        images, labels = images.to(device), labels.to(device)
        outputs = model(images)
        loss = criterion(outputs, labels)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        train_loss += loss.item()
        _, predicted = torch.max(outputs.data, 1)
        train_total += labels.size(0)
        train_correct += (predicted == labels).sum().item()
    
    avg_train_loss = train_loss / len(train_loader)
    avg_train_acc = 100 * train_correct / train_total
    
    # Test
    model.eval()
    test_loss = 0
    test_correct = 0
    test_total = 0
    
    with torch.no_grad():
        for images, labels in tqdm(test_loader, desc="Testing", leave=False):
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            test_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            test_total += labels.size(0)
            test_correct += (predicted == labels).sum().item()
    
    avg_test_loss = test_loss / len(test_loader)
    avg_test_acc = 100 * test_correct / test_total
    
    history["train_loss"].append(avg_train_loss)
    history["train_acc"].append(avg_train_acc)
    history["test_loss"].append(avg_test_loss)
    history["test_acc"].append(avg_test_acc)
    
    print(f"  Train Loss: {avg_train_loss:.4f} | Acc: {avg_train_acc:.2f}%")
    print(f"  Test Loss:  {avg_test_loss:.4f} | Acc: {avg_test_acc:.2f}%")
    
    if avg_test_acc > best_acc:
        best_acc = avg_test_acc
        os.makedirs("models", exist_ok=True)
        torch.save(model.state_dict(), MODEL_PATH)
        print(f"  ✅ Saved! (Best: {best_acc:.2f}%)")
    
    print()

# Save results
with open("models/history.json", "w") as f:
    json.dump(history, f)

# Plot
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].plot(history['train_loss'], label='Train'), axes[0].plot(history['test_loss'], label='Test')
axes[0].set_title('Loss'), axes[0].legend(), axes[0].grid(True, alpha=0.3)
axes[1].plot(history['train_acc'], label='Train'), axes[1].plot(history['test_acc'], label='Test')
axes[1].set_title('Accuracy'), axes[1].legend(), axes[1].grid(True, alpha=0.3)
plt.savefig('models/training_curves.png', dpi=100, bbox_inches='tight')

print("=" * 70)
print(f"✅ TRAINING COMPLETE! Best Accuracy: {best_acc:.2f}%")
print("=" * 70)
print(f"Model saved to: {MODEL_PATH}")
print(f"Graph saved to: models/training_curves.png")
print("\nNext: Create web app with Streamlit!")