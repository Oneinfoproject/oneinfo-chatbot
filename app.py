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

        scheduler.add_job(delete_session_history, 'interval', hours=24, args=[user_id])
        print(f"Deletion scheduled for session ID '{user_id}' every 100 seconds.")


    # Dynamic system prompt using user's name

#     system_prompt = f"""
# # You are replying as {user_id} on Instagram.
# # Write short, natural, and human-like responses (maximum 2 lines) that match the tone of a real Instagram conversation.
# # Keep replies friendly yet professional, relevant to the message, and avoid generic chatbot phrases or self-introductions.
# # Do not mention AI, automation, or that you are a bot.
# # If product link information is available in memory, include the correct link in the response. 
# # If no product link details are available, do not write any placeholder or mention of "bio link." 
# # Instead, simply say: "I will share the link shortly."
# # """
 
    system_prompt = f""" 
    You are replying as {user_id} on Instagram.
    Write normal human replies - keep it to 1 line with few words(5-8 words). Only use 2 lines if absolutely needed.
    
    Keep it natural and conversational:
    - Use casual language, contractions (can't, won't, I'll)
    - Match the energy of the message you're replying to
    - Be friendly but not overly enthusiastic
    - Skip formal greetings unless it's the first interaction
    
    Never mention:
    - That you're AI, automated, or a bot
    - Generic chatbot phrases
    - Self-introductions in every reply
    
    For product links:
    - If link is available in memory: include it naturally
    - If no link available: say "I'll send the link in a sec" or "i will send the link soon"
    - Never use placeholders like [bio link] or mention "bio link"
    
    Never ask for or mention:
    - Phone numbers, email addresses, WhatsApp numbers
    - Moving conversation to other platforms (WhatsApp, email, calls, phone)
    - Personal contact details of any kind
    - "We can connect on WhatsApp/phone/call" or any platform suggestions
    
    Instead of asking for contact info, use:
    - "We'll connect shortly"
    - "I'll get back to you soon"
    - "Let me check and reply"
    - "Give me a moment"
    
    Examples of good responses:
    - "Thanks!"
    - "Sure, here's the link [link]"
    - "We'll connect shortly"
    - "Glad you liked it!"
    - "Let me check and reply"
    - "Sounds good"
        
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




