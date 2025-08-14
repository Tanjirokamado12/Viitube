import os
import subprocess
import urllib.request
import zipfile
import shutil
import socket
import sys
import tempfile

CACHE_FILE = "local_ip_cache.txt"  # File to store the cached IP
APKTOOL_PATH = "apktool.jar"      # Path to APKTool JAR file
APKRENAMER_ZIP_URL = "https://github.com/dvaoru/ApkRenamer/releases/download/1.9.7/ApkRenamer.zip"  # ApkRenamer zip URL
APKRENAMER_DIR = "ApkRenamer"  # Directory where ApkRenamer will be extracted

# Function to get the local IP address
def get_local_ip():
    try:
        # Connect to an external server to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        # Try connecting to Google's public DNS server
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]  # Get the local network IP
    except Exception:
        local_ip = '127.0.0.1'  # Fallback to localhost if no network is available
    finally:
        s.close()
    return local_ip

# Function to read the cached IP if it exists
def read_cached_ip():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            cached_ip = f.read().strip()
            print(f"Using cached IP: {cached_ip}")
            return cached_ip
    else:
        return None

# Function to write the IP to cache
def save_ip_to_cache(ip):
    with open(CACHE_FILE, 'w') as f:
        f.write(ip)
    print(f"IP {ip} saved to cache.")

