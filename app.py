from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from fastapi import FastAPI
from sqlalchemy import create_engine
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

load_dotenv()





# ---------------------------
# Lifespan Manager
# ---------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()




app = FastAPI(lifespan=lifespan)



active_session_ids = set()




# ---------------------------
# LLM Initialization
# ---------------------------
llm = init_chat_model(
    "gpt-5",
    model_provider="openai",
    api_key=os.getenv('OPEN_API_KEY')
)




# ---------------------------
# Database Setup
# ---------------------------
engine = create_engine("sqlite:///sqlite.db")




# ---------------------------
# Session History Deletion Function
# ---------------------------
def delete_session_history(session_id: str):
    try:
        history = SQLChatMessageHistory(session_id=session_id, connection=engine)
        history.clear()
        print(f"Chat history for session ID '{session_id}' cleared.")
    except Exception as e:
        print(f"Error clearing history for session ID '{session_id}': {e}")





# ---------------------------
# Scheduler Initialization
# ---------------------------
scheduler = BackgroundScheduler()





# ---------------------------
# Chatbot Endpoint
# ---------------------------
@app.post("/chatbot")
async def cvn_chatbot(user_id: str, query: str):


    if user_id not in active_session_ids:

        active_session_ids.add(user_id)

        scheduler.add_job(delete_session_history, 'interval', seconds=100, args=[user_id])
        print(f"Deletion scheduled for session ID '{user_id}' every 100 seconds.")


    # Dynamic system prompt using user's name
    system_prompt = f"""
You are replying as {user_id} on Instagram.
Write short, natural, and human-like responses (maximum 2 lines) that match the tone of a real Instagram conversation.
Keep replies friendly yet professional, relevant to the message, and avoid generic chatbot phrases or self-introductions.
Do not mention AI, automation, or that you are a bot.
"""





    # Build prompt dynamically for each request
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{query}"),
        ]
    )

    # Create chain with history tracking
    chain = prompt | llm


    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda session_id: SQLChatMessageHistory(session_id=session_id, connection=engine),
        input_messages_key="query",
        history_messages_key="history",
    )

    config = {"configurable": {"session_id": user_id}}
    output = chain_with_history.invoke({"query": query}, config=config)
    return output.content




# ----------------------------
# Run with Uvicorn
# ----------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port) 




