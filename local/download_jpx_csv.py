import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin


def download_jpx_csv(base_url, target_filename, save_path="."):
    """
    Downloads a specified CSV file from the JPX website.

    Args:
        base_url (str): The URL of the webpage containing the CSV link.
        target_filename (str): The name of the CSV file to download (e.g., "rb20250821.csv").
        save_path (str): The directory where the CSV file will be saved. Defaults to current directory.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Step 1: Fetch the webpage content
    try:
        print(f"Fetching webpage: {base_url}")
        response = requests.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        print("Webpage fetched successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {base_url}: {e}")
        return False

    # Step 2: Parse the HTML content and locate the download link
    soup = BeautifulSoup(response.text, "html.parser")
    download_link = None

    # Look for <a> tags with href containing the target filename
    for link in soup.find_all("a", href=True):
        if target_filename in link["href"]:
            download_link = link["href"]
            break

    # Also check for <a> tags with text containing the target filename, if href is not direct
    if not download_link:
        for link in soup.find_all("a"):
            if link.string and target_filename in link.string:
                # This case might require more logic to find the actual href if it's not direct
                # For now, we assume the href contains the filename if the text does.
                # This might need refinement if the link structure is more complex.
                if link.has_attr("href"):
                    download_link = link["href"]
                    break

    if not download_link:
        print(f"Error: Download link for '{target_filename}' not found on the page.")
        return False

    # Construct full download URL if it's a relative path
    if not download_link.startswith("http"):
        # Assuming the base URL is the directory for relative links
        # This might need adjustment based on the actual website structure
        download_url = urljoin(base_url, download_link)
    else:
        download_url = download_link

    print(f"Found download link: {download_url}")

    # Step 3: Download the CSV file
    try:
        print(f"Downloading file from: {download_url}")
        file_response = requests.get(
            download_url, stream=True, headers=headers, timeout=30
        )
        file_response.raise_for_status()
        print("File download initiated.")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file from {download_url}: {e}")
        return False

    # Step 4: Save the CSV file locally
    os.makedirs(save_path, exist_ok=True)
    local_filepath = os.path.join(save_path, target_filename)

    try:
        with open(local_filepath, "wb") as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(
            f"File '{target_filename}' downloaded and saved to '{local_filepath}' successfully."
        )
        return True
    except IOError as e:
        print(f"Error saving file '{local_filepath}': {e}")
        return False


if __name__ == "__main__":
    base_url = "https://www.jpx.co.jp/markets/derivatives/settlement-price/index.html"
    target_filename = "rb20250821.csv"

    # You can specify a different save_path if needed, e.g., "data"
    if download_jpx_csv(base_url, target_filename):
        print("Script finished successfully.")
    else:
        print("Script finished with errors.")
