import os
import subprocess
import plistlib
from datetime import datetime
import zipfile
import shutil

# Directory is the root of the repository
ROOT_DIR = "."
TEMP_DIR = "temp_extracted"  # Temporary directory for extracted files

# Current date (set to today's date from system)
CURRENT_DATE = datetime.now()

def decode_mobileprovision(file_path, output_path):
    """Decode a .mobileprovision file into a .plist file using the security command."""
    try:
        subprocess.run(
            ["security", "cms", "-D", "-i", file_path, "-o", output_path],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error decoding {file_path}: {e.stderr}")
        return False

def check_expiry(file_path):
    """Check if a .mobileprovision file is expired."""
    temp_plist = f"{file_path}.plist"
    
    # Decode the .mobileprovision file
    if not decode_mobileprovision(file_path, temp_plist):
        print(f"{file_path}: Failed to decode")
        return
    
    # Parse the plist file
    try:
        with open(temp_plist, "rb") as f:
            plist_data = plistlib.load(f)
            expiration_date = plist_data.get("ExpirationDate")
            
            if not expiration_date:
                print(f"{file_path}: No expiration date found")
                return
            
            # Compare with current date
            is_expired = expiration_date < CURRENT_DATE
            status = "EXPIRED" if is_expired else "VALID"
            print(f"{file_path}: {status} (Expires: {expiration_date})")
    
    except Exception as e:
        print(f"{file_path}: Error processing - {str(e)}")
    
    finally:
        # Clean up temporary plist file
        if os.path.exists(temp_plist):
            os.remove(temp_plist)

def extract_mobileprovision_from_ipa(ipa_path):
    """Extract embedded.mobileprovision from an .ipa file."""
    try:
        with zipfile.ZipFile(ipa_path, 'r') as ipa_zip:
            extracted_paths = []
            # Look for embedded.mobileprovision in Payload/*.app/
            for file in ipa_zip.namelist():
                if file.endswith("embedded.mobileprovision"):
                    # Extract to temporary directory with unique name
                    extract_path = os.path.join(TEMP_DIR, os.path.basename(file) + f"_{len(extracted_paths)}")
                    ipa_zip.extract(file, TEMP_DIR)
                    # Move to avoid overwriting if multiple files
                    shutil.move(os.path.join(TEMP_DIR, file), extract_path)
                    extracted_paths.append(extract_path)
            if not extracted_paths:
                print(f"{ipa_path}: No embedded.mobileprovision found")
            return extracted_paths
    except Exception as e:
        print(f"{ipa_path}: Error extracting - {str(e)}")
        return []

def process_directory(directory):
    """Recursively process directory for .mobileprovision and .ipa files."""
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)

            if filename.endswith(".mobileprovision"):
                # Check standalone .mobileprovision files
                check_expiry(file_path)

            elif filename.endswith(".ipa"):
                # Extract and check embedded .mobileprovision from .ipa
                extracted_paths = extract_mobileprovision_from_ipa(file_path)
                for extracted_path in extracted_paths:
                    check_expiry(extracted_path)

def main():
    # Ensure temp directory exists and is empty
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

    # Process all files recursively
    process_directory(ROOT_DIR)

    # Clean up temporary directory
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)

if __name__ == "__main__":
    main()