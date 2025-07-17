from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, time
import logging

# 🔁 Import your fraud prediction logic
from real_time.predict_pipeline import predict_fraud

# ✅ Logging setup
logging.basicConfig(level=logging.INFO)

# ✅ Define Pydantic input model
class Input(BaseModel):
    Sender_account: str = Field(..., example="2365007895")
    Receiver_account: str = Field(..., example="ACC5678")
    Sender_bank_location: str = Field(..., example="Mumbai")
    Receiver_bank_location: str = Field(..., example="Delhi")
    Payment_type: str = Field(..., example="Wire Transfer")
    # Laundering_type: str = Field(..., example="Smurfing")
    Payment_currency: str = Field(..., example="INR")
    Received_currency: str = Field(..., example="INR")
    Amount: float = Field(..., example=45000)
    Date: date = Field(..., example="2025-07-13")
    Time: time = Field(..., example="12:30:45")

# ✅ Initialize FastAPI app
app = FastAPI(
    title="Fraud Detection API",
    description="Detects fraudulent transactions using multi-agent system",
    version="1.0.0"
)

# ✅ Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Health check route
@app.get("/health")
async def health_check():
    return {"status": "🟢 API running"}

# ✅ Fraud prediction route
@app.post("/predict")
async def predict(input_data: Input):
    input_dict = input_data.model_dump()

    # Optional: Convert date/time back to strings if downstream needs
    input_dict["Date"] = input_data.Date.strftime("%Y-%m-%d")
    input_dict["Time"] = input_data.Time.strftime("%H:%M:%S")

    try:
        output = predict_fraud(input_dict)
    except Exception as e:
        logging.exception("❌ Prediction error:")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Prediction failed",
                "details": str(e)
            }
        )

    return JSONResponse(content=output, status_code=200)
