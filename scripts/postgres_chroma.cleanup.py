import psycopg2
import psycopg2.extras
import chromadb
import itertools
import json
import argparse
import os

def find_file_ids_in_dict(obj):
    """Recursively search for dicts like {"file": {"id": ...}} and collect the file IDs."""
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'file' and isinstance(v, dict) and 'id' in v:
                found.append(v['id'])
            else:
                found.extend(find_file_ids_in_dict(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(find_file_ids_in_dict(item))
    return found

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-db', '--database-url', type=str, required=True,
                        help='PostgreSQL database URL, e.g., postgres://user:pass@host:port/db')
    parser.add_argument('--chroma-path', type=str, required=False,
                        help='Full path to the chromadb vector_db directory.')
    parser.add_argument('-b', '--batch-chats', type=int, default=100)
    parser.add_argument('-l', '--list-files', action='store_true')
    parser.add_argument('--delete-files', action='store_true')
    parser.add_argument('--delete-db-entries', action='store_true')
    parser.add_argument('--delete-vectors', action='store_true')
    parser.add_argument('--no-confirm', action='store_true')
    args = parser.parse_args()

    # Connect to PostgreSQL
    conn = psycopg2.connect(args.database_url)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # File IDs from file table
    cursor.execute("SELECT id FROM file")
    files_db_ids = cursor.fetchall()
    file_ids_ = [file_['id'] for file_ in files_db_ids]
    file_ids_set = set(file_ids_)

    # Knowledge IDs
    cursor.execute("SELECT data FROM knowledge")
    knowledge_data = cursor.fetchall()
    knowledge_ids = []
    for knowledge_row in knowledge_data:
        kdata = knowledge_row['data']
        # Get dict representation
        if isinstance(kdata, str):
            kdata = json.loads(kdata)
        # For safety: expect the first value to be a list of IDs
        ids = list(kdata.values())[0] if isinstance(kdata, dict) and len(kdata) else []
        knowledge_ids.extend(ids)
    knowledge_ids_set = set(knowledge_ids)

    # Chat file IDs
    cursor.execute("SELECT chat FROM chat")
    chat_file_ids = []
    while True:
        rows = cursor.fetchmany(args.batch_chats)
        if not rows:
            break
        for chat_entry in rows:
            chat_content = chat_entry['chat']
            # Ensure chat_content is dict
            if isinstance(chat_content, str):
                try:
                    chat_content = json.loads(chat_content)
                except Exception:
                    continue  # skip unparseable
            chat_files_id = find_file_ids_in_dict(chat_content)
            chat_file_ids += list(set(chat_files_id))
        chat_file_ids_set = set(chat_file_ids)

    # Safety check
    knowledge_in_chat_id = chat_file_ids_set.intersection(knowledge_ids_set)
    if knowledge_in_chat_id:
        raise ValueError(
            f"Something went wrong: {len(knowledge_in_chat_id)} IDs from knowledges in chat file IDs, "
            f"should never happen.\nIDs: {knowledge_in_chat_id}")

    # File IDs from both chat and knowledge—do not delete them
    knowledge_and_chat_ids_set = chat_file_ids_set.union(knowledge_ids_set)
    ids_to_delete = file_ids_set.difference(knowledge_and_chat_ids_set)

    print(f"Found {len(knowledge_ids_set)} files in knowledge, "
          f"{len(chat_file_ids_set)} files in chat. Total: {len(knowledge_and_chat_ids_set)}")
    print(f"Found {len(file_ids_set)} 'file' entries in the database.")

    # read the files in the uploads directory (assume next to script or adjust as needed)
    if args.chroma_path:
        root_dir = os.path.abspath(os.path.join(args.chroma_path, ".."))
    else:
        root_dir = os.path.dirname(os.path.abspath(__file__))

    uploads_dir = os.path.join(root_dir, 'uploads')
    if not os.path.isdir(uploads_dir):
        raise ValueError(f"No path found for the uploads directory, path: {uploads_dir}")

    files = os.listdir(uploads_dir)
    files_on_storage_ids = [name.split('_')[0] for name in files]
    print(f'Found {len(files_on_storage_ids)} files in the upload directory.')

    files_to_delete = []
    unknown_files = []
    for file, file_id in zip(files, files_on_storage_ids):
        if file_id not in knowledge_and_chat_ids_set:
            files_to_delete.append(os.path.join(uploads_dir, file))
            if file_id not in ids_to_delete:
                unknown_files.append(os.path.join(uploads_dir, file))

    print(f"{len(files_to_delete)} files can be deleted from storage. "
          f"Number of storage files not found in db: {len(unknown_files)}")
    if len(files_to_delete) and args.list_files:
        print("Files to delete:")
        print(*files_to_delete, sep='\n')
        print("")

    print(f'{len(ids_to_delete)} entries can be deleted from the "file" table in the database.')

    # Chroma vector_db
    if args.chroma_path:
        chroma_path = args.chroma_path
    else:
        chroma_path = os.path.join(root_dir, "vector_db")
    client = chromadb.PersistentClient(chroma_path)
    collections = client.list_collections()
    files_collections = [
        collection.name.replace("file-", "") for collection in collections
        if collection.name.startswith("file-")
    ]
    chroma_files_set = set(files_collections)
    chroma_files_to_delete = chroma_files_set.difference(knowledge_and_chat_ids_set)
    print(f"{len(chroma_files_to_delete)} vector store entries can be deleted.")
    if len(chroma_files_to_delete) and args.list_files:
        print("Chroma collections to delete:")
        print(*chroma_files_to_delete, sep='\n')
        print("")

    answer = 'no'
    if len(chroma_files_to_delete) and args.delete_vectors:
        if not args.no_confirm:
            answer = input(
                "Deleting unused vector entries. Are you sure? yes/[no]: "
                )
        if args.no_confirm or answer.lower() in ["y", "yes"]:
            for collection in chroma_files_to_delete:
                client.delete_collection(name="file-" + collection)
            print(f"Deleted {len(chroma_files_to_delete)} vector store entries.")
        else:
            print("Aborting vector deletion.. ")

    if len(files_to_delete) and args.delete_files:
        if not args.no_confirm:
            answer = input(
                "Deleting unused files from uploads dir. Are you sure? yes/[no]: "
                )
        if args.no_confirm or answer.lower() in ["y", "yes"]:
            for file in files_to_delete:
                os.remove(file)
            print(f"Deleted {len(files_to_delete)} files from uploads dir.")
        else:
            print("Aborting files deletion.. ")

    if len(ids_to_delete) and args.delete_db_entries:
        if not args.no_confirm:
            answer = input(
                "Deleting unused entries from 'file' table. Are you sure? yes/[no]: "
                )
        if args.no_confirm or answer.lower() in ["y", "yes"]:
            placeholders = ', '.join(['%s'] * len(ids_to_delete))
            cursor.execute(f"DELETE FROM file WHERE id IN ({placeholders})", list(ids_to_delete))
            conn.commit()
            print(f"Deleted {len(ids_to_delete)} entries from 'file' table.")
        else:
            print("Aborting entry deletion.. ")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()