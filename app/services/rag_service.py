import google.generativeai as genai
from app.config import settings
from app.models.document import DocumentChunk

genai.configure(api_key=settings.GEMINI_API_KEY)

GENERATION_MODEL = "gemini-2.5-flash"


async def generate_answer(question: str, chunks: list[DocumentChunk]) -> str:
    context = "\n\n---\n\n".join([chunk.content for chunk in chunks])

    prompt = f"""You are a helpful assistant. Answer the question using ONLY the context provided below.
If the answer is not in the context, say "I could not find an answer in the provided document."

Context:
{context}

Question: {question}

Answer:"""

    model = genai.GenerativeModel(GENERATION_MODEL)
    response = await model.generate_content_async(prompt)
    return response.text