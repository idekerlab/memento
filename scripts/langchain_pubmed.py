from langchain_community.retrievers import PubMedRetriever

retriever = PubMedRetriever()

docs = retriever.get_relevant_documents("m6a")

for doc in docs:
    print(doc)

