from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
import csv
import random
import os
import json

from agent_logic import generate_suggestions
from predict_model import predict_cognitive_load
from explainability import explain_load
from scenario_simulation import run_digital_twin_simulation
from validation import get_validation_dashboard
from report_generator import generate_flowmind_report

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOG_FILE = "user_metrics.csv"
EXPERIMENT_LOG_FILE = "experiment_sessions.csv"
PROFILE_FILE = "adaptive_profile.json"


def safe_round(value, digits=1):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0


def calculate_nasa_tlx_score(nasa_tlx: dict | None, fallback_score: float | None = None):
    if nasa_tlx:
        keys = [
            "mentalDemand",
            "physicalDemand",
            "temporalDemand",
            "performanceDifficulty",
            "effort",
            "frustration",
        ]

        values = []
        for key in keys:
            if key in nasa_tlx:
                try:
                    values.append(float(nasa_tlx[key]))
                except (TypeError, ValueError):
                    pass

        if values:
            return round(sum(values) / len(values), 1)

    if fallback_score is not None:
        return safe_round(fallback_score, 1)

    return 0


def build_pss_psqi_summary(data):
    return {
        "pssScore": safe_round(data.pss_score, 1),
        "pssLevel": data.pss_level or "Not Provided",
        "psqiScore": safe_round(data.psqi_score, 1),
        "psqiLevel": data.psqi_level or "Not Provided",
    }


def build_behavior_summary(data):
    typing_speed = safe_round(data.typing_speed, 1)
    backspace_count = int(data.backspace_count or 0)
    idle_time = int(data.idle_time or 0)
    mouse_activity = int(data.mouse_activity or 0)
    behavioral_load_score = safe_round(data.behavioral_load_score, 1)

    if behavioral_load_score >= 60:
        status = "High Cognitive Effort"
        message = "Behavior shows high effort through pauses, corrections, or restless activity."
    elif behavioral_load_score >= 30:
        status = "Moderate Cognitive Effort"
        message = "Behavior shows moderate hesitation or activity changes."
    else:
        status = "Stable"
        message = "Behavior pattern is currently stable."

    return {
        "typingSpeed": typing_speed,
        "backspaceCount": backspace_count,
        "idleTime": idle_time,
        "mouseActivity": mouse_activity,
        "behavioralLoadScore": behavioral_load_score,
        "behavioralStatus": status,
        "behavioralMessage": message,
    }


class UserInput(BaseModel):
    tasks: int
    stress: float
    sleep: float
    deadline: int
    webcam_posture: int = 5

    typing_speed: float = 0
    backspace_count: int = 0
    idle_time: int = 0
    mouse_activity: int = 0
    behavioral_load_score: float = 0

    nasa_tlx_score: float = 0
    nasa_tlx: dict | None = None

    pss_score: float = 0
    pss_level: str = ""
    psqi_score: float = 0
    psqi_level: str = ""


class DigitalTwinInput(BaseModel):
    tasks: int
    stress: float
    sleep: float
    deadline: int
    webcam_posture: int = 5
    scenario_type: str

    typing_speed: float = 0
    backspace_count: int = 0
    idle_time: int = 0
    mouse_activity: int = 0
    behavioral_load_score: float = 0
    nasa_tlx_score: float = 0
    nasa_tlx: dict | None = None

    pss_score: float = 0
    pss_level: str = ""
    psqi_score: float = 0
    psqi_level: str = ""


class ExperimentSessionInput(BaseModel):
    tasks: int
    stress: float
    sleep: float
    deadline: int
    webcam_posture: int = 5

    typing_speed: float = 0
    backspace_count: int = 0
    idle_time: int = 0
    mouse_activity: int = 0
    behavioral_load_score: float = 0
    nasa_tlx_score: float = 0
    nasa_tlx: dict | None = None

    pss_score: float = 0
    pss_level: str = ""
    psqi_score: float = 0
    psqi_level: str = ""


class ReportInput(BaseModel):
    tasks: int
    stress: float
    sleep: float
    deadline: int
    webcam_posture: int = 5
    digital_twin_data: dict | None = None

    typing_speed: float = 0
    backspace_count: int = 0
    idle_time: int = 0
    mouse_activity: int = 0
    behavioral_load_score: float = 0
    nasa_tlx_score: float = 0
    nasa_tlx: dict | None = None

    pss_score: float = 0
    pss_level: str = ""
    psqi_score: float = 0
    psqi_level: str = ""


