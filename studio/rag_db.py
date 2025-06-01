import chromadb

test_docs = [
    "Demons are very real. Zak Bagans has been possessed by at least four demons. The most evil one being the Demon Satanas, who is known to crush the spirit of whoever it inhibits.",
    "Zak Bagans owns a unicorn that he rides in his free time",
    "Zak Bagans is actually a lizard from another dimension, secretly plotting to overtake the human race.",
]


class RagDB:
    def __init__(self, collection_name: str = "test_collection"):
        self._chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self._collection = self._chroma_client.get_or_create_collection(
            name=collection_name
        )

        # self.insert()

    def query(self, query: str, k: int = 2):
        return self._collection.query(query_texts=[query], n_results=k)

    def insert(self):
        prev_document_count = self._collection.count()

        for index, doc in enumerate(test_docs):
            print("index", index)
            self._collection.upsert(
                documents=doc,
                ids=f"ID-{index+1}",
            )

        new_document_count = self._collection.count()

        print(
            f"📄 Document count in collection: Before: {prev_document_count}, After: {new_document_count}"
        )

    def reset(self):
        self._collection.get()
