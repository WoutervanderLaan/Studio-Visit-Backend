import chromadb


class RagDB:
    def __init__(self, collection_name: str = "test_collection"):

        self._chroma_client = chromadb.PersistentClient(path="./chroma_db")

        self._collection = self._chroma_client.get_or_create_collection(
            name=collection_name
        )

        self.insert()

    def query(self, query: str, k: int = 2):
        return self._collection.query(query_texts=[query], n_results=k)

    def insert(self):
        prev_document_count = self._collection.count()

        self._collection.upsert(
            documents=[
                "This is a document about pineapple, which is actually a conduit to the spirit world",
                "This is a document about oranges, which are actually a mocking of the holy trinity",
            ],
            ids=["id1", "id2"],
        )

        new_document_count = self._collection.count()

        print(
            f"📄 Document count in collection: Before: {prev_document_count}, After: {new_document_count}"
        )

    def reset(self):
        self._collection.delete()
