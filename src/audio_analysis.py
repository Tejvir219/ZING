"""
src/audio_analysis.py
Real audio analysis using librosa for duration/pauses
and faster-whisper (optional) for transcription.
"""

import os


def analyze_audio(audio_path):
    """
    Loads the WAV file using librosa, measures duration and silence gaps,
    then attempts transcription via faster-whisper.
    Returns a structured dict of all speech metrics.
    """
    print(f"[Audio] Analyzing audio: {audio_path}")

    if not audio_path or not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        print("[Audio] Audio file not found or empty.")
        return _empty_audio_result()

    try:
        import librosa
        import numpy as np

        # ── Load audio ────────────────────────────────────────────────────────
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        duration_sec = librosa.get_duration(y=y, sr=sr)
        print(f"[Audio] Duration: {duration_sec:.1f}s | Sample rate: {sr} Hz")

        # ── Pause / silence detection via RMS energy ──────────────────────────
        hop_length   = 512
        frame_length = 2048
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        silence_threshold = np.percentile(rms, 20)   # bottom 20% energy = silence
        silent_frames = np.sum(rms < silence_threshold)
        total_frames  = len(rms)
        silence_ratio = silent_frames / total_frames

        # Count transitions from speech → silence as "pauses"
        is_silent  = rms < silence_threshold
        transitions = np.diff(is_silent.astype(int))
        pause_count = int(np.sum(transitions == 1))   # speech→silence events

        # ── Transcription (optional) ──────────────────────────────────────────
        transcript = _transcribe(audio_path)

        # ── WPM calculation ───────────────────────────────────────────────────
        words      = transcript.split()
        word_count = len(words)
        speech_sec = max(1.0, duration_sec * (1 - silence_ratio))
        wpm        = round(word_count / (speech_sec / 60))

        # ── Fluency score heuristic ───────────────────────────────────────────
        fluency = _fluency_score(wpm, pause_count, silence_ratio, word_count)
        summary = _fluency_summary(fluency, wpm, pause_count)

        return {
            "transcript":       transcript,
            "audio_duration_seconds": round(duration_sec, 1),
            "word_count":       word_count,
            "words_per_minute": wpm,
            "pause_count":      pause_count,
            "fluency_score":    fluency,
            "speech_summary":   summary
        }

    except ImportError as e:
        print(f"[Audio] Library not available ({e}).")
        return _analyze_with_soundfile(audio_path, reason=str(e))
    except Exception as e:
        print(f"[Audio] Error during analysis: {e}.")
        return _analyze_with_soundfile(audio_path, reason=str(e))


def _transcribe(audio_path):
    """Try faster-whisper; return empty text if transcription is unavailable."""
    try:
        from faster_whisper import WhisperModel
        print("[Audio] Loading Whisper model (tiny)...")
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path, language="en")
        text = " ".join(seg.text.strip() for seg in segments)
        return text.strip()
    except Exception as e:
        print(f"[Audio] Whisper unavailable ({type(e).__name__}).")
        return ""


def _fluency_score(wpm, pauses, silence_ratio, word_count):
    score = 100

    # Penalise for very slow or very fast speech
    if wpm < 60:
        score -= 25
    elif wpm < 90:
        score -= 10
    elif wpm > 180:
        score -= 15

    # Penalise for excessive pauses
    if pauses > 10:
        score -= 20
    elif pauses > 5:
        score -= 10

    # Penalise for long silence stretches
    if silence_ratio > 0.5:
        score -= 15
    elif silence_ratio > 0.3:
        score -= 8

    # Reward richer vocabulary/longer speech
    if word_count > 60:
        score += 5

    return max(0, min(100, score))


def _fluency_score_without_transcript(pauses, silence_ratio, duration_sec):
    score = 82
    if pauses > 20:
        score -= 25
    elif pauses > 10:
        score -= 15
    elif pauses > 5:
        score -= 8

    if silence_ratio > 0.55:
        score -= 20
    elif silence_ratio > 0.35:
        score -= 10

    if duration_sec < 5:
        score -= 10
    return max(0, min(100, round(score)))


def _analyze_with_soundfile(audio_path, reason=""):
    """Fallback audio analysis that avoids librosa/numba dependency issues."""
    try:
        import numpy as np
        import soundfile as sf

        y, sr = sf.read(audio_path, always_2d=False)
        if getattr(y, "ndim", 1) > 1:
            y = y.mean(axis=1)
        duration_sec = len(y) / float(sr or 1)

        if len(y) == 0:
            return _empty_audio_result("Audio file could not be decoded.")

        frame_length = max(512, int((sr or 16000) * 0.05))
        hop = frame_length
        frame_count = max(1, len(y) // hop)
        rms = []
        for idx in range(frame_count):
            frame = y[idx * hop : idx * hop + frame_length]
            if len(frame) == 0:
                continue
            rms.append(float(np.sqrt(np.mean(np.square(frame)))))

        if not rms:
            return _empty_audio_result("Audio file had no readable frames.")

        rms = np.array(rms)
        threshold = max(float(np.percentile(rms, 20)), 1e-6)
        is_silent = rms <= threshold
        silence_ratio = float(np.mean(is_silent))
        transitions = np.diff(is_silent.astype(int))
        pause_count = int(np.sum(transitions == 1))

        transcript = _transcribe(audio_path)
        words = transcript.split()
        word_count = len(words)
        speech_sec = max(1.0, duration_sec * (1 - silence_ratio))
        wpm = round(word_count / (speech_sec / 60)) if word_count else 0

        if word_count:
            fluency = _fluency_score(wpm, pause_count, silence_ratio, word_count)
            summary = _fluency_summary(fluency, wpm, pause_count)
        else:
            fluency = _fluency_score_without_transcript(pause_count, silence_ratio, duration_sec)
            summary = (
                f"Audio decoded successfully ({duration_sec:.1f}s) with {pause_count} pause(s). "
                "Transcript unavailable, so fluency is estimated from silence and pause patterns."
            )

        if reason:
            print(f"[Audio] Used soundfile fallback because librosa failed: {reason}")

        return {
            "transcript": transcript,
            "audio_duration_seconds": round(duration_sec, 1),
            "word_count": word_count,
            "words_per_minute": wpm,
            "pause_count": pause_count,
            "fluency_score": fluency,
            "speech_summary": summary,
        }
    except Exception as e:
        print(f"[Audio] Fallback analysis failed: {e}.")
        return _empty_audio_result(f"Audio analysis failed: {e}")


def _fluency_summary(score, wpm, pauses):
    if score >= 85:
        return f"Excellent speech clarity at {wpm} WPM with minimal pauses."
    elif score >= 70:
        return f"Clear speech at {wpm} WPM with {pauses} noticeable pause(s)."
    elif score >= 50:
        return f"Moderate fluency. Speech rate is {wpm} WPM with {pauses} pause(s)."
    else:
        return "Low fluency detected — consider speech exercises and practice reading aloud."


def _empty_audio_result(reason="No audio data provided yet."):
    return {
        "transcript":               "",
        "audio_duration_seconds":   0,
        "word_count":               0,
        "words_per_minute":         0,
        "pause_count":              0,
        "fluency_score":            0,
        "speech_summary":           reason
    }


if __name__ == "__main__":
    import json
    result = analyze_audio("../data/audio/sample_audio.wav")
    print(json.dumps(result, indent=2))