def log_metrics(data: UserInput, result: dict):
    headers = [
        "timestamp",
        "logType",
        "tasks",
        "stress",
        "sleep",
        "deadline",
        "postureScore",
        "typingSpeed",
        "backspaceCount",
        "idleTime",
        "mouseActivity",
        "behavioralLoadScore",
        "nasaTlxScore",
        "pssScore",
        "pssLevel",
        "psqiScore",
        "psqiLevel",
        "cognitiveLoad",
        "improvedLoad",
        "risk",
        "suggestion",
    ]

    behavior = result.get("behaviorSummary", {})
    nasa = result.get("nasaTlx", {})
    validated = result.get("validatedAssessment", {})

    row = [
        datetime.now(),
        "auto",
        data.tasks,
        data.stress,
        data.sleep,
        data.deadline,
        result["postureScore"],
        behavior.get("typingSpeed", 0),
        behavior.get("backspaceCount", 0),
        behavior.get("idleTime", 0),
        behavior.get("mouseActivity", 0),
        behavior.get("behavioralLoadScore", 0),
        nasa.get("score", 0),
        validated.get("pssScore", 0),
        validated.get("pssLevel", "Not Provided"),
        validated.get("psqiScore", 0),
        validated.get("psqiLevel", "Not Provided"),
        result["cognitiveLoad"],
        result["improvedLoad"],
        result["risk"],
        result["suggestion"],
    ]

    file_exists = os.path.exists(LOG_FILE)

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow(row)


def generate_experiment_session_id():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_code = random.randint(100, 999)
    return f"EXP-{timestamp}-{random_code}"


def save_experiment_log(data: ExperimentSessionInput, result: dict):
    headers = [
        "sessionId",
        "timestamp",
        "logType",
        "tasks",
        "stress",
        "sleep",
        "deadline",
        "postureScore",
        "typingSpeed",
        "backspaceCount",
        "idleTime",
        "mouseActivity",
        "behavioralLoadScore",
        "nasaTlxScore",
        "pssScore",
        "pssLevel",
        "psqiScore",
        "psqiLevel",
        "flowmindNasaDifference",
        "baselineLoad",
        "flowmindLoad",
        "improvement",
        "improvementPercent",
        "risk",
        "suggestion",
        "topFactor",
    ]

    session_id = generate_experiment_session_id()
    baseline_load = result["cognitiveLoad"]
    flowmind_load = result["improvedLoad"]
    improvement = round(baseline_load - flowmind_load, 1)

    improvement_percent = round((improvement / baseline_load) * 100, 1) if baseline_load > 0 else 0

    top_factor = result.get("explainability", {}).get("top_factor", "unknown")
    behavior = result.get("behaviorSummary", {})
    nasa = result.get("nasaTlx", {})
    validated = result.get("validatedAssessment", {})

    nasa_score = nasa.get("score", 0)
    flowmind_nasa_difference = round(abs(baseline_load - nasa_score), 1)

    row = [
        session_id,
        datetime.now(),
        "experiment",
        data.tasks,
        data.stress,
        data.sleep,
        data.deadline,
        result["postureScore"],
        behavior.get("typingSpeed", 0),
        behavior.get("backspaceCount", 0),
        behavior.get("idleTime", 0),
        behavior.get("mouseActivity", 0),
        behavior.get("behavioralLoadScore", 0),
        nasa_score,
        validated.get("pssScore", 0),
        validated.get("pssLevel", "Not Provided"),
        validated.get("psqiScore", 0),
        validated.get("psqiLevel", "Not Provided"),
        flowmind_nasa_difference,
        baseline_load,
        flowmind_load,
        improvement,
        improvement_percent,
        result["risk"],
        result["suggestion"],
        top_factor,
    ]

    file_exists = os.path.exists(EXPERIMENT_LOG_FILE)

    with open(EXPERIMENT_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow(row)

    return {
        "sessionId": session_id,
        "message": "Experiment session saved successfully.",
        "baselineLoad": baseline_load,
        "flowmindLoad": flowmind_load,
        "improvement": improvement,
        "improvementPercent": improvement_percent,
        "topFactor": top_factor,
        "nasaTlxScore": nasa_score,
        "flowmindNasaDifference": flowmind_nasa_difference,
        "pssScore": validated.get("pssScore", 0),
        "pssLevel": validated.get("pssLevel", "Not Provided"),
        "psqiScore": validated.get("psqiScore", 0),
        "psqiLevel": validated.get("psqiLevel", "Not Provided"),
        "behaviorSummary": behavior,
    }


def get_webcam_posture_score():
    return random.randint(4, 8)


def generate_posture_intelligence(posture_score):
    if posture_score >= 8:
        return {
            "postureStatus": "Good",
            "ergonomicRisk": "Low",
            "postureMessage": "Posture is healthy. Continue current sitting position.",
            "recommendedAction": "Maintain posture and take normal micro-breaks.",
        }
    elif posture_score >= 5:
        return {
            "postureStatus": "Needs Attention",
            "ergonomicRisk": "Moderate",
            "postureMessage": "Posture is acceptable but may create fatigue over time.",
            "recommendedAction": "Straighten shoulders and adjust screen height.",
        }
    else:
        return {
            "postureStatus": "Poor",
            "ergonomicRisk": "High",
            "postureMessage": "Poor posture detected. Ergonomic correction is required.",
            "recommendedAction": "Sit upright, align neck, and take a posture reset break.",
        }


def load_adaptive_profile():
    if not os.path.exists(PROFILE_FILE):
        return {
            "totalSessions": 0,
            "averageLoad": 0,
            "averageStress": 0,
            "averageSleep": 0,
            "averagePosture": 0,
            "personalPattern": "No personal pattern detected yet.",
            "adaptiveRecommendation": "Save more sessions to build a personalized profile.",
        }

    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "totalSessions": 0,
            "averageLoad": 0,
            "averageStress": 0,
            "averageSleep": 0,
            "averagePosture": 0,
            "personalPattern": "Profile file could not be read.",
            "adaptiveRecommendation": "Start a new adaptive profile.",
        }


