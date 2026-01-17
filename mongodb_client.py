"""MongoDB client for storing consultations, feedback, and medical knowledge base"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os

# Global MongoDB client
_mongo_client: Optional[AsyncIOMotorClient] = None
_database = None


async def connect_mongodb():
    """Initialize MongoDB connection"""
    global _mongo_client, _database

    # Get MongoDB URI from environment or use local default
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "carepoint_medical")

    try:
        _mongo_client = AsyncIOMotorClient(mongodb_uri)
        _database = _mongo_client[db_name]

        # Test connection
        await _mongo_client.admin.command('ping')

        print(f"✅ Connected to MongoDB: {db_name}")

        # Create indexes
        await _create_indexes()

        return _database
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {str(e)}")
        raise


async def close_mongodb():
    """Close MongoDB connection"""
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        print("🔌 Disconnected from MongoDB")


async def _create_indexes():
    """Create necessary indexes for collections"""
    global _database

    try:
        # Consultations collection indexes
        consultations = _database["consultations"]
        # Sparse index: only enforces uniqueness for documents that have trace_id
        await consultations.create_index("trace_id", unique=True, sparse=True)
        await consultations.create_index("patient_id")
        await consultations.create_index("timestamp")
        await consultations.create_index([("patient_id", 1), ("timestamp", -1)])

        # Feedback collection indexes
        feedback = _database["feedback"]
        await feedback.create_index("trace_id")
        await feedback.create_index("patient_id")
        await feedback.create_index("timestamp")

        # Medical knowledge base indexes (for future vector search)
        knowledge = _database["medical_knowledge"]
        await knowledge.create_index("specialty")
        await knowledge.create_index("urgency_indicators")

        print("📊 MongoDB indexes created successfully")
    except Exception as e:
        print(f"⚠️  Failed to create indexes: {str(e)}")


async def store_consultation(consultation_data: dict) -> str:
    """
    Store consultation record in MongoDB

    Args:
        consultation_data: Dict containing consultation details

    Returns:
        MongoDB document ID
    """
    global _database

    try:
        consultations = _database["consultations"]

        # Add timestamp if not present
        if "timestamp" not in consultation_data:
            consultation_data["timestamp"] = datetime.utcnow()

        result = await consultations.insert_one(consultation_data)

        print(f"💾 Stored consultation: {consultation_data.get('trace_id', 'unknown')}")

        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Failed to store consultation: {str(e)}")
        raise


async def get_patient_history(patient_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve consultation history for a patient

    Args:
        patient_id: Patient identifier
        limit: Maximum number of records to return

    Returns:
        List of consultation records
    """
    global _database

    try:
        consultations = _database["consultations"]

        cursor = consultations.find(
            {"patient_id": patient_id}
        ).sort("timestamp", -1).limit(limit)

        history = await cursor.to_list(length=limit)

        # Convert ObjectId to string for JSON serialization
        for record in history:
            record["_id"] = str(record["_id"])

        print(f"📋 Retrieved {len(history)} consultations for patient {patient_id}")

        return history
    except Exception as e:
        print(f"❌ Failed to retrieve patient history: {str(e)}")
        return []


async def store_feedback(trace_id: str, feedback_data: dict) -> str:
    """
    Store user feedback for a consultation

    Args:
        trace_id: Trace ID of the consultation
        feedback_data: Feedback details (rating, text, etc.)

    Returns:
        MongoDB document ID
    """
    global _database

    try:
        feedback = _database["feedback"]

        # Add timestamp and trace_id
        feedback_record = {
            "trace_id": trace_id,
            "timestamp": datetime.utcnow(),
            **feedback_data
        }

        result = await feedback.insert_one(feedback_record)

        print(f"👍 Stored feedback for trace {trace_id}")

        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Failed to store feedback: {str(e)}")
        raise


async def update_consultation_feedback(trace_id: str, rating: int):
    """
    Update consultation record with feedback rating

    Args:
        trace_id: Trace ID of the consultation
        rating: Feedback rating
    """
    global _database

    try:
        consultations = _database["consultations"]

        result = await consultations.update_one(
            {"trace_id": trace_id},
            {
                "$set": {
                    "feedback_rating": rating,
                    "feedback_timestamp": datetime.utcnow()
                }
            }
        )

        if result.modified_count > 0:
            print(f"✅ Updated consultation {trace_id} with feedback rating: {rating}")
        else:
            print(f"⚠️  No consultation found with trace_id: {trace_id}")

    except Exception as e:
        print(f"❌ Failed to update consultation feedback: {str(e)}")


async def get_urgency_distribution(hours: int = 24) -> Dict[str, int]:
    """
    Get distribution of urgency levels over last N hours

    Args:
        hours: Number of hours to look back

    Returns:
        Dict mapping urgency levels to counts
    """
    global _database

    try:
        consultations = _database["consultations"]

        # Calculate cutoff time
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Aggregation pipeline
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$output.urgency",
                "count": {"$sum": 1}
            }}
        ]

        cursor = consultations.aggregate(pipeline)
        results = await cursor.to_list(length=100)

        # Convert to dict
        distribution = {item["_id"]: item["count"] for item in results}

        print(f"📊 Urgency distribution (last {hours}h): {distribution}")

        return distribution
    except Exception as e:
        print(f"❌ Failed to get urgency distribution: {str(e)}")
        return {}


async def get_model_consensus_stats(days: int = 7) -> Dict[str, Any]:
    """
    Calculate consensus statistics between models

    Args:
        days: Number of days to analyze

    Returns:
        Dict with consensus metrics
    """
    global _database

    try:
        consultations = _database["consultations"]

        # Calculate cutoff time
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get all council consultations
        cursor = consultations.find({
            "timestamp": {"$gte": cutoff},
            "route": "council"
        })

        records = await cursor.to_list(length=1000)

        if not records:
            return {"message": "No council consultations found"}

        # Calculate consensus metrics
        total_consultations = len(records)
        high_consensus = 0  # All 3 models agree on urgency

        for record in records:
            votes = record.get("council_votes", {})
            urgencies = [v.get("urgency") for v in votes.values() if v.get("urgency")]

            if len(urgencies) >= 3 and len(set(urgencies)) == 1:
                high_consensus += 1

        consensus_rate = high_consensus / total_consultations if total_consultations > 0 else 0

        stats = {
            "total_consultations": total_consultations,
            "high_consensus_count": high_consensus,
            "consensus_rate": round(consensus_rate, 3),
            "period_days": days
        }

        print(f"📈 Model consensus stats: {stats}")

        return stats
    except Exception as e:
        print(f"❌ Failed to get model consensus stats: {str(e)}")
        return {}


async def store_medical_knowledge(knowledge_data: dict) -> str:
    """
    Store medical knowledge document with embedding

    Args:
        knowledge_data: Dict containing medical knowledge with embedding

    Returns:
        MongoDB document ID
    """
    global _database

    if _database is None:
        raise Exception("Database not connected. Call connect_mongodb() first.")

    try:
        knowledge = _database["medical_knowledge"]

        result = await knowledge.insert_one(knowledge_data)

        print(f"📚 Stored medical knowledge: {knowledge_data.get('title', 'unknown')}")

        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Failed to store medical knowledge: {str(e)}")
        raise


async def search_knowledge_base(query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search medical knowledge base using vector similarity
    Note: Requires MongoDB Atlas with vector search index configured

    Args:
        query_embedding: Query embedding vector
        limit: Maximum number of results

    Returns:
        List of relevant medical knowledge documents
    """
    try:
        # Create a fresh MongoDB client for this event loop
        from motor.motor_asyncio import AsyncIOMotorClient

        mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB_NAME", "carepoint_medical")

        # Create client in this event loop
        client = AsyncIOMotorClient(mongodb_uri)
        database = client[db_name]
        knowledge = database["medical_knowledge"]

        # For local MongoDB without Atlas Vector Search, use simple similarity calculation
        # In production with Atlas, use $vectorSearch aggregation stage

        # Get all knowledge documents
        cursor = knowledge.find().limit(100)  # Limit for performance
        all_docs = await cursor.to_list(length=100)

        # Close the client
        client.close()

        if not all_docs:
            print("⚠️  Knowledge base is empty")
            return []

        # Calculate similarity scores
        from embeddings import calculate_similarity

        scored_docs = []
        for doc in all_docs:
            if "embedding" in doc:
                similarity = calculate_similarity(query_embedding, doc["embedding"])
                doc["similarity_score"] = similarity
                scored_docs.append(doc)

        # Sort by similarity and take top results
        scored_docs.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_results = scored_docs[:limit]

        # Convert ObjectId to string
        for doc in top_results:
            doc["_id"] = str(doc["_id"])

        print(f"🔍 Found {len(top_results)} relevant knowledge documents")

        return top_results
    except Exception as e:
        print(f"❌ Failed to search knowledge base: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


async def get_similar_cases(symptoms: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Find similar consultation cases based on text similarity

    Args:
        symptoms: Patient symptoms text
        limit: Maximum number of similar cases to return

    Returns:
        List of similar consultation records
    """
    global _database

    try:
        consultations = _database["consultations"]

        # For now, do simple text search on keywords
        # TODO: Add embeddings to consultations for better similarity search

        # Extract potential keywords (simple approach)
        keywords = symptoms.lower().split()

        # Search for consultations with similar keywords
        cursor = consultations.find({
            "$or": [
                {"input.text": {"$regex": keyword, "$options": "i"}}
                for keyword in keywords[:3]  # Use first 3 words
            ]
        }).limit(limit)

        similar_cases = await cursor.to_list(length=limit)

        # Convert ObjectId to string
        for case in similar_cases:
            case["_id"] = str(case["_id"])

        print(f"🔍 Found {len(similar_cases)} similar cases for: {symptoms[:50]}")

        return similar_cases
    except Exception as e:
        print(f"❌ Failed to find similar cases: {str(e)}")
        return []


async def get_consultation_by_trace_id(trace_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific consultation by trace ID

    Args:
        trace_id: OpenTelemetry trace ID

    Returns:
        Consultation record or None
    """
    global _database

    try:
        consultations = _database["consultations"]

        record = await consultations.find_one({"trace_id": trace_id})

        if record:
            record["_id"] = str(record["_id"])
            print(f"📄 Retrieved consultation: {trace_id}")
        else:
            print(f"⚠️  No consultation found with trace_id: {trace_id}")

        return record
    except Exception as e:
        print(f"❌ Failed to retrieve consultation: {str(e)}")
        return None
