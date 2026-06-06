# report_generator.py
# Dependency-free PDF generator for FlowMind
# No fpdf installation needed

import os
from datetime import datetime


REPORT_DIR = "reports"


def clean_text(value):
    """
    Make text safe for simple PDF generation.
    Removes emojis and special unicode characters.
    """
    if value is None:
        return "N/A"

    text = str(value)

    replacements = {
        "✅": "[OK]",
        "🧠": "",
        "🎯": "",
        "📅": "",
        "💬": "",
        "🔁": "",
        "²": "2",
        "–": "-",
        "—": "-",
        "“": '"',
        "”": '"',
        "’": "'",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.encode("latin-1", "ignore").decode("latin-1")


def escape_pdf_text(text):
    """
    Escape characters that break PDF text format.
    """
    text = clean_text(text)
    text = text.replace("\\", "\\\\")
    text = text.replace("(", "\\(")
    text = text.replace(")", "\\)")
    return text


def wrap_text(text, width=85):
    """
    Simple text wrapping for PDF lines.
    """
    text = clean_text(text)
    words = text.split()
    lines = []
    current = ""

    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines if lines else [""]


class SimplePDF:
    def __init__(self):
        self.lines = []
        self.page_width = 595
        self.page_height = 842
        self.margin_left = 50
        self.start_y = 790
        self.line_height = 16

    def add_title(self, title):
        self.lines.append(("TITLE", clean_text(title)))

    def add_heading(self, heading):
        self.lines.append(("HEADING", clean_text(heading)))

    def add_text(self, text):
        for line in wrap_text(text):
            self.lines.append(("TEXT", line))

    def add_key_value(self, key, value):
        text = f"{key}: {value}"
        self.add_text(text)

    def add_blank(self):
        self.lines.append(("BLANK", ""))

    def build_pdf_content(self):
        content = []
        y = self.start_y

        content.append("BT")

        for line_type, text in self.lines:
            if y < 60:
                y = 60

            if line_type == "TITLE":
                content.append("/F1 18 Tf")
                content.append(f"70 {y} Td")
                content.append(f"({escape_pdf_text(text)}) Tj")
                content.append(f"-70 -{self.line_height + 8} Td")
                y -= self.line_height + 8

            elif line_type == "HEADING":
                content.append("/F1 13 Tf")
                content.append(f"0 -{self.line_height + 6} Td")
                content.append(f"({escape_pdf_text(text)}) Tj")
                y -= self.line_height + 6

            elif line_type == "TEXT":
                content.append("/F2 10 Tf")
                content.append(f"0 -{self.line_height} Td")
                content.append(f"({escape_pdf_text(text)}) Tj")
                y -= self.line_height

            elif line_type == "BLANK":
                content.append(f"0 -{self.line_height} Td")
                y -= self.line_height

        content.append("ET")
        return "\n".join(content)

    def output(self, output_path):
        page_content = self.build_pdf_content()
        content_bytes = page_content.encode("latin-1", errors="ignore")

        objects = []

        objects.append(
            b"<< /Type /Catalog /Pages 2 0 R >>"
        )

        objects.append(
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        )

        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> "
            b"/Contents 6 0 R >>"
        )

        objects.append(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
        )

        objects.append(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        )

        objects.append(
            f"<< /Length {len(content_bytes)} >>\nstream\n".encode("latin-1")
            + content_bytes
            + b"\nendstream"
        )

        pdf = b"%PDF-1.4\n"
        offsets = [0]

        for i, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf += f"{i} 0 obj\n".encode("latin-1")
            pdf += obj
            pdf += b"\nendobj\n"

        xref_start = len(pdf)
        pdf += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
        pdf += b"0000000000 65535 f \n"

        for offset in offsets[1:]:
            pdf += f"{offset:010d} 00000 n \n".encode("latin-1")

        pdf += (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF"
        ).encode("latin-1")

        with open(output_path, "wb") as f:
            f.write(pdf)

        return output_path