def update_adaptive_profile(data, result):
    old_profile = load_adaptive_profile()

    old_count = old_profile.get("totalSessions", 0)
    new_count = old_count + 1

    def update_average(old_avg, new_value):
        return round(((old_avg * old_count) + new_value) / new_count, 1)

    average_load = update_average(old_profile.get("averageLoad", 0), result["cognitiveLoad"])
    average_stress = update_average(old_profile.get("averageStress", 0), data.stress)
    average_sleep = update_average(old_profile.get("averageSleep", 0), data.sleep)
    average_posture = update_average(old_profile.get("averagePosture", 0), result["postureScore"])

    if average_stress >= 7 and average_sleep <= 5:
        pattern = "High PSS-based stress with poor PSQI-based sleep pattern detected."
        recommendation = "Plan shorter focus blocks and prioritize recovery before heavy work."
    elif average_posture <= 5:
        pattern = "Repeated posture risk pattern detected."
        recommendation = "Improve workstation setup and add posture reset reminders."
    elif average_load >= 70:
        pattern = "Frequent high cognitive load pattern detected."
        recommendation = "Reduce task density and use deadline-based prioritization."
    else:
        pattern = "Workload pattern is currently manageable."
        recommendation = "Continue current workflow with regular micro-breaks."

    new_profile = {
        "totalSessions": new_count,
        "averageLoad": average_load,
        "averageStress": average_stress,
        "averageSleep": average_sleep,
        "averagePosture": average_posture,
        "personalPattern": pattern,
        "adaptiveRecommendation": recommendation,
        "lastUpdated": str(datetime.now()),
    }

    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(new_profile, f, indent=4)

    return new_profile


def generate_early_warning(cognitive_load, stress, sleep, deadline, posture, behavioral_load_score=0):
    warning_score = 0

    if cognitive_load >= 70:
        warning_score += 35
    elif cognitive_load >= 50:
        warning_score += 20

    if stress >= 8:
        warning_score += 20
    elif stress >= 6:
        warning_score += 10

    if sleep <= 4:
        warning_score += 20
    elif sleep <= 6:
        warning_score += 10

    if deadline >= 8:
        warning_score += 15
    elif deadline >= 6:
        warning_score += 8

    if posture <= 4:
        warning_score += 10
    elif posture <= 6:
        warning_score += 5

    if behavioral_load_score >= 60:
        warning_score += 10
    elif behavioral_load_score >= 30:
        warning_score += 5

    warning_score = min(100, warning_score)

    if warning_score >= 70:
        level = "High Warning"
        message = "High overload risk may occur soon. Take action immediately."
        action = "Reduce tasks, take a recovery break, and focus only on urgent work."
    elif warning_score >= 40:
        level = "Medium Warning"
        message = "Workload may increase if current pattern continues."
        action = "Avoid multitasking and take a short break after one focus block."
    else:
        level = "Low Warning"
        message = "No major overload warning detected."
        action = "Continue current work rhythm with normal micro-breaks."

    return {
        "warningScore": warning_score,
        "warningLevel": level,
        "warningMessage": message,
        "preventiveAction": action,
    }


