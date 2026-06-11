def analyze_activity(activity_data):
    """
    Analyzes the activity_log.json to determine quiz scores, strong/weak concepts,
    and canvas interactions.
    """
    print("Analyzing activity data...")
    if not activity_data:
        return {}
        
    quiz_data = activity_data.get('quiz', [])
    total_questions = len(quiz_data)
    correct_answers = sum(1 for q in quiz_data if q.get('correct'))
    score_percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    concepts = {}
    for q in quiz_data:
        concept = q.get('concept')
        is_correct = q.get('correct')
        if concept not in concepts:
            concepts[concept] = {'total': 0, 'correct': 0}
        concepts[concept]['total'] += 1
        if is_correct:
            concepts[concept]['correct'] += 1
            
    strong_concepts = []
    weak_concepts = []
    
    for concept, stats in concepts.items():
        accuracy = stats['correct'] / stats['total']
        if accuracy >= 0.7:
            strong_concepts.append(concept)
        else:
            weak_concepts.append(concept)
            
    canvas_data = activity_data.get('canvas', {})
    canvas_completion = canvas_data.get('completion_percentage', 0)
    
    return {
        "quiz_score_percentage": score_percentage,
        "strong_concepts": strong_concepts,
        "weak_concepts": weak_concepts,
        "canvas_completion_percentage": canvas_completion,
        "total_time_taken_seconds": sum(q.get('time_taken_seconds', 0) for q in quiz_data) + canvas_data.get('time_taken_seconds', 0)
    }

def analyze_attendance(attendance_data):
    """
    Analyzes attendance.json to determine rate, streaks, and missed classes.
    """
    print("Analyzing attendance data...")
    if not attendance_data:
        return {}
        
    records = attendance_data.get('attendance', [])
    if not records:
        return {}
        
    total_classes = len(records)
    classes_attended = sum(1 for r in records if r.get('present'))
    attendance_rate = (classes_attended / total_classes * 100) if total_classes > 0 else 0
    
    # Calculate current streak (working backward from the most recent class)
    streak = 0
    for r in reversed(records):
        if r.get('present'):
            streak += 1
        else:
            break
            
    return {
        "attendance_rate": attendance_rate,
        "current_streak": streak,
        "missed_classes": total_classes - classes_attended,
        "weekly_consistency_summary": "Consistent attendance." if attendance_rate > 80 else "Needs improvement in attendance."
    }

if __name__ == "__main__":
    from ingest import load_data
    data = load_data("../data")
    print("Activity:", analyze_activity(data.get('activity')))
    print("Attendance:", analyze_attendance(data.get('attendance')))
