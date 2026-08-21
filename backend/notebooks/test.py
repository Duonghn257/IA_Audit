import os
from openai import AzureOpenAI
from dotenv import load_dotenv
load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = "2024-02-01"

# Lưu ý: đây là DEPLOYMENT NAME trên Azure,
# không nhất thiết giống model name.
AZURE_EMBEDDING_DEPLOYMENT = "text-embedding-3-small"

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
)

try:
    response = client.embeddings.create(
        model=AZURE_EMBEDDING_DEPLOYMENT,
        input="Xin chào, đây là câu test Azure OpenAI embedding."
    )

    embedding = response.data[0].embedding

    print("✅ Azure OpenAI key hoạt động!")
    print("Embedding dimension:", len(embedding))
    print("First 10 values:", embedding[:10])
    print("Usage:", response.usage)

except Exception as e:
    print("❌ Azure OpenAI request failed")
    print(type(e).__name__, ":", e)