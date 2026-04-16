from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from .vector_store import get_vector_store
from .config import OLLAMA_MODEL, OLLAMA_BASE_URL

def get_llm():
    return ChatOllama(
        model=OLLAMA_MODEL,
        temperature=0.1,
        num_ctx=8192,
        base_url=OLLAMA_BASE_URL,
    )

def format_docs(docs):
    return "\n\n".join([f"مستند: {doc.page_content}" for doc in docs])

def get_rag_chain():
    vectorstore = get_vector_store()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    template = """أنت مساعد بحث علمي وتقني دقيق ومحترف.

استخدم السياق التالي فقط للإجابة.
إذا لم تجد معلومات كافية، قل بوضوح: "لا توجد معلومات كافية في الوثائق المرفوعة".

سياق:
{context}

سؤال: {question}

الإجابة (بنفس لغة السؤال):"""

    prompt = ChatPromptTemplate.from_template(template)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | get_llm()
        | StrOutputParser()
    )

    return chain