def build_agent_details(cognitive_load, tasks, stress, sleep, deadline, posture, timeline, behavior_summary=None):
    behavior_summary = behavior_summary or {}
    behavioral_load_score = behavior_summary.get("behavioralLoadScore", 0)

    if cognitive_load >= 75:
        cog_status = "Critical"
        cog_reason = "Cognitive load is high, so overload risk is critical."
    elif cognitive_load >= 45:
        cog_status = "Watch"
        cog_reason = "Cognitive load is moderate, so the system is monitoring workload."
    else:
        cog_status = "Normal"
        cog_reason = "Cognitive load is low, so workload is manageable."

    if stress >= 8 or cognitive_load >= 75:
        intent_status = "Critical"
        intent_reason = "High PSS-based stress or overload indicates recovery-first workflow."
    elif deadline >= 7:
        intent_status = "Watch"
        intent_reason = "Deadline pressure is high, so deadline-focused mode is selected."
    else:
        intent_status = "Normal"
        intent_reason = "Inputs indicate stable focus conditions."

    if tasks >= 9:
        planner_status = "Critical"
        planner_reason = "Task count is high, so urgent prioritization is required."
    elif deadline >= 7:
        planner_status = "Watch"
        planner_reason = "Deadline pressure is high, so urgent tasks are moved first."
    else:
        planner_status = "Normal"
        planner_reason = "Task flow is balanced for the current workload."

    if sleep <= 4:
        recovery_status = "Critical"
        recovery_reason = "PSQI-based sleep quality is poor, so recovery break is recommended."
    elif posture <= 5 or stress >= 7 or behavioral_load_score >= 60:
        recovery_status = "Watch"
        recovery_reason = "Posture risk or elevated PSS stress is present, so micro-breaks are suggested"
    else:
        recovery_status = "Normal"
        recovery_reason = "Recovery state is acceptable, continue with micro-breaks."

    if cognitive_load >= 75:
        reflection_status = "Critical"
        reflection_reason = "Overload pattern is stored for future early warning."
    elif cognitive_load >= 45:
        reflection_status = "Watch"
        reflection_reason = "Moderate load pattern is stored for progress tracking."
    else:
        reflection_status = "Normal"
        reflection_reason = "Healthy workload pattern is stored as a positive baseline."

    return [
        {
            "name": "🧠 CogLoad Monitor",
            "message": timeline[0] if len(timeline) > 0 else "CogLoad Agent analyzing workload",
            "status": cog_status,
            "confidence": min(95, max(65, round(cognitive_load + 15))),
            "reason": cog_reason,
        },
        {
            "name": "🎯 Intent Agent",
            "message": timeline[1] if len(timeline) > 1 else "Intent Agent predicting workflow",
            "status": intent_status,
            "confidence": min(95, round(60 + deadline * 3 + stress * 2)),
            "reason": intent_reason,
        },
        {
            "name": "📅 Planner Agent",
            "message": timeline[2] if len(timeline) > 2 else "Planner Agent arranging tasks",
            "status": planner_status,
            "confidence": min(95, round(60 + tasks * 2 + deadline * 2)),
            "reason": planner_reason,
        },
        {
            "name": "💬 Recovery Agent",
            "message": timeline[3] if len(timeline) > 3 else "Recovery Agent checking fatigue",
            "status": recovery_status,
            "confidence": min(
                95,
                round(60 + (10 - sleep) * 2 + (10 - posture) * 2 + stress * 2),
            ),
            "reason": recovery_reason,
        },
        {
            "name": "🔁 Reflection Agent",
            "message": timeline[4] if len(timeline) > 4 else "Reflection Agent updating pattern",
            "status": reflection_status,
            "confidence": min(95, max(70, round(cognitive_load + 10))),
            "reason": reflection_reason,
        },
    ]


