from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")
notes_dir = "notes/"
notes = []
contents = []

for file in os.listdir(notes_dir):
    with open(os.path.join(notes_dir, file), "r") as f:
        text = f.read()
        contents.append(text)
        notes.append(file)

embeddings = model.encode(contents)


def search(query):
    query_vec = model.encode([query])
    scores = cosine_similarity(query_vec, embeddings)[0]
    top_idx = np.argmax(scores)
    return notes[top_idx], contents[top_idx]


result = search("how to reverse a linked list")
print(result)
