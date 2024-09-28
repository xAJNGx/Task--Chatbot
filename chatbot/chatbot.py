import os
from dotenv import load_dotenv
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain.prompts import PromptTemplate

import google.generativeai as genai

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=GOOGLE_API_KEY)

# Load and process the Danson Solutions FAQ document
loader = TextLoader("documents/danson_solutions_faq.txt")
documents = loader.load()
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)

# Initialize embeddings and vectorstore
embeddings = GoogleGenerativeAIEmbeddings(api_key=GOOGLE_API_KEY, model="models/embedding-001")
vectorstore = Chroma.from_documents(texts, embedding=embeddings)

# Create conversational chain with RAG
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
conversation_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=vectorstore.as_retriever(),
    memory=memory
)

# Flexible MCQ generation prompt
mcq_prompt = PromptTemplate(
    input_variables=["user_input"],
    template="""Based on the following user request, generate multiple-choice questions:

User Request: {user_input}

Please generate the appropriate number of multiple-choice questions for the specified grade, subject, and subtopic. If the user hasn't specified all details, use your best judgment to fill in the gaps. Each question should have 4 options (A, B, C, D) with one correct answer. Format the output as follows:

Q1. [Question text]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct Answer: [Correct option letter]

[Repeat for the number of questions requested or a reasonable number if not specified]
"""
)

def generate_mcqs(user_input):
    prompt = mcq_prompt.format(user_input=user_input)
    response = llm.invoke(prompt)
    
    # Handle different types of responses
    if isinstance(response, str):
        return response
    elif isinstance(response, dict) and 'text' in response:
        return response['text']
    elif hasattr(response, 'content'):
        return response.content
    else:
        return str(response)

def chatbot(user_input):
    # Check for greetings
    greetings = ["hello", "hi", "hey", "greetings"]
    if any(greeting in user_input.lower() for greeting in greetings):
        return "Hello! Welcome to Danson Solutions. How can I assist you today? I can answer questions about our company or generate MCQs for educational purposes."

    # Check for MCQ generation request
    if "generate" in user_input.lower() and "mcq" in user_input.lower():
        return generate_mcqs(user_input)

    # Use RAG to answer Danson Solutions related questions
    try:
        response = conversation_chain.invoke({"question": user_input})
        return response["answer"]
    except Exception as e:
        return f"An error occurred: {str(e)}"