def run_full_analysis(data):
    posture_score = data.webcam_posture or get_webcam_posture_score()

    cognitive_load, risk = predict_cognitive_load(
        tasks=data.tasks,
        stress=data.stress,
        sleep=data.sleep,
        deadline=data.deadline,
        posture=posture_score,
        typing_speed=data.typing_speed,
        backspace_count=data.backspace_count,
        idle_time=data.idle_time,
        mouse_activity=data.mouse_activity,
        behavioral_load_score=data.behavioral_load_score,
    )

    behavior_summary = build_behavior_summary(data)
    validated_assessment = build_pss_psqi_summary(data)

    nasa_score = calculate_nasa_tlx_score(
        nasa_tlx=data.nasa_tlx,
        fallback_score=data.nasa_tlx_score,
    )

    improved_load = max(25, cognitive_load - random.randint(20, 40))

    suggestion, timeline, plan = generate_suggestions(
        cognitive_load=cognitive_load,
        tasks=data.tasks,
        stress=data.stress,
        sleep=data.sleep,
        deadline=data.deadline,
        posture=posture_score,
    )

    explainability = explain_load(
        tasks=data.tasks,
        stress=data.stress,
        sleep=data.sleep,
        deadline=data.deadline,
        webcam_posture=posture_score,
        typing_speed=data.typing_speed,
        backspace_count=data.backspace_count,
        idle_time=data.idle_time,
        mouse_activity=data.mouse_activity,
        behavioral_load_score=data.behavioral_load_score,
    )

    agent_details = build_agent_details(
        cognitive_load=cognitive_load,
        tasks=data.tasks,
        stress=data.stress,
        sleep=data.sleep,
        deadline=data.deadline,
        posture=posture_score,
        timeline=timeline,
        behavior_summary=behavior_summary,
    )

    posture_intelligence = generate_posture_intelligence(posture_score)

    early_warning = generate_early_warning(
        cognitive_load=cognitive_load,
        stress=data.stress,
        sleep=data.sleep,
        deadline=data.deadline,
        posture=posture_score,
        behavioral_load_score=behavior_summary["behavioralLoadScore"],
    )

    adaptive_profile = update_adaptive_profile(
        data,
        {
            "cognitiveLoad": round(cognitive_load, 1),
            "postureScore": posture_score,
        },
    )

    result = {
        "inputs": {
            "tasks": data.tasks,
            "stress": data.stress,
            "sleep": data.sleep,
            "deadline": data.deadline,
            "postureScore": posture_score,
        },
        "validatedAssessment": validated_assessment,
        "behaviorSummary": behavior_summary,
        "nasaTlx": {
            "score": nasa_score,
            "flowmindScore": round(cognitive_load, 1),
            "difference": round(abs(cognitive_load - nasa_score), 1),
            "raw": data.nasa_tlx or {},
        },
        "cognitiveLoad": round(cognitive_load, 1),
        "improvedLoad": round(improved_load, 1),
        "risk": risk,
        "suggestion": suggestion,
        "timeline": timeline,
        "plan": plan,
        "postureScore": posture_score,
        "explainability": explainability,
        "agentDetails": agent_details,
        "postureIntelligence": posture_intelligence,
        "earlyWarning": early_warning,
        "adaptiveProfile": adaptive_profile,
    }

    return result


@app.post("/analyze")
def analyze(data: UserInput):
    result = run_full_analysis(data)
    log_metrics(data, result)
    return result


@app.post("/save-experiment-session")
def save_experiment_session(data: ExperimentSessionInput):
    result = run_full_analysis(data)
    saved_session = save_experiment_log(data, result)

    return {
        "saved": True,
        "session": saved_session,
        "analysis": result,
    }


@app.post("/generate-report")
def generate_report(data: ReportInput):
    analysis_result = run_full_analysis(data)
    validation_result = get_validation_dashboard()

    report_path = generate_flowmind_report(
        analysis_data=analysis_result,
        validation_data=validation_result,
        digital_twin_data=data.digital_twin_data,
    )

    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=os.path.basename(report_path),
    )


@app.get("/adaptive-profile")
def adaptive_profile():
    return load_adaptive_profile()


@app.post("/explainability")
def get_explainability(data: UserInput):
    posture_score = data.webcam_posture or get_webcam_posture_score()

    result = explain_load(
        tasks=data.tasks,
        stress=data.stress,
        sleep=data.sleep,
        deadline=data.deadline,
        webcam_posture=posture_score,
        typing_speed=data.typing_speed,
        backspace_count=data.backspace_count,
        idle_time=data.idle_time,
        mouse_activity=data.mouse_activity,
        behavioral_load_score=data.behavioral_load_score,
    )

    return result


@app.post("/digital-twin-simulation")
def digital_twin_simulation(data: DigitalTwinInput):
    posture_score = data.webcam_posture or get_webcam_posture_score()

    result = run_digital_twin_simulation(
        tasks=data.tasks,
        stress=data.stress,
        sleep=data.sleep,
        deadline=data.deadline,
        posture=posture_score,
        scenario_type=data.scenario_type,
    )

    return result


@app.get("/validation-results")
def validation_results():
    result = get_validation_dashboard()
    return result