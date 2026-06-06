# explainability.py

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def calculate_behavioral_risk(
    typing_speed=0,
    backspace_count=0,
    idle_time=0,
    mouse_activity=0,
    behavioral_load_score=0
):
    typing_speed = clamp(float(typing_speed), 0, 100)
    backspace_count = clamp(int(backspace_count), 0, 100)
    idle_time = clamp(int(idle_time), 0, 300)
    mouse_activity = clamp(int(mouse_activity), 0, 500)
    behavioral_load_score = clamp(float(behavioral_load_score), 0, 100)

    if behavioral_load_score > 0:
        return behavioral_load_score / 10

    risk = 0

    if typing_speed == 0:
        risk += 1
    elif typing_speed < 15:
        risk += 3
    elif typing_speed < 25:
        risk += 2

    if backspace_count >= 30:
        risk += 3
    elif backspace_count >= 15:
        risk += 2
    elif backspace_count >= 5:
        risk += 1

    if idle_time >= 60:
        risk += 3
    elif idle_time >= 30:
        risk += 2
    elif idle_time >= 15:
        risk += 1

    if mouse_activity >= 250:
        risk += 1
    elif mouse_activity >= 120:
        risk += 0.5

    return clamp(risk, 0, 10)


def explain_load(
    tasks: int,
    stress: float,
    sleep: float,
    deadline: int,
    webcam_posture: int = 5,
    typing_speed: float = 0,
    backspace_count: int = 0,
    idle_time: int = 0,
    mouse_activity: int = 0,
    behavioral_load_score: float = 0
):
    """
    Explainable AI logic for FlowMind.
    Stress comes from PSS converted score.
    Sleep comes from PSQI converted score.
    """

    task_risk = clamp(float(tasks), 0, 12) / 12 * 10

    # PSS-based stress risk
    stress_risk = clamp(float(stress), 0, 10)

    # PSQI-based sleep risk: lower converted sleep score means higher risk
    sleep_risk = max(0, 10 - clamp(float(sleep), 0, 10))

    deadline_risk = clamp(float(deadline), 0, 10)

    posture_risk = max(0, 10 - clamp(float(webcam_posture), 0, 10))

    behavior_risk = calculate_behavioral_risk(
        typing_speed=typing_speed,
        backspace_count=backspace_count,
        idle_time=idle_time,
        mouse_activity=mouse_activity,
        behavioral_load_score=behavioral_load_score
    )

    weights = {
        "tasks": 0.22,
        "stress": 0.22,
        "sleep": 0.16,
        "deadline": 0.18,
        "posture": 0.10,
        "behavior": 0.12
    }

    weighted_scores = {
        "tasks": task_risk * weights["tasks"],
        "stress": stress_risk * weights["stress"],
        "sleep": sleep_risk * weights["sleep"],
        "deadline": deadline_risk * weights["deadline"],
        "posture": posture_risk * weights["posture"],
        "behavior": behavior_risk * weights["behavior"]
    }

    total_score = sum(weighted_scores.values())

    if total_score == 0:
        contributions = {
            "tasks": 0,
            "stress": 0,
            "sleep": 0,
            "deadline": 0,
            "posture": 0,
            "behavior": 0
        }
    else:
        contributions = {
            factor: round((score / total_score) * 100, 2)
            for factor, score in weighted_scores.items()
        }

    top_factor = max(contributions, key=contributions.get)

    explanation_text = generate_explanation_text(top_factor, contributions)

    return {
        "contributions": contributions,
        "top_factor": top_factor,
        "explanation": explanation_text,
        "behaviorDetails": {
            "typingSpeed": typing_speed,
            "backspaceCount": backspace_count,
            "idleTime": idle_time,
            "mouseActivity": mouse_activity,
            "behavioralLoadScore": behavioral_load_score,
            "behaviorRisk": round(behavior_risk, 2)
        }
    }


def generate_explanation_text(top_factor: str, contributions: dict):
    factor_names = {
        "tasks": "too many tasks",
        "stress": "high PSS-based perceived stress",
        "sleep": "poor PSQI-based sleep quality",
        "deadline": "high deadline pressure",
        "posture": "poor ergonomic posture",
        "behavior": "behavioral signs such as hesitation, corrections, idle time, or restless activity"
    }

    display_names = {
        "tasks": "Tasks",
        "stress": "PSS Stress",
        "sleep": "PSQI Sleep",
        "deadline": "Deadline",
        "posture": "Posture",
        "behavior": "Behavior"
    }

    main_reason = factor_names.get(top_factor, "multiple factors")
    display_factor = display_names.get(top_factor, top_factor)

    return (
        f"Your cognitive load is mainly affected by {main_reason}. "
        f"The highest contribution is from {display_factor} "
        f"with {contributions[top_factor]}% impact."
    )