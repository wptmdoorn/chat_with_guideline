# import csv
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma

from langchain.document_loaders import UnstructuredPDFLoader
from langchain.text_splitter import CharacterTextSplitter
import os
import json

from dotenv import load_dotenv
load_dotenv()


def process_file(file):
    print(f'Loading {file}...')
    loader = UnstructuredPDFLoader(os.path.join('docs', file))
    data = loader.load()

    print(f'Total length of PDF: {len(data[0].page_content)}')
    text_splitter = CharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    chunks = text_splitter.split_documents(data)
    print(f'Created {len(chunks)} chunks')
    print(f'Chunk 50 example: {chunks[50]}')

    embeddings = OpenAIEmbeddings()
    pdfsearch = Chroma.from_documents(
        chunks, embeddings, persist_directory=f'embeddings/{file}')
    pdfsearch.persist()

    print(f'Saved embeddings to embeddings/{file}')

    # Appending embeddings to metadata.json
    with open('embeddings/metadata.json', 'r') as f:
        d = json.load(f)
        d.append({"dir": file, "title": "", type: ""})

    with open('embeddings/metadata.json', 'w') as f:
        json.dump(d, f, indent=4)

    print(f'Saved metadata to embeddings/metadata.json')


print('Searching for PDF files...')
pdf_files = [f for f in os.listdir('docs') if f.endswith('.pdf')]
print(f'Found {len(pdf_files)} PDF files')

for file in pdf_files:
    if not os.path.exists(f'embeddings/{file}'):
        print(f'Creating embeddings for {file}')

        os.mkdir(f'embeddings/{file}')
        process_file(file)
