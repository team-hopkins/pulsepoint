"""Check MongoDB consultations collection"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime


async def check_consultations():
    """Check recent consultations in MongoDB"""
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "carepoint_medical")
    
    client = AsyncIOMotorClient(mongodb_uri)
    database = client[db_name]
    consultations = database["consultations"]
    
    # Count total consultations
    total = await consultations.count_documents({})
    print(f"📊 Total consultations: {total}")
    
    # Get recent consultations
    print(f"\n📋 Recent consultations (last 5):")
    cursor = consultations.find().sort("timestamp", -1).limit(5)
    
    async for doc in cursor:
        timestamp = doc.get("timestamp", "N/A")
        patient = doc.get("patient_id", "N/A")
        route = doc.get("route", "N/A")
        urgency = doc.get("output", {}).get("urgency", "N/A")
        trace_id = doc.get("trace_id", "NO TRACE ID")
        
        print(f"\n   🏥 {patient} @ {timestamp}")
        print(f"      Route: {route} | Urgency: {urgency}")
        if trace_id:
            trace_display = f"{trace_id[:20]}..." if len(trace_id) > 20 else trace_id
            print(f"      Trace ID: {trace_display}")
        else:
            print(f"      Trace ID: ⚠️  NULL (old record)")
    
    # Check for null trace_ids
    null_count = await consultations.count_documents({"trace_id": None})
    print(f"\n⚠️  Consultations with null trace_id: {null_count}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(check_consultations())
