import streamlit as st
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import UnstructuredFileLoader
from langchain.docstore.document import Document
import os
import time
import pytube
import openai

# Chat UI title
st.header("Upload your own files and ask questions like ChatGPT")
st.subheader('File type supported: PDF/DOCX/TXT :city_sunrise:')

# File uploader in the sidebar on the left
with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.")
    st.stop()

# Set OPENAI_API_KEY as an environment variable
os.environ["OPENAI_API_KEY"] = openai_api_key

llm = ChatOpenAI(temperature=0,max_tokens=1000, model_name="gpt-3.5-turbo",streaming=True)

# Load version history from the text file
def load_version_history():
    with open("version_history.txt", "r") as file:
        return file.read()
        
with st.sidebar:
    uploaded_files = st.file_uploader("Please upload your files", accept_multiple_files=True, type=None)
    youtube_url = st.sidebar.text_input("YouTube URL")
    st.info(load_version_history(), icon="🤖")
    st.info("Please refresh the browser if you decided to upload more files to reset the session", icon="🚨")

# Check if files are uploaded or YT URL is provided
if uploaded_files or youtube_url:
    # Print the number of files uploaded or YouTube URL provided to console
    print(f"Number of files uploaded: {len(uploaded_files)}")

        # Create a progress bar with an initial value of 0
    progress_bar = st.progress(0)

    # Define a text message to display above the progress bar
    progress_text = "Uploading in progress. Please wait."

    # Iterate through the range (0 to 100, for example) to simulate progress
    for percent_complete in range(101):
    # Update the progress bar's value and text message
        progress_bar.progress(percent_complete, text=progress_text)

        # Sleep to simulate some processing time
        time.sleep(0.1)

    # Clear the progress bar when processing is complete
    progress_bar.empty()
        
    # Load the data and perform preprocessing only if it hasn't been loaded before
    if "processed_data" not in st.session_state:
        # Load the data from uploaded PDF files
        documents = []
        if uploaded_files:
            for uploaded_file in uploaded_files:
                # Get the full file path of the uploaded file
                file_path = os.path.join(os.getcwd(), uploaded_file.name)

                # Save the uploaded file to disk
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())

                # Use UnstructuredFileLoader to load the PDF file
                loader = UnstructuredFileLoader(file_path)
                loaded_documents = loader.load()
                print(f"Number of files loaded: {len(loaded_documents)}")

                # Extend the main documents list with the loaded documents
                documents.extend(loaded_documents)

        # Load the YouTube audio stream if URL is provided
        if youtube_url:
            youtube_video = pytube.YouTube(youtube_url)
            streams = youtube_video.streams.filter(only_audio=True)
            stream = streams.first()
            stream.download(filename="youtube_audio.mp4")
            with open("youtube_audio.mp4", "rb") as audio_file:
                transcript = openai.Audio.transcribe("whisper-1", audio_file)
            youtube_text = transcript['text']
            # Create a Langchain document instance for the transcribed text
            youtube_document = Document(page_content=youtube_text, metadata={})
            documents.append(youtube_document)

        # Chunk the data, create embeddings, and save in vectorstore
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
        document_chunks = text_splitter.split_documents(documents)

        embeddings = OpenAIEmbeddings()
        vectorstore = Chroma.from_documents(document_chunks, embeddings)

        # Store the processed data in session state for reuse
        st.session_state.processed_data = {
            "document_chunks": document_chunks,
            "vectorstore": vectorstore,
        }

        # Print the number of total chunks to console
        print(f"Number of total chunks: {len(document_chunks)}")


    else:
        # If the processed data is already available, retrieve it from session state
        document_chunks = st.session_state.processed_data["document_chunks"]
        vectorstore = st.session_state.processed_data["vectorstore"]

    # Initialize Langchain's QA Chain with the vectorstore
    qa = ConversationalRetrievalChain.from_llm(llm,vectorstore.as_retriever())

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Ask your questions?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Query the assistant using the latest chat history
        result = qa({"question": prompt, "chat_history": [(message["role"], message["content"]) for message in st.session_state.messages]})

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            full_response = result["answer"]
            message_placeholder.markdown(full_response + "|")
        message_placeholder.markdown(full_response)    
        print(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})

else:
    st.write("Please upload your files and provide a YouTube URL for transcription.")
