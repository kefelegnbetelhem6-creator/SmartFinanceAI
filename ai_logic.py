import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def get_ai_advice(transactions_summary):
    # መጀመሪያ ግንኙነቱ መስራቱን ለማረጋገጥ ይህንን ይመልስልን
    return "ሰላም! አዲሱ ኮድ አሁን መስራት ጀምሯል። ጥቂት ሰከንድ ይጠብቁ..."

def suggest_category(description):
    return "Other"