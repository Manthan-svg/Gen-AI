from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter


loader = PyPDFLoader("/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/c4611_sample_explain.pdf")
data = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=100)
chunks = text_splitter.split_documents(data)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


vector_db = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chorma_db"
)

query = "How to deploy the sample?";
docs = vector_db.similarity_search(query,k=1)

print(f"Found {len(docs)} relevant sections:")

for doc in docs:
    print("-" * 30)
    print(doc.page_content+ "...")
