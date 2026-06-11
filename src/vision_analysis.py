"""
src/vision_analysis.py
Real video analysis using OpenCV Haar Cascade face detection.
"""

import os


def analyze_video(video_path):
    """
    Analyzes the student session video frame-by-frame using OpenCV
    Haar Cascade face detection.
    - Face visible and centered      -> high focus  (score: 80-100)
    - Face visible but off-center    -> medium focus (score: 50-79)
    - Face not visible               -> low focus   (score: 0-49)
    Returns a structured dict with all focus metrics.
    """
    print(f"[Vision] Analyzing video: {video_path}")

    if not video_path or not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
        print("[Vision] Video not found or empty.")
        return _empty_vision_result()

    try:
        import cv2

        # Use OpenCV's built-in Haar Cascade (always available with opencv-python)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("[Vision] Cannot open video.")
            return _empty_vision_result()

        fps           = cap.get(cv2.CAP_PROP_FPS) or 10
        total_frames  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frame_scores      = []
        frames_with_face  = 0
        total_frames_read = 0

        # Sample every other frame for performance
        sample_interval = max(1, int(fps // 2))

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            total_frames_read += 1
            if total_frames_read % sample_interval != 0:
                continue

            h, w = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40)
            )

            if len(faces) > 0:
                frames_with_face += 1
                # Use the largest detected face
                x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                face_cx = x + fw / 2
                face_cy = y + fh / 2

                # Measure how centred the face is (0 = perfectly centred)
                offset_x = abs((face_cx / w) - 0.5)
                offset_y = abs((face_cy / h) - 0.5)
                offset   = (offset_x + offset_y) / 2

                if offset < 0.10:
                    score = 95
                elif offset < 0.20:
                    score = 80
                elif offset < 0.35:
                    score = 60
                else:
                    score = 40
            else:
                score = 10  # face not visible

            frame_scores.append(score)

        cap.release()

        if not frame_scores:
            return _empty_vision_result()

        sampled       = len(frame_scores)
        avg_score     = round(sum(frame_scores) / sampled)
        face_ratio    = round(frames_with_face / sampled, 2)
        video_dur_sec = total_frames_read / fps

        focused_sec    = round(video_dur_sec * face_ratio * (avg_score / 100))
        distracted_sec = round(video_dur_sec - focused_sec)
        summary        = _focus_summary(avg_score, face_ratio)

        print(f"[Vision] Done. Avg focus: {avg_score}/100 | Face ratio: {face_ratio}")

        return {
            "average_focus_score":         avg_score,
            "face_detected_ratio":         face_ratio,
            "focused_duration_seconds":    focused_sec,
            "distracted_duration_seconds": distracted_sec,
            "focus_summary":               summary
        }

    except ImportError as e:
        print(f"[Vision] OpenCV not available ({e}).")
        return _empty_vision_result()
    except Exception as e:
        print(f"[Vision] Unexpected error: {e}.")
        return _empty_vision_result()


def _focus_summary(score, ratio):
    if score >= 85 and ratio >= 0.85:
        return "Excellent focus -- student remained attentive throughout the session."
    elif score >= 70:
        return "Mostly focused with a few short distractions."
    elif score >= 50:
        return "Moderate focus -- some periods of distraction detected."
    else:
        return "Low focus -- student was frequently distracted or away from camera."


def _empty_vision_result():
    return {
        "average_focus_score":         0,
        "face_detected_ratio":         0,
        "focused_duration_seconds":    0,
        "distracted_duration_seconds": 0,
        "focus_summary":               "No video data provided yet."
    }


if __name__ == "__main__":
    import json
    result = analyze_video("../data/video/sample_session.mp4")
    print(json.dumps(result, indent=2))
