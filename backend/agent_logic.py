# agent_logic.py

def generate_suggestions(
    cognitive_load,
    tasks=None,
    stress=None,
    sleep=None,
    deadline=None,
    posture=None
):
    """
    Dynamic Agentic AI workflow for FlowMind.
    Stress comes from PSS converted score.
    Sleep comes from PSQI converted score.
    """

    tasks = tasks if tasks is not None else 6
    stress = float(stress) if stress is not None else 5
    sleep = float(sleep) if sleep is not None else 6
    deadline = float(deadline) if deadline is not None else 5
    posture = float(posture) if posture is not None else 5

    if cognitive_load >= 75:
        cogload_msg = "🧠 CogLoad Agent: High overload detected"
    elif cognitive_load >= 45:
        cogload_msg = "🧠 CogLoad Agent: Moderate cognitive load detected"
    else:
        cogload_msg = "🧠 CogLoad Agent: Workload is currently manageable"

    if stress >= 8 or cognitive_load >= 75:
        intent_msg = "🎯 Intent Agent: Recovery-first workflow recommended due to high PSS-based stress or overload"
    elif deadline >= 7:
        intent_msg = "🎯 Intent Agent: Deadline-focused work mode selected"
    else:
        intent_msg = "🎯 Intent Agent: Deep focus mode recommended"

    if tasks >= 9:
        task_msg = "📅 Planner Agent: Too many tasks found, prioritizing urgent work"
    elif deadline >= 7:
        task_msg = "📅 Planner Agent: High-deadline tasks moved to top priority"
    else:
        task_msg = "📅 Planner Agent: Current task flow is balanced"

    if sleep <= 4:
        empathy_msg = "💬 Recovery Agent: Poor PSQI-based sleep quality detected, take a short recovery break"
    elif stress >= 7:
        empathy_msg = "💬 Recovery Agent: PSS-based stress is high, avoid multitasking"
    elif posture <= 5:
        empathy_msg = "💬 Recovery Agent: Posture risk detected, adjust sitting position"
    else:
        empathy_msg = "💬 Recovery Agent: Maintain focus with short micro-breaks"

    if cognitive_load >= 75:
        reflection_msg = "🔁 Reflection Agent: Overload pattern logged for future warning"
    elif cognitive_load >= 45:
        reflection_msg = "🔁 Reflection Agent: Moderate load session recorded"
    else:
        reflection_msg = "🔁 Reflection Agent: Healthy workload pattern recorded"

    timeline = [
        cogload_msg,
        intent_msg,
        task_msg,
        empathy_msg,
        reflection_msg
    ]

    if cognitive_load >= 75:
        suggestion = (
            "You are overloaded. Start with urgent tasks, take a short break, "
            "reduce multitasking, and correct posture."
        )

        plan = [
            "✅ Complete only the top urgent task first",
            "✅ Take a 10-minute recovery break",
            "✅ Avoid multitasking for the next focus block",
            "✅ Shift low-priority tasks to later",
            "✅ Adjust posture using webcam feedback"
        ]

        if sleep <= 4:
            plan.append("✅ Keep the next work block short because PSQI-based sleep quality is poor")

        if stress >= 8:
            plan.append("✅ Use a calm 25-minute focus session because PSS-based stress is high")

    elif cognitive_load >= 45:
        suggestion = (
            "Workload is moderate. Continue working, but avoid multitasking, "
            "watch posture, and take short breaks."
        )

        plan = [
            "✅ Complete important tasks first",
            "✅ Take a 5-minute break after one focus block",
            "✅ Prioritize high-impact work",
            "✅ Check posture before continuing"
        ]

        if deadline >= 7:
            plan.append("✅ Finish deadline-based work before optional tasks")

        if stress >= 7:
            plan.append("✅ Reduce multitasking because PSS-based stress is high")

        if sleep <= 5:
            plan.append("✅ Add a recovery break because PSQI-based sleep quality is low")

    else:
        suggestion = (
            "Workload is manageable. Continue your current plan and maintain good posture."
        )

        plan = [
            "✅ Continue current tasks",
            "✅ Maintain good posture",
            "✅ Take mini-breaks when needed",
            "✅ Keep the same focus rhythm"
        ]

    return suggestion, timeline, plan