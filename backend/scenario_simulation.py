# scenario_simulation.py

import random
from agent_logic import generate_suggestions
from predict_model import predict_cognitive_load


def run_digital_twin_simulation(
    tasks,
    stress,
    sleep,
    deadline,
    posture,
    scenario_type
):
    current_load, current_risk = predict_cognitive_load(
        tasks=tasks,
        stress=stress,
        sleep=sleep,
        deadline=deadline,
        posture=posture
    )

    simulated_tasks = tasks
    simulated_stress = float(stress)
    simulated_sleep = float(sleep)
    simulated_deadline = deadline
    simulated_posture = posture

    action = "No change applied"

    if scenario_type == "improve_sleep":
        simulated_sleep = min(10, max(float(sleep), 8))
        action = "Improve PSQI-based sleep quality score to at least 8/10"

    elif scenario_type == "reduce_stress":
        simulated_stress = max(1, round(float(stress) * 0.7, 1))
        action = "Reduce PSS-based stress by 30%"

    elif scenario_type == "improve_posture":
        simulated_posture = min(10, max(posture + 3, 8))
        action = "Improve ergonomic posture score"

    elif scenario_type == "reduce_tasks":
        simulated_tasks = max(1, round(tasks * 0.7))
        action = "Reduce task load by 30%"

    elif scenario_type == "balanced_recovery":
        simulated_sleep = min(10, max(float(sleep), 8))
        simulated_stress = max(1, round(float(stress) * 0.7, 1))
        simulated_posture = min(10, max(posture + 3, 8))
        simulated_tasks = max(1, round(tasks * 0.8))
        action = (
            "Balanced recovery plan: improve PSQI-based sleep quality, "
            "reduce PSS-based stress, improve posture, and reduce tasks"
        )

    predicted_load, predicted_risk = predict_cognitive_load(
        tasks=simulated_tasks,
        stress=simulated_stress,
        sleep=simulated_sleep,
        deadline=simulated_deadline,
        posture=simulated_posture
    )

    improvement = round(current_load - predicted_load, 1)

    if improvement > 15:
        impact = "High positive impact"
    elif improvement > 5:
        impact = "Moderate positive impact"
    elif improvement > 0:
        impact = "Small positive impact"
    else:
        impact = "No major improvement"

    return {
        "scenario": scenario_type,
        "action": action,
        "currentLoad": round(current_load, 1),
        "predictedLoad": round(predicted_load, 1),
        "improvement": improvement,
        "currentRisk": current_risk,
        "predictedRisk": predicted_risk,
        "impact": impact,
        "simulatedInputs": {
            "tasks": simulated_tasks,
            "stress": simulated_stress,
            "sleep": simulated_sleep,
            "deadline": simulated_deadline,
            "posture": simulated_posture
        }
    }


def generate_synthetic_data(n=1000):
    data_list = []

    for _ in range(n):
        tasks = random.randint(1, 12)

        # Stress and sleep support decimal values because frontend converts PSS/PSQI to 1-10 scale
        stress = round(random.uniform(1, 10), 1)
        sleep = round(random.uniform(1, 10), 1)

        deadline = random.randint(1, 10)
        webcam_posture = random.randint(3, 10)

        cognitive_load, risk = predict_cognitive_load(
            tasks=tasks,
            stress=stress,
            sleep=sleep,
            deadline=deadline,
            posture=webcam_posture
        )

        suggestion, timeline, plan = generate_suggestions(
            cognitive_load=cognitive_load,
            tasks=tasks,
            stress=stress,
            sleep=sleep,
            deadline=deadline,
            posture=webcam_posture
        )

        data_list.append({
            "tasks": tasks,
            "stress": stress,
            "sleep": sleep,
            "deadline": deadline,
            "posture": webcam_posture,
            "cognitiveLoad": round(cognitive_load, 1),
            "risk": risk,
            "suggestion": suggestion,
            "timeline": timeline,
            "plan": plan
        })

    return data_list


if __name__ == "__main__":
    data = generate_synthetic_data(1000)
    print(f"Generated {len(data)} synthetic user scenarios for validation.")

    test_simulation = run_digital_twin_simulation(
        tasks=8,
        stress=8.2,
        sleep=4.5,
        deadline=8,
        posture=5,
        scenario_type="balanced_recovery"
    )

    print(test_simulation)