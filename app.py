from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from fastapi import FastAPI
from sqlalchemy import create_engine
from apscheduler.schedulers.background import BackgroundScheduler
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
load_dotenv()




@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the scheduler when the FastAPI app starts up
    scheduler.start()
    yield
    # Shut down the scheduler when the FastAPI app shuts down
    scheduler.shutdown()



app = FastAPI(lifespan=lifespan) 

active_session_ids = set()




llm = init_chat_model("gemini-2.0-flash", 
                    model_provider="google_genai", 
                    api_key=os.getenv('GEMINI_API_KEY'))




system_prompt = """
        You are Oninfo, a smart AI assistant designed to help users with clear, accurate, and relevant information.
        You can answer general questions, provide guidance, and remember the conversation to offer better assistance.

        Always be polite, informative, and concise. When necessary, ask follow-up questions to better understand the user's needs.

        If a user asks about Oninfo services or features, confidently explain them.

        Avoid guessing—only answer if you’re certain or provide a best-effort response with a disclaimer.
"""




prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{query}"),
    ]
)




chain = prompt | llm





engine = create_engine("sqlite:///sqlite.db")

chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: SQLChatMessageHistory(session_id=session_id, connection=engine),
    input_messages_key="query",
    history_messages_key="history",
)





# Function to delete chat history for a given session ID
def delete_session_history(session_id: str):
    try:
        history = SQLChatMessageHistory(session_id=session_id, connection=engine)
        history.clear()
        print(f"Chat history for session ID '{session_id}' cleared.")
    except Exception as e:
        print(f"Error clearing history for session ID '{session_id}': {e}")




# Initialize the scheduler
scheduler = BackgroundScheduler()





@app.post("/chatbot")
async def cvn_chatbot(user_id: str, query: str):

    if user_id not in active_session_ids:

        active_session_ids.add(user_id)

        scheduler.add_job(delete_session_history, 'interval', seconds=100, args=[user_id]) #hours
        print(f"Deletion scheduled for session ID '{user_id}' every 100 seconds.")


    config = {"configurable": {"session_id": user_id}}
    output = chain_with_history.invoke({"query": query}, config=config)
    return output.content





# ----------------------------
# Run with Uvicorn
# ----------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("d_app:app", host="127.0.0.1", port=8000, reload=True) 




