import os

from listener_mongodb import MongoChangeStreamReplicator


if __name__ == "__main__":
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise SystemExit("Defina MONGODB_URI antes de iniciar el listener")
    MongoChangeStreamReplicator(uri).ejecutar()
