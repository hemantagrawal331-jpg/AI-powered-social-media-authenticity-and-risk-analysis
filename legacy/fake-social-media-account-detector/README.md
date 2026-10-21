# Fake Social Media Account Detector

A B.Tech final-year project: predicts whether a social-media profile is
**genuine** or **fake** from its public metadata, using a Random Forest
classifier served through a FastAPI backend, with a simple HTML frontend.

## Structure
```
fake-account-detector/
├── data/
│   ├── generate_dataset.py   # builds a synthetic training dataset
│   └── accounts.csv          # generated dataset (5,000 rows)
├── model/
│   ├── train_model.py        # trains, evaluates, saves the Random Forest
│   ├── rf_model.pkl          # trained model
│   ├── metrics.json          # accuracy, ROC-AUC, confusion matrix
│   └── feature_importance.png
├── backend/
│   └── main.py                # FastAPI app with /predict endpoint
├── frontend/
│   └── index.html              # form UI, calls the backend
└── requirements.txt
```

## How to run

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **(Optional) Regenerate data & retrain**
   ```bash
   python data/generate_dataset.py
   python model/train_model.py
   ```
   This is already done — `rf_model.pkl` is included.

3. **Start the backend**
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

4. **Open the frontend**
   Just open `frontend/index.html` in your browser (double-click it, or
   right-click → Open With → Browser). Fill in the form and click Predict.

## Important note on the dataset

The included dataset is **synthetic** — I generated it with clear, separable
patterns so the pipeline runs end-to-end. That's why the model shows ~100%
accuracy; it's not a real-world result, and a professor will notice inflated
numbers immediately. For a stronger project:

1. Replace `data/accounts.csv` with a real dataset (search Kaggle for
   "fake social media account detection" or "Instagram fake followers").
2. Keep the same column names, or adjust `FEATURES` in `train_model.py`
   and `backend/main.py` to match.
3. Retrain — expect real accuracy somewhere in the 85–95% range, which is
   far more credible and gives you something genuine to analyze in your
   report (which features matter, where the model makes mistakes, etc).

## Ideas to extend (from your notes)

- Add Logistic Regression / SVM / XGBoost and compare metrics
- CSV batch upload + batch classification endpoint
- Prediction history stored in SQLite
- Admin dashboard showing model performance over time
- Rule-based + ML hybrid scoring (weighted combination)
- PDF/CSV export of detection report

## Next steps I can help with
- Swapping in a real Kaggle dataset
- Adding the batch-upload and history features
- Turning the frontend into a React app
- Preparing your viva slides / report explaining the model
# fake-social-media-account-detector
