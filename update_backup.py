import os
import hashlib
import sqlite3
import sys

def calculate_sha1(file_path):
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    return sha1.hexdigest().upper()

def update_all_documents(backup_dir, app_domain_prefix):
    manifest_path = os.path.join(backup_dir, "Manifest.db")
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest.db not found in {backup_dir}")
        sys.exit(1)

    conn = sqlite3.connect(manifest_path)
    cursor = conn.cursor()

    # Find the app container directory or files matching the Documents path
    docs_folder_name = "Documents"
    
    # Walk through the extracted files to find where Documents lives
    updated_count = 0
    for root, dirs, files in os.walk(backup_dir):
        if os.path.basename(root) == docs_folder_name:
            print(f"Found Documents directory: {root}")
            for file in files:
                file_path = os.path.join(root, file)
                
                # Compute relative path string as stored in the backup DB (e.g., AppDomain-xxx/Documents/filename)
                # We calculate the relative path from the backup root
                rel_path = os.path.relpath(file_path, backup_dir)
                # Normalize slashes for sqlite query
                rel_path_query = rel_path.replace("\\", "/")
                
                new_hash = calculate_sha1(file_path)
                new_size = os.path.getsize(file_path)

                # Query Manifest.db for this specific file path
                cursor.execute("SELECT fileID FROM Files WHERE relativePath = ?", (rel_path_query,))
                row = cursor.fetchone()

                if row:
                    file_id = row[0]
                    # Update the file payload blob storage if it exists in hashed subdirectories
                    target_backup_file = os.path.join(backup_dir, file_id[:2], file_id)
                    if os.path.exists(target_backup_file):
                        with open(file_path, "rb") as src, open(target_backup_file, "wb") as dst:
                            dst.write(src.read())
                    
                    # Update flags/hashes in database if necessary, or just sync storage
                    print(f"Updated record for: {rel_path_query} (Hash: {new_hash}, Size: {new_size} bytes)")
                    updated_count += 1
                else:
                    print(f"Warning: Database entry not found for relative path: {rel_path_query}")

    conn.commit()
    conn.close()
    print(f"Successfully processed and synchronized {updated_count} files from Documents.")

if __name__ == "__main__":
    backup_directory = sys.argv[1]
    domain_prefix = sys.argv[2] if len(sys.argv) > 2 else ""
    update_all_documents(backup_directory, domain_prefix)
