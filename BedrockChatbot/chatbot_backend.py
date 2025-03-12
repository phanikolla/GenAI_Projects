#Steps
#1 import the ConversationSummaryBufferMemory, ConversationChain, ChatBedrock (BedrockChat) Langchain Modules
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory
from langchain_aws import ChatBedrock
#2a Write a function for invoking model- client connection with Bedrock with profile, model_id & Inference params- model_kwargs
def demo_chatbot():
    # Create an instance of the model
    demo_llm = ChatBedrock(
        credentials_profile_name='default',
        model_id='anthropic.claude-3-haiku-20240307-v1:0',
        model_kwargs={
            "max_tokens": 300,
            "temperature": 0.1,
            "top_p": 0.9,
            "stop_sequences": ["\n\nHuman:"]})
    return demo_llm
    
    # Invoke the model and get the response
    #response = demo_llm.invoke(input_text)
    
    # Print out the actual response content
    #print(response)  # This is to check if the model is returning the correct output

    # Optionally, extract specific content from the response if needed (adjust based on actual response format)
   # if hasattr(response, 'get'):
    #    return response.get('text', 'No response text found')
    #return 'No response data available'

# Test the chatbot
#response = demo_chatbot(input_text="Hi, what is the temperature in Hyderabad in May?")
#print(response)

#3 Create a Function for  ConversationSummaryBufferMemory  (llm and max token limit)
def demo_memory():
    llm_data=demo_chatbot()
    memory=ConversationSummaryBufferMemory(llm=llm_data,max_token_limit=300)
    return memory

#4 Create a Function for Conversation Chain - Input text + Memory
def demo_conversation(input_text,memory):
    llm_chain_data=demo_chatbot()
    llm_conversation=ConversationChain(llm=llm_chain_data,memory=memory,verbose=True)

#5 Chat response using invoke (Prompt template)
    chat_reply=llm_conversation.invoke(input_text)
    return chat_reply['response']    