def generate_flowmind_report(analysis_data, validation_data=None, digital_twin_data=None):
    """
    Creates a simple PDF report without external libraries.
    This function is used by main.py /generate-report endpoint.
    """

    validation_data = validation_data or {}
    digital_twin_data = digital_twin_data or {}

    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(REPORT_DIR, f"FlowMind_Report_{timestamp}.pdf")

    pdf = SimplePDF()

    pdf.add_title("FlowMind Cognitive Load Report")
    pdf.add_text(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    pdf.add_blank()

    # User Inputs
    pdf.add_heading("1. User Input Summary")
    inputs = analysis_data.get("inputs", {})
    pdf.add_key_value("Tasks", inputs.get("tasks", "N/A"))
    pdf.add_key_value("Stress", inputs.get("stress", "N/A"))
    pdf.add_key_value("Sleep", inputs.get("sleep", "N/A"))
    pdf.add_key_value("Deadline", inputs.get("deadline", "N/A"))
    pdf.add_key_value("Webcam Ergonomic/Posture Score", inputs.get("postureScore", "N/A"))
    pdf.add_blank()

    # Cognitive Load
    pdf.add_heading("2. Cognitive Load Analysis")
    pdf.add_key_value("Cognitive Load", f"{analysis_data.get('cognitiveLoad', 'N/A')}%")
    pdf.add_key_value("FlowMind Optimized Load", f"{analysis_data.get('improvedLoad', 'N/A')}%")
    pdf.add_key_value("Risk Level", analysis_data.get("risk", "N/A"))
    pdf.add_key_value("AI Suggestion", analysis_data.get("suggestion", "N/A"))
    pdf.add_blank()

    # Behavioral Tracking
    pdf.add_heading("3. Real-Time Behavioral Tracking")
    behavior = analysis_data.get("behaviorSummary", {})
    pdf.add_key_value("Typing Speed", f"{behavior.get('typingSpeed', 'N/A')} WPM")
    pdf.add_key_value("Backspace Count", behavior.get("backspaceCount", "N/A"))
    pdf.add_key_value("Idle Time", f"{behavior.get('idleTime', 'N/A')} seconds")
    pdf.add_key_value("Mouse Activity", behavior.get("mouseActivity", "N/A"))
    pdf.add_key_value("Behavioral Load Score", f"{behavior.get('behavioralLoadScore', 'N/A')}%")
    pdf.add_key_value("Behavioral Status", behavior.get("behavioralStatus", "N/A"))
    pdf.add_key_value("Behavioral Message", behavior.get("behavioralMessage", "N/A"))
    pdf.add_text(
        "Behavioral features are used as indirect indicators of workload. "
        "They do not directly measure cognitive load, but show signs such as "
        "hesitation, correction frequency, idle time, and restless interaction."
    )
    pdf.add_blank()

    # NASA-TLX
    pdf.add_heading("4. NASA-TLX Workload Validation")
    nasa = analysis_data.get("nasaTlx", {})
    pdf.add_key_value("NASA-TLX Score", f"{nasa.get('score', 'N/A')}%")
    pdf.add_key_value("FlowMind Score", f"{nasa.get('flowmindScore', analysis_data.get('cognitiveLoad', 'N/A'))}%")
    pdf.add_key_value("FlowMind-NASA Difference", f"{nasa.get('difference', 'N/A')}%")
    pdf.add_text(
        "NASA-TLX is used as a subjective workload validation method. "
        "The user rates mental demand, physical demand, temporal demand, "
        "performance difficulty, effort, and frustration after task completion."
    )
    pdf.add_blank()

        # PSS and PSQI Validated Assessment
    pdf.add_heading("5. PSS and PSQI Validated Assessment")
    validated = analysis_data.get("validatedAssessment", {})

    pdf.add_key_value("PSS Stress Score", f"{validated.get('pssScore', 'N/A')}/40")
    pdf.add_key_value("PSS Stress Level", validated.get("pssLevel", "N/A"))
    pdf.add_key_value("PSQI Sleep Score", f"{validated.get('psqiScore', 'N/A')}/21")
    pdf.add_key_value("PSQI Sleep Quality", validated.get("psqiLevel", "N/A"))

    pdf.add_text(
        "PSS is used to estimate perceived stress, while PSQI is used to estimate "
        "sleep quality. These validated questionnaire-based scores are used as "
        "background risk factors for cognitive workload assessment."
    )
    pdf.add_blank()

    # Explainable AI
    pdf.add_heading("5. Explainable AI Breakdown")
    explainability = analysis_data.get("explainability", {})
    pdf.add_key_value("Explanation", explainability.get("explanation", "N/A"))
    pdf.add_key_value("Main Overload Driver", explainability.get("top_factor", "N/A"))

    contributions = explainability.get("contributions", {})
    for factor, value in contributions.items():
        pdf.add_key_value(factor.capitalize(), f"{value}%")

    behavior_details = explainability.get("behaviorDetails", {})
    if behavior_details:
        pdf.add_key_value("Behavior Risk", behavior_details.get("behaviorRisk", "N/A"))

    pdf.add_blank()

    # Agent Workflow
    pdf.add_heading("6. Agentic AI Workflow")
    agent_details = analysis_data.get("agentDetails", [])

    if agent_details:
        for agent in agent_details:
            pdf.add_text(f"Agent: {agent.get('name', 'Agent')}")
            pdf.add_key_value("Status", agent.get("status", "N/A"))
            pdf.add_key_value("Confidence", f"{agent.get('confidence', 0)}%")
            pdf.add_key_value("Message", agent.get("message", "N/A"))
            pdf.add_key_value("Reason", agent.get("reason", "N/A"))
            pdf.add_blank()
    else:
        pdf.add_text("No agent details available.")

    # Plan
    pdf.add_heading("7. Optimized Daily Plan")
    plan = analysis_data.get("plan", [])

    if plan:
        for item in plan:
            pdf.add_text(f"- {item}")
    else:
        pdf.add_text("No optimized plan available.")

    pdf.add_blank()

    # Webcam Intelligence
    pdf.add_heading("8. Webcam Ergonomic Intelligence")
    posture_info = analysis_data.get("postureIntelligence", {})
    pdf.add_key_value("Posture Status", posture_info.get("postureStatus", "N/A"))
    pdf.add_key_value("Ergonomic Risk", posture_info.get("ergonomicRisk", "N/A"))
    pdf.add_key_value("Message", posture_info.get("postureMessage", "N/A"))
    pdf.add_key_value("Recommended Action", posture_info.get("recommendedAction", "N/A"))
    pdf.add_text(
        "The webcam module estimates ergonomic posture using real-time visual signals. "
        "It supports cognitive load analysis by identifying possible physical strain or posture-related fatigue."
    )
    pdf.add_blank()

    # Early Warning
    pdf.add_heading("9. Early Overload Warning")
    warning = analysis_data.get("earlyWarning", {})
    pdf.add_key_value("Warning Score", f"{warning.get('warningScore', 'N/A')}%")
    pdf.add_key_value("Warning Level", warning.get("warningLevel", "N/A"))
    pdf.add_key_value("Warning Message", warning.get("warningMessage", "N/A"))
    pdf.add_key_value("Preventive Action", warning.get("preventiveAction", "N/A"))
    pdf.add_blank()

    # Adaptive Profile
    pdf.add_heading("10. Personal Adaptive Profile")
    profile = analysis_data.get("adaptiveProfile", {})
    pdf.add_key_value("Total Sessions", profile.get("totalSessions", "N/A"))
    pdf.add_key_value("Average Load", f"{profile.get('averageLoad', 'N/A')}%")
    pdf.add_key_value("Average Stress", profile.get("averageStress", "N/A"))
    pdf.add_key_value("Average Sleep", profile.get("averageSleep", "N/A"))
    pdf.add_key_value("Average Posture", profile.get("averagePosture", "N/A"))
    pdf.add_key_value("Personal Pattern", profile.get("personalPattern", "N/A"))
    pdf.add_key_value("Adaptive Recommendation", profile.get("adaptiveRecommendation", "N/A"))
    pdf.add_blank()

    # Digital Twin
    pdf.add_heading("11. Digital Twin What-if Simulation")

    if digital_twin_data:
        pdf.add_key_value("Current Load", f"{digital_twin_data.get('currentLoad', 'N/A')}%")
        pdf.add_key_value("Predicted Load", f"{digital_twin_data.get('predictedLoad', 'N/A')}%")
        pdf.add_key_value("Expected Improvement", f"{digital_twin_data.get('improvement', 'N/A')}%")
        pdf.add_key_value("Impact", digital_twin_data.get("impact", "N/A"))
        pdf.add_key_value("Recommended Action", digital_twin_data.get("action", "N/A"))
    else:
        pdf.add_text("No digital twin simulation selected.")

    pdf.add_blank()

    # Validation
    pdf.add_heading("12. Research Validation Summary")
    model_metrics = validation_data.get("modelMetrics", {})
    session_metrics = validation_data.get("sessionMetrics", {})
    auto_metrics = validation_data.get("autoLogMetrics", {})
    experiment_metrics = validation_data.get("experimentMetrics", {})

    pdf.add_key_value("Model RMSE", model_metrics.get("rmse", "N/A"))
    pdf.add_key_value("Model MAE", model_metrics.get("mae", "N/A"))
    pdf.add_key_value("R2 Score", model_metrics.get("r2Score", "N/A"))
    pdf.add_key_value("Valid Experiment Sessions", session_metrics.get("totalSessions", "N/A"))
    pdf.add_key_value("Auto Logs Ignored", auto_metrics.get("totalAutoLogs", "N/A"))
    pdf.add_key_value("Duplicate Sessions Ignored", experiment_metrics.get("duplicateSessionsIgnored", "N/A"))
    pdf.add_key_value("Baseline Average Load", f"{session_metrics.get('averageLoad', 'N/A')}%")
    pdf.add_key_value("FlowMind Average Load", f"{session_metrics.get('averageImprovedLoad', 'N/A')}%")
    pdf.add_key_value("Average Reduction", f"{session_metrics.get('averageImprovement', 'N/A')}%")
    pdf.add_key_value("Reduction Rate", f"{session_metrics.get('averageImprovementPercent', 'N/A')}%")
    pdf.add_blank()

    # NASA-TLX + Behavioral Validation Metrics
    pdf.add_heading("13. NASA-TLX and Behavioral Validation Metrics")
    pdf.add_key_value("Average NASA-TLX Score", f"{session_metrics.get('averageNasaTlxScore', 'N/A')}%")
    pdf.add_key_value("Average Behavioral Load", f"{session_metrics.get('averageBehavioralLoad', 'N/A')}%")
    pdf.add_key_value("Average FlowMind-NASA Difference", f"{session_metrics.get('averageFlowmindNasaDifference', 'N/A')}%")
    pdf.add_key_value("FlowMind vs NASA-TLX Correlation", session_metrics.get("flowmindNasaCorrelation", "N/A"))
    pdf.add_key_value("Behavioral Load vs NASA-TLX Correlation", session_metrics.get("behaviorNasaCorrelation", "N/A"))
    pdf.add_key_value("Idle Time vs NASA-TLX Correlation", session_metrics.get("idleNasaCorrelation", "N/A"))
    pdf.add_key_value("Backspace Count vs NASA-TLX Correlation", session_metrics.get("backspaceNasaCorrelation", "N/A"))
    pdf.add_text(
        "These metrics help evaluate whether FlowMind predictions and behavioral indicators "
        "are aligned with NASA-TLX subjective workload ratings."
    )
    pdf.add_blank()

    pdf.add_heading("Conclusion")
    pdf.add_text(
        "FlowMind AI provides real-time cognitive load monitoring, explainable AI, "
        "agentic recommendations, webcam-based ergonomic intelligence, behavioral tracking, "
        "NASA-TLX workload validation, digital twin simulation, adaptive learning, "
        "early overload warning, and research-grade validation."
    )

    return pdf.output(output_path)


if __name__ == "__main__":
    sample_analysis = {
        "inputs": {
            "tasks": 6,
            "stress": 6,
            "sleep": 6,
            "deadline": 7,
            "postureScore": 8,
        },
        "behaviorSummary": {
            "typingSpeed": 25,
            "backspaceCount": 8,
            "idleTime": 12,
            "mouseActivity": 80,
            "behavioralLoadScore": 30,
            "behavioralStatus": "Moderate Cognitive Effort",
            "behavioralMessage": "Behavior shows moderate hesitation.",
        },
        "nasaTlx": {
            "score": 58,
            "flowmindScore": 52.3,
            "difference": 5.7,
        },
        "cognitiveLoad": 52.3,
        "improvedLoad": 35.0,
        "risk": "Moderate Load",
        "suggestion": "Workload is moderate. Avoid multitasking.",
        "explainability": {
            "top_factor": "stress",
            "explanation": "Stress and deadline are increasing cognitive load.",
            "contributions": {
                "tasks": 22,
                "stress": 28,
                "sleep": 14,
                "deadline": 25,
                "posture": 11,
                "behavior": 8,
            },
        },
        "agentDetails": [],
        "plan": ["Complete important tasks first", "Take a short break"],
        "postureIntelligence": {
            "postureStatus": "Good",
            "ergonomicRisk": "Low",
            "postureMessage": "Posture is healthy.",
            "recommendedAction": "Maintain posture.",
        },
        "earlyWarning": {
            "warningScore": 40,
            "warningLevel": "Medium Warning",
            "warningMessage": "Workload may increase.",
            "preventiveAction": "Avoid multitasking.",
        },
        "adaptiveProfile": {
            "totalSessions": 1,
            "averageLoad": 52.3,
            "averageStress": 6,
            "averageSleep": 6,
            "averagePosture": 8,
            "personalPattern": "Workload manageable.",
            "adaptiveRecommendation": "Continue micro-breaks.",
        },
    }

    path = generate_flowmind_report(sample_analysis)
    print(f"PDF report generated: {path}")