"""Clear old 384-dimension embeddings from MongoDB before switching to OpenAI embeddings"""
import asyncio
from mongodb_client import connect_mongodb, close_mongodb

async def clear_embeddings():
    """Remove all documents with old 384-dimension embeddings"""
    db = await connect_mongodb()

    # Delete all documents from medical_knowledge collection
    result = await db.medical_knowledge.delete_many({})
    print(f"✅ Deleted {result.deleted_count} old embeddings from medical_knowledge collection")

    await close_mongodb()
    print("✅ Ready for new OpenAI embeddings (1536 dimensions)")

if __name__ == "__main__":
    asyncio.run(clear_embeddings())
