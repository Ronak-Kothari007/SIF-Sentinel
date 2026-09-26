import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path("backend").resolve()))
from models.predict_baseline import get_predictor

print("Loading predictor...")
predictor = get_predictor()

# Apply monkey patch
lr = predictor._pipeline.named_steps["lr"]
if not hasattr(lr, "multi_class"):
    print("Monkey patching multi_class...")
    lr.multi_class = "auto"

print("Predicting...")
result = predictor.predict("Worker entered confined space without gas test.")
print("Success:", result)