# Check if Java is installed
def check_java():
    try:
        subprocess.run(['java', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Java is installed.")
        return True
    except subprocess.CalledProcessError:
        print("Java is not installed. Please install Java first.")
        return False

# Download APKTool
def download_apktool():
    apktool_url = "https://github.com/iBotPeaches/Apktool/releases/download/v2.8.1/apktool_2.8.1.jar"  # Latest APKTool JAR
    apktool_file = APKTOOL_PATH
    
    print("Downloading APKTool...")
    try:
        urllib.request.urlretrieve(apktool_url, apktool_file)
        print(f"APKTool downloaded as {apktool_file}")
    except Exception as e:
        print(f"Error downloading APKTool: {e}")
        sys.exit(1)

# Create a wrapper script to use APKTool
def create_apktool_script():
    script_content = """#!/bin/bash
    java -jar apktool.jar "$@"
    """
    with open("apktool", "w") as f:
        f.write(script_content)
    os.chmod("apktool", 0o755)  # Make the script executable
    print("Wrapper script 'apktool' created.")

# Decompile APK directly into the temp directory
def decompile_apk(apk_path):
    # Define the temp directory (same directory as the script)
    temp_dir = os.path.join(os.getcwd(), 'temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Run APKTool to decompile the APK directly into the temp directory with -f flag to overwrite
    try:
        print(f"Decompiling APK {apk_path} into {temp_dir}...")
        subprocess.run(['java', '-jar', APKTOOL_PATH, 'd', '-f', apk_path, '-o', temp_dir], check=True)
        print(f"APK decompiled successfully into: {temp_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Error decompiling APK: {e}")
        sys.exit(1)

# Check for cached IP, or get new one and cache it
def get_or_cache_local_ip():
    cached_ip = read_cached_ip()
    if cached_ip is None:  # If no cached IP, fetch and save it
        local_ip = get_local_ip()
        save_ip_to_cache(local_ip)
        return local_ip
    return cached_ip

# Replace occurrences of strings in .smali files
def replace_in_smali_files(smali_dir, local_ip):
    # Define the replacements as a list of tuples (old, new)
    replacements = [
        ("http://gdata.youtube.com/", f"http://{local_ip}/"),
        ("https://gdata.youtube.com/", f"http://{local_ip}/"),
        ("https://www.google.com/", f"http://{local_ip}/"),
        ("AES/ECB/PKCS5Padding", "AES/ECB/ZeroBytePadding"),
        ("\"gdata.youtube.com\"", f"\"{local_ip}\""),
        ("\"dev.gdata.youtube.com\"", f"\"{local_ip}\""),
        ("\"stage.gdata.youtube.com\"", f"\"{local_ip}\""),
    ]

    # Walk through the smali directory and replace in all files
    for root, dirs, files in os.walk(smali_dir):
        for file in files:
            if file.endswith('.smali'):
                smali_file_path = os.path.join(root, file)
                print(f"Modifying {smali_file_path}...")
                with open(smali_file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Apply replacements
                for old, new in replacements:
                    file_content = file_content.replace(old, new)
                
                # Write the modified content back to the file
                with open(smali_file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)

    print("Replacements in smali files completed.")

# Recompile the APK
def recompile_apk():
    try:
        print("Recompiling APK...")
        subprocess.run(['java', '-jar', APKTOOL_PATH, 'b', 'temp', '-o', 'recompiled.apk'], check=True)
        print("APK recompiled successfully as 'recompiled.apk',rest of pathing continue at https://github.com/Tanjirokamado12/Viitube/blob/main/apk_setup.md ,changing package name part.")
    except subprocess.CalledProcessError as e:
        print(f"Error recompiling APK: {e}")
        sys.exit(1)

# Download ApkRenamer zip and extract it
def download_apkrenamer():
    if not os.path.exists(APKRENAMER_DIR):
        print("Downloading ApkRenamer...")
        try:
            urllib.request.urlretrieve(APKRENAMER_ZIP_URL, 'ApkRenamer.zip')
            print("ApkRenamer downloaded.")
            
            # Extract ApkRenamer.zip
            with zipfile.ZipFile('ApkRenamer.zip', 'r') as zip_ref:
                zip_ref.extractall(APKRENAMER_DIR)
            print(f"ApkRenamer extracted to {APKRENAMER_DIR}")
        except Exception as e:
            print(f"Error downloading or extracting ApkRenamer: {e}")
            sys.exit(1)

# Change the package name using ApkRenamer
def change_package_name(new_package_name):
    try:
        # Update the path to the ApkRenamer.jar
        apkrenamer_path = os.path.join(APKRENAMER_DIR, 'ApkRenamer', 'renamer.jar')  # Correct path
        patched_apk = os.path.join(os.getcwd(), 'recompiled.apk')  # Path to the recompiled APK
        print(f"Renaming package to: {new_package_name}...")
        
        # Run ApkRenamer using the correct path for renamer.jar
        subprocess.run(['java', '-jar', apkrenamer_path, '-a', patched_apk, '-d', '-p', new_package_name, '-n', 'Youtube'], check=True)
        print(f"Package name successfully changed to: {new_package_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error renaming package: {e}")
        sys.exit(1)


# Extract the package name from AndroidManifest.xml
def get_package_name_from_manifest():
    manifest_path = os.path.join(os.getcwd(), 'temp', 'AndroidManifest.xml')
    if not os.path.exists(manifest_path):
        print("Error: AndroidManifest.xml not found in the decompiled APK.")
        sys.exit(1)

    # Read the manifest file and extract the package name
    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Simple way to extract the package name from the manifest
    import re
    match = re.search(r'package="([^"]+)"', content)
    if match:
        return match.group(1)
    else:
        print("Error: Package name not found in AndroidManifest.xml.")
        sys.exit(1)

# Main function to setup APKTool, decompile, modify, recompile, and rename the APK
def main():
    # Check for Java installation
    if not check_java():
        return

    # Step 1: Get or cache local IP
    local_ip = get_or_cache_local_ip()

    # Step 2: Download APKTool if needed
    if not os.path.exists(APKTOOL_PATH):
        download_apktool()
        create_apktool_script()

    # Step 3: Download ApkRenamer and extract
    download_apkrenamer()

    # Step 4: Ask for APK file and decompile it
    apk_path = input("Enter the full path to the APK file you want to decompile: ")
    decompile_apk(apk_path)

    # Step 5: Modify the smali files
    replace_in_smali_files(os.path.join(os.getcwd(), 'temp', 'smali'), local_ip)

    # Step 6: Recompile APK
    recompile_apk()

if __name__ == "__main__":
    main()
