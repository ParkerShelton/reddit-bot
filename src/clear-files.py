import os

def clear_file_type(folder_path, file_extension):
    """
    Deletes all files with a specified extension in a given folder.

    Args:
        folder_path (str): The path to the folder.
        file_extension (str): The file extension to target (e.g., '.log').
    """
    try:
        # Check if the folder exists
        if not os.path.isdir(folder_path):
            print(f"Error: Folder '{folder_path}' not found.")
            return

        # List all files in the directory
        for filename in os.listdir(folder_path):
            # Check if the filename ends with the specified extension
            if filename.endswith(file_extension):
                file_path = os.path.join(folder_path, filename)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except OSError as e:
                    print(f"Error deleting file {file_path}: {e}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Example usage:
# Replace the folder path and file extension with your desired values.
audio_folder = "./audio_posts"
audio_extension = ".mp3"

old_posts_folder = "./old-posts"
post_extension = ".txt"

clear_file_type(audio_folder, audio_extension)
clear_file_type(old_posts_folder, post_extension)
