from pymongo import MongoClient
import getpass
import sys

# Configuração
ORIGEM_HOST = "10.61.8.28:1352"
DESTINO_HOST = "10.61.8.174:27017"
DB_NAME = "risco"
BUCKET = "fs"  # ou seu_bucket

# Credenciais interativas (compatível MongoDB 4.0+)
print("=== Credenciais ===")
user = input("Usuário: ").strip()
pwd = getpass.getpass("Senha: ") if user else None


# 1. Montar URIs (compatível MongoDB 4.0, SCRAM-SHA-1/256)
def make_uri(host, user, pwd, db):
    if user and pwd:
        return f"mongodb://{user}:{pwd}@{host}/{db}?authSource={db}&authMechanism=SCRAM-SHA-1"
    return f"mongodb://{host}:27017/"


uri_origem = make_uri(ORIGEM_HOST, user, pwd, DB_NAME)
uri_destino = make_uri(DESTINO_HOST, user, pwd, DB_NAME)

# 2. Conectar (timeout 30s, compatível v4.0)
origem = MongoClient(uri_origem, serverSelectionTimeoutMS=30000)[DB_NAME]
destino = MongoClient(uri_destino, serverSelectionTimeoutMS=30000)[DB_NAME]

# 3. Coleções GridFS
files_origem = origem[f"{BUCKET}.files"]
chunks_origem = origem[f"{BUCKET}.chunks"]
files_destino = destino[f"{BUCKET}.files"]
chunks_destino = destino[f"{BUCKET}.chunks"]

# 4. Lógica sync (igual anterior)
print("🔍 Max uploadDate destino...")
max_date_dest = files_destino.find().sort("uploadDate", -1).limit(1).next()["uploadDate"]
print(f"   {max_date_dest}")

print("📤 Sync novos arquivos...")
novos_files = list(files_origem.find({"uploadDate": {"$gt": max_date_dest}}))
print(f"   {len(novos_files)} arquivos novos")

copiados = 0
for file_doc in novos_files:
    file_id = file_doc["_id"]

    # fs.files
    files_destino.replace_one({"_id": file_id}, file_doc, upsert=True)

    # fs.chunks (todos deste file)
    chunks_count = chunks_origem.count_documents({"files_id": file_id})
    if chunks_count > 0:
        for chunk in chunks_origem.find({"files_id": file_id}).sort("n", 1):
            chunks_destino.replace_one(
                {"files_id": file_id, "n": chunk["n"]},
                chunk, upsert=True
            )
        print(f"   ✅ {file_doc.get('filename', file_id)[:50]}... ({chunks_count} chunks)")

    copiados += 1

print(f"🎉 {copiados} arquivos sincronizados!")
print(f"   Total destino: {files_destino.count_documents({})}")