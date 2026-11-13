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

def update_manifest(backup_dir, relative_path_query, new_file_path):
    manifest_path = os.path.join(backup_dir, "Manifest.db")
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest.db not found in {backup_dir}")
        sys.exit(1)

    new_hash = calculate_sha1(new_file_path)
    new_size = os.path.getsize(new_file_path)
    
    print(f"New File Hash (SHA-1): {new_hash}")
    print(f"New File Size: {new_size} bytes")

    conn = sqlite3.connect(manifest_path)
    cursor = conn.cursor()

    # Find the file record matching the relative path
    cursor.execute("SELECT fileID, relativePath FROM Files WHERE relativePath LIKE ?", (f"%{relative_path_query}%",))
    row = cursor.fetchone()

    if not row:
        print(f"Error: No database record found matching path query '{relative_path_query}'")
        conn.close()
        sys.exit(1)

    file_id, found_path = row
    print(f"Found target record: ID [{file_id}] Path [{found_path}]")

    # Update file size and blob/hash tracking fields if required by your structure,
    # or copy the payload file directly into the backup root with its uppercase SHA-1 name.
    target_backup_file = os.path.join(backup_dir, file_id[:2], file_id)
    if os.path.exists(target_backup_file):
        with open(new_file_path, "rb") as src, open(target_backup_file, "wb") as dst:
            dst.write(src.read())
        print(f"Successfully replaced payload file at {target_backup_file}")
    else:
        print(f"Warning: Payload storage file {target_backup_file} not found directly.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Example usage inside CI
    backup_directory = sys.argv[1]
    rel_query = sys.argv[2]
    replacement_file = sys.argv[3]
    update_manifest(backup_directory, rel_query, replacement_file)
