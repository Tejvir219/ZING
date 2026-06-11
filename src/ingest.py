import json
import os


VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".webm")
AUDIO_EXTENSIONS = (".wav", ".mp3", ".m4a", ".flac", ".ogg")
HOMEWORK_EXTENSIONS = (".pdf",)

def load_json(filepath):
    """Utility to load a JSON file."""
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found.")
        return {}
    with open(filepath, 'r') as f:
        return json.load(f)

def _first_file(directory, extensions):
    if not os.path.exists(directory):
        return ""

    matches = [
        os.path.join(directory, filename)
        for filename in sorted(os.listdir(directory))
        if filename.lower().endswith(extensions)
    ]
    return matches[0] if matches else ""


def load_data(base_path="data"):
    """Loads user-provided data for the pipeline."""
    data = {}
    
    # Load activity log
    activity_path = os.path.join(base_path, "activity", "activity_log.json")
    data['activity'] = load_json(activity_path)
    
    # Load attendance log
    attendance_path = os.path.join(base_path, "attendance", "attendance.json")
    data['attendance'] = load_json(attendance_path)
    
    # Paths for media/files (will be processed by specific modules)
    data['video_path'] = _first_file(os.path.join(base_path, "video"), VIDEO_EXTENSIONS)
    data['audio_path'] = _first_file(os.path.join(base_path, "audio"), AUDIO_EXTENSIONS)
    
    # Homework paths
    homework_dir = os.path.join(base_path, "homework")
    if os.path.exists(homework_dir):
        data['homework_paths'] = [
            os.path.join(homework_dir, f)
            for f in sorted(os.listdir(homework_dir))
            if f.lower().endswith(HOMEWORK_EXTENSIONS)
        ]
    else:
        data['homework_paths'] = []
        
    return data

if __name__ == "__main__":
    # Test ingestion
    data = load_data()
    print("Ingested data keys:", data.keys())
    print("Activity Student ID:", data['activity'].get('student_id'))
