import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
import { Bar, Line } from "react-chartjs-2";
import Chart from "chart.js/auto";
import * as mpPose from "@mediapipe/pose";
import * as cam from "@mediapipe/camera_utils";

function App() {
  const [tasks, setTasks] = useState(6);
  const [stress, setStress] = useState(6);
  const [sleep, setSleep] = useState(6);
  const [deadline, setDeadline] = useState(7);

  // Role-based UI
  const [role, setRole] = useState("student");

  const [result, setResult] = useState(null);
  const [apiError, setApiError] = useState("");
  const [postureScore, setPostureScore] = useState(5);
  const [postureDebug, setPostureDebug] = useState({
    headTilt: 0,
    faceCenter: 0,
    screenDistance: "Detecting",
    shoulderVisibility: "Detecting",
  });
  const [loadHistory, setLoadHistory] = useState(Array(20).fill(0));

  const [digitalTwinResult, setDigitalTwinResult] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState("");
  const [isSimulating, setIsSimulating] = useState(false);

  const [validationData, setValidationData] = useState(null);
  const [isValidationLoading, setIsValidationLoading] = useState(false);

  const [isSavingExperiment, setIsSavingExperiment] = useState(false);
  const [savedExperiment, setSavedExperiment] = useState(null);

  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [reportMessage, setReportMessage] = useState("");

  // NASA-TLX States
  const [mentalDemand, setMentalDemand] = useState(50);
  const [physicalDemand, setPhysicalDemand] = useState(30);
  const [temporalDemand, setTemporalDemand] = useState(50);
  const [performanceDifficulty, setPerformanceDifficulty] = useState(50);
  const [effort, setEffort] = useState(50);
  const [frustration, setFrustration] = useState(50);

  const videoRef = useRef(null);

  const isStudent = role === "student";

  const nasaTlxScore = useMemo(() => {
    const total =
      mentalDemand +
      physicalDemand +
      temporalDemand +
      performanceDifficulty +
      effort +
      frustration;

    return Number((total / 6).toFixed(1));
  }, [
    mentalDemand,
    physicalDemand,
    temporalDemand,
    performanceDifficulty,
    effort,
    frustration,
  ]);

  // Real-time Webcam Ergonomic Score for laptop camera
  useEffect(() => {
    const pose = new mpPose.Pose({
      locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`,
    });

    pose.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      enableSegmentation: false,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    pose.onResults((results) => {
      if (!results.poseLandmarks) {
        setPostureScore((prevScore) => Math.max(1, Math.round(prevScore * 0.9)));
        setPostureDebug((prev) => ({
          ...prev,
          shoulderVisibility: "Not detected",
        }));
        return;
      }

      const lm = results.poseLandmarks;
      const nose = lm[0];
      const leftEye = lm[2];
      const rightEye = lm[5];
      const leftShoulder = lm[11];
      const rightShoulder = lm[12];

      const leftShoulderVisible = (leftShoulder.visibility ?? 1) > 0.45;
      const rightShoulderVisible = (rightShoulder.visibility ?? 1) > 0.45;
      const shouldersVisible = leftShoulderVisible && rightShoulderVisible;

      const faceCenterOffset = Math.abs(nose.x - 0.5);
      const faceCenterPenalty = Math.min(3.0, faceCenterOffset * 12);

      const headTilt = Math.abs((leftEye?.y ?? nose.y) - (rightEye?.y ?? nose.y));
      const headTiltPenalty = Math.min(2.5, headTilt * 35);

      let shoulderTiltPenalty = 0;
      let shoulderWidth = 0;
      let shoulderVisibilityPenalty = 1.5;

      if (shouldersVisible) {
        const shoulderTilt = Math.abs(leftShoulder.y - rightShoulder.y);
        shoulderTiltPenalty = Math.min(2.0, shoulderTilt * 25);
        shoulderWidth = Math.abs(leftShoulder.x - rightShoulder.x);
        shoulderVisibilityPenalty = 0;
      }

      let distancePenalty = 0;
      let distanceStatus = "Normal";

      if (shouldersVisible) {
        if (shoulderWidth > 0.55) {
          distancePenalty = 1.5;
          distanceStatus = "Too close";
        } else if (shoulderWidth < 0.16) {
          distancePenalty = 1.0;
          distanceStatus = "Too far";
        }
      } else {
        const noseY = nose.y;
        if (noseY < 0.22) {
          distancePenalty = 1.0;
          distanceStatus = "Too close / face high";
        } else if (noseY > 0.72) {
          distancePenalty = 1.0;
          distanceStatus = "Too far / face low";
        }
      }

      let rawScore =
        10 -
        faceCenterPenalty -
        headTiltPenalty -
        shoulderTiltPenalty -
        distancePenalty -
        shoulderVisibilityPenalty;

      rawScore = Math.min(10, Math.max(1, rawScore));

      setPostureScore((prevScore) => {
        const smoothedScore = prevScore * 0.7 + rawScore * 0.3;
        return Math.round(smoothedScore);
      });

      setPostureDebug({
        headTilt: Number((headTilt * 100).toFixed(1)),
        faceCenter: Number((faceCenterOffset * 100).toFixed(1)),
        screenDistance: distanceStatus,
        shoulderVisibility: shouldersVisible ? "Visible" : "Partially visible",
      });
    });

    if (videoRef.current) {
      const camera = new cam.Camera(videoRef.current, {
        onFrame: async () => await pose.send({ image: videoRef.current }),
        width: 640,
        height: 480,
      });

      camera.start();
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        setApiError("");

        const response = await fetch("http://127.0.0.1:8000/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tasks,
            stress,
            sleep,
            deadline,
            webcam_posture: postureScore,
            nasa_tlx_score: nasaTlxScore,
          }),
        });

        if (!response.ok) {
          throw new Error("Backend response not OK");
        }

        const data = await response.json();

        const normalizedData = {
          ...data,
          cognitiveLoad:
            data.cognitiveLoad ??
            data.cognitive_load ??
            data.cognitive_load_score ??
            data.cognitiveLoadScore ??
            0,
          improvedLoad:
            data.improvedLoad ??
            data.improved_load ??
            data.improved_load_score ??
            0,
          risk: data.risk ?? data.riskLevel ?? data.risk_level ?? "Calculated",
          suggestion:
            data.suggestion ??
            data.aiSuggestion ??
            data.ai_suggestion ??
            data.recommendation ??
            "Workload analyzed successfully.",
        };

        setResult(normalizedData);
        setLoadHistory((prev) => [
          ...prev.slice(1),
          normalizedData.cognitiveLoad || 0,
        ]);
      } catch (err) {
        console.error("Backend error:", err);
        setApiError("Backend connected nahi ho raha ya response key mismatch hai.");
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [tasks, stress, sleep, deadline, postureScore, nasaTlxScore]);

  const runDigitalTwinSimulation = async (scenarioType) => {
    try {
      setSelectedScenario(scenarioType);
      setIsSimulating(true);

      const response = await fetch("http://127.0.0.1:8000/digital-twin-simulation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tasks,
          stress,
          sleep,
          deadline,
          webcam_posture: postureScore,
          scenario_type: scenarioType,
          nasa_tlx_score: nasaTlxScore,
        }),
      });

      const data = await response.json();
      setDigitalTwinResult(data);
    } catch (err) {
      console.error("Digital twin simulation error:", err);
    } finally {
      setIsSimulating(false);
    }
  };

  const fetchValidationResults = async () => {
    try {
      setIsValidationLoading(true);
      const response = await fetch("http://127.0.0.1:8000/validation-results");
      const data = await response.json();
      setValidationData(data);
    } catch (err) {
      console.error("Validation dashboard error:", err);
    } finally {
      setIsValidationLoading(false);
    }
  };

  useEffect(() => {
    fetchValidationResults();
  }, []);

  const saveExperimentSession = async () => {
    try {
      setIsSavingExperiment(true);

      const response = await fetch("http://127.0.0.1:8000/save-experiment-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tasks,
          stress,
          sleep,
          deadline,
          webcam_posture: postureScore,
          nasa_tlx_score: nasaTlxScore,
          nasa_tlx: {
            mentalDemand,
            physicalDemand,
            temporalDemand,
            performanceDifficulty,
            effort,
            frustration,
            score: nasaTlxScore,
          },
        }),
      });

      const data = await response.json();
      setSavedExperiment(data);
      await fetchValidationResults();
    } catch (err) {
      console.error("Save experiment session error:", err);
    } finally {
      setIsSavingExperiment(false);
    }
  };

  const generateReport = async () => {
    try {
      setIsGeneratingReport(true);
      setReportMessage("");

      const response = await fetch("http://127.0.0.1:8000/generate-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tasks,
          stress,
          sleep,
          deadline,
          webcam_posture: postureScore,
          digital_twin_data: digitalTwinResult,
          nasa_tlx_score: nasaTlxScore,
        }),
      });

      if (!response.ok) {
        throw new Error("Report generation failed");
      }

      const blob = await response.blob();
      const fileURL = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = fileURL;
      link.download = "FlowMind_Cognitive_Report.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(fileURL);

      setReportMessage("Report generated and downloaded successfully.");
    } catch (err) {
      console.error("Report generation error:", err);
      setReportMessage("Report generation failed. Check backend terminal.");
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const chartData = {
    labels: ["Before AI", "After AI"],
    datasets: [
      {
        label: "Cognitive Load %",
        data: [result?.cognitiveLoad || 0, result?.improvedLoad || 0],
        backgroundColor: [
          result?.cognitiveLoad > 85 ? "#f43f5e" : "#fca5a5",
          "#22c55e",
        ],
        borderRadius: 10,
      },
    ],
  };

  const explainability = result?.explainability;
  const contributions = explainability?.contributions || {};

  const explainabilityChartData = {
    labels: ["Tasks", "Stress", "Sleep", "Deadline", "Posture"],
    datasets: [
      {
        label: "Contribution %",
        data: [
          contributions.tasks || 0,
          contributions.stress || 0,
          contributions.sleep || 0,
          contributions.deadline || 0,
          contributions.posture || 0,
        ],
        backgroundColor: ["#38bdf8", "#f472b6", "#a78bfa", "#fb923c", "#22c55e"],
        borderRadius: 10,
      },
    ],
  };

  const latestLoad = loadHistory[loadHistory.length - 1] || 0;
  const validLoads = loadHistory.filter((value) => value > 0);

  const averageLoad =
    validLoads.length > 0
      ? (
          validLoads.reduce((sum, value) => sum + value, 0) / validLoads.length
        ).toFixed(1)
      : 0;

  const peakLoad =
    validLoads.length > 0 ? Math.max(...validLoads).toFixed(1) : 0;

  const previousLoad = loadHistory[loadHistory.length - 2] || 0;

  let trendStatus = "Stable";
  if (latestLoad > previousLoad + 2) {
    trendStatus = "Increasing";
  } else if (latestLoad < previousLoad - 2) {
    trendStatus = "Reducing";
  }

  const liveLineChartData = {
    labels: loadHistory.map((_, i) => i + 1),
    datasets: [
      {
        label: "Live Cognitive Load",
        data: loadHistory,
        borderColor: "#fbbf24",
        backgroundColor: "rgba(251, 191, 36, 0.2)",
        tension: 0.35,
        fill: true,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        labels: {
          color: "#cbd5e1",
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: "#cbd5e1",
        },
        grid: {
          color: "rgba(148, 163, 184, 0.12)",
        },
      },
      y: {
        min: 0,
        max: 100,
        ticks: {
          color: "#cbd5e1",
        },
        grid: {
          color: "rgba(148, 163, 184, 0.12)",
        },
      },
    },
  };

  const fallbackAgentDetails = [
    {
      name: "🧠 CogLoad Monitor",
      message: result?.timeline?.[0] || "Waiting for cognitive load signal...",
      status:
        result?.cognitiveLoad >= 75
          ? "Critical"
          : result?.cognitiveLoad >= 45
          ? "Watch"
          : "Normal",
      confidence: result?.cognitiveLoad
        ? Math.min(95, Math.max(65, Math.round(result.cognitiveLoad + 15)))
        : 0,
      reason:
        result?.cognitiveLoad >= 75
          ? "Cognitive load is high, so overload risk is critical."
          : result?.cognitiveLoad >= 45
          ? "Cognitive load is moderate, so the system is monitoring workload."
          : "Cognitive load is low, so workload is currently manageable.",
    },
    {
      name: "🎯 Intent Agent",
      message: result?.timeline?.[1] || "Waiting for intent prediction...",
      status: deadline >= 7 || stress >= 7 ? "Watch" : "Normal",
      confidence: Math.min(95, 60 + deadline * 3 + stress * 2),
      reason:
        deadline >= 7
          ? "Deadline pressure is high, so deadline-focused mode is selected."
          : stress >= 7
          ? "Stress is high, so recovery-first focus is suggested."
          : "Inputs indicate stable focus conditions.",
    },
    {
      name: "📅 Planner Agent",
      message: result?.timeline?.[2] || "Waiting for planning decision...",
      status: tasks >= 9 || deadline >= 7 ? "Watch" : "Normal",
      confidence: Math.min(95, 60 + tasks * 2 + deadline * 2),
      reason:
        tasks >= 9
          ? "Task count is high, so prioritization is required."
          : deadline >= 7
          ? "Deadline pressure is high, so urgent tasks are moved first."
          : "Task flow is balanced for the current workload.",
    },
    {
      name: "💬 Recovery Agent",
      message: result?.timeline?.[3] || "Waiting for recovery suggestion...",
      status: sleep <= 4 || postureScore <= 5 || stress >= 7 ? "Watch" : "Normal",
      confidence: Math.min(
        95,
        60 + (10 - sleep) * 2 + (10 - postureScore) * 2 + stress * 2
      ),
      reason:
        sleep <= 4
          ? "Sleep score is low, so recovery break is recommended."
          : postureScore <= 5
          ? "Posture score is low, so ergonomic correction is required."
          : stress >= 7
          ? "Stress level is high, so multitasking should be avoided."
          : "Recovery state is acceptable, continue with micro-breaks.",
    },
    {
      name: "🔁 Reflection Agent",
      message: result?.timeline?.[4] || "Waiting for session reflection...",
      status:
        result?.cognitiveLoad >= 75
          ? "Critical"
          : result?.cognitiveLoad >= 45
          ? "Watch"
          : "Normal",
      confidence: result?.cognitiveLoad
        ? Math.min(95, Math.max(70, Math.round(result.cognitiveLoad + 10)))
        : 0,
      reason:
        result?.cognitiveLoad >= 75
          ? "Overload pattern is stored for future early warning."
          : result?.cognitiveLoad >= 45
          ? "Moderate load pattern is stored for progress tracking."
          : "Healthy workload pattern is stored as a positive baseline.",
    },
  ];

  const agentCards =
    result?.agentDetails && result.agentDetails.length > 0
      ? result.agentDetails
      : fallbackAgentDetails;

  const getStatusClass = (status) => {
    if (status === "Critical") return "status-critical";
    if (status === "Watch") return "status-watch";
    return "status-normal";
  };

  const scenarioButtons = [
    { key: "improve_sleep", label: "Improve Sleep" },
    { key: "reduce_stress", label: "Reduce Stress" },
    { key: "improve_posture", label: "Improve Posture" },
    { key: "reduce_tasks", label: "Reduce Tasks" },
    { key: "balanced_recovery", label: "Balanced Recovery Plan" },
  ];

  const modelMetrics = validationData?.modelMetrics || {};
  const sessionMetrics = validationData?.sessionMetrics || {};
  const autoLogMetrics = validationData?.autoLogMetrics || {};
  const experimentMetrics = validationData?.experimentMetrics || {};

  const postureIntelligence = result?.postureIntelligence || {};
  const adaptiveProfile = result?.adaptiveProfile || {};
  const earlyWarning = result?.earlyWarning || {};

  return (
    <div className="container premium">
      <h1>FlowMind</h1>
      <p className="subtitle">
        Explainable Cognitive Workload and Ergonomic Assistance System
      </p>

      <div className="chart-card">
        <h2>Select User Interface</h2>
        <p className="digital-subtitle">
          Choose your role to personalize the workload assessment context.
        </p>

        <div className="scenario-buttons">
          <button
            className={role === "student" ? "scenario-btn active-scenario" : "scenario-btn"}
            onClick={() => setRole("student")}
          >
            Student Interface
          </button>

          <button
            className={role === "professor" ? "scenario-btn active-scenario" : "scenario-btn"}
            onClick={() => setRole("professor")}
          >
            Professor Interface
          </button>
        </div>

        <div className="impact-box" style={{ marginTop: "22px" }}>
          {isStudent
            ? "Student mode focuses on academic tasks, study stress, sleep quality, deadline pressure, NASA-TLX validation, and webcam-based ergonomic posture risk."
            : "Professor mode focuses on lecture preparation, evaluation workload, meetings, screen fatigue, deadline pressure, NASA-TLX validation, and webcam-based ergonomic posture risk."}
        </div>
      </div>

      <h2 className="section-title">
        {isStudent
          ? "Student Cognitive Workload Assessment"
          : "Professor Cognitive Workload Assessment"}
      </h2>

      <div className="executive-summary">
        <div className="summary-box">
          <span>Current Load</span>
          <strong>{result?.cognitiveLoad || 0}%</strong>
        </div>
        <div className="summary-box">
          <span>Risk Level</span>
          <strong>{apiError || result?.risk || "Calculating..."}</strong>
        </div>
        <div className="summary-box">
          <span>Posture Risk</span>
          <strong>{postureIntelligence.ergonomicRisk || "Analyzing"}</strong>
        </div>
        <div className="summary-box">
          <span>Early Warning</span>
          <strong>{earlyWarning.warningLevel || "Analyzing"}</strong>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <h2>{isStudent ? "Academic Workload Input" : "Professional Workload Input"}</h2>

          <label>
            {isStudent ? "Academic Tasks" : "Professional Tasks"}: {tasks}
          </label>
          <input
            type="range"
            min="1"
            max="12"
            value={tasks}
            onChange={(e) => setTasks(Number(e.target.value))}
          />

          <label>
            {isStudent ? "Study Stress" : "Work Stress"}: {stress}/10
          </label>
          <input
            type="range"
            min="1"
            max="10"
            value={stress}
            onChange={(e) => setStress(Number(e.target.value))}
          />

          <label>
            {isStudent ? "Sleep Quality" : "Rest / Sleep Quality"}: {sleep}
          </label>
          <input
            type="range"
            min="1"
            max="10"
            value={sleep}
            onChange={(e) => setSleep(Number(e.target.value))}
          />

          <label>
            {isStudent
              ? "Assignment / Exam Deadline Pressure"
              : "Lecture / Work Deadline Pressure"}
            : {deadline}/10
          </label>
          <input
            type="range"
            min="1"
            max="10"
            value={deadline}
            onChange={(e) => setDeadline(Number(e.target.value))}
          />

          <h3>Webcam Feed (Ergonomic Detection)</h3>
          <video ref={videoRef} width="100%" height="240" autoPlay muted></video>

          <p>Real-time Ergonomic Score: {postureScore}/10</p>
          <p className="mini-text">
            Head tilt: {postureDebug.headTilt} | Face center offset:{" "}
            {postureDebug.faceCenter} | Distance: {postureDebug.screenDistance} |
            Shoulders: {postureDebug.shoulderVisibility}
          </p>
        </div>

        <div className="card score-card">
          <h2>Cognitive Load Score</h2>
          <div className="score">{result?.cognitiveLoad || 0}%</div>
          <p>{apiError || result?.risk || "Calculating..."}</p>
        </div>

        <div className="card">
          <h2>AI Suggestion</h2>
          <details open>
            <summary>Click to view recommendation</summary>
            <p>{apiError || result?.suggestion || "Analyzing workload..."}</p>
          </details>
        </div>
      </div>

      <div className="chart-card">
        <h2>
          {isStudent
            ? "Student NASA-TLX Workload Validation"
            : "Professor NASA-TLX Workload Validation"}
        </h2>
        <p className="digital-subtitle">
          {isStudent
            ? "After completing a study or academic task, the student rates workload using NASA-TLX. The score is compared with the FlowMind predicted cognitive load score."
            : "After completing teaching, evaluation, meeting, or screen-based work, the professor rates workload using NASA-TLX. The score is compared with the FlowMind predicted cognitive load score."}
        </p>

        <label>Mental Demand: {mentalDemand}</label>
        <input
          type="range"
          min="0"
          max="100"
          value={mentalDemand}
          onChange={(e) => setMentalDemand(Number(e.target.value))}
        />

        <label>Physical Demand: {physicalDemand}</label>
        <input
          type="range"
          min="0"
          max="100"
          value={physicalDemand}
          onChange={(e) => setPhysicalDemand(Number(e.target.value))}
        />

        <label>Temporal Demand / Time Pressure: {temporalDemand}</label>
        <input
          type="range"
          min="0"
          max="100"
          value={temporalDemand}
          onChange={(e) => setTemporalDemand(Number(e.target.value))}
        />

        <label>Performance Difficulty: {performanceDifficulty}</label>
        <input
          type="range"
          min="0"
          max="100"
          value={performanceDifficulty}
          onChange={(e) => setPerformanceDifficulty(Number(e.target.value))}
        />

        <label>Effort: {effort}</label>
        <input
          type="range"
          min="0"
          max="100"
          value={effort}
          onChange={(e) => setEffort(Number(e.target.value))}
        />

        <label>Frustration: {frustration}</label>
        <input
          type="range"
          min="0"
          max="100"
          value={frustration}
          onChange={(e) => setFrustration(Number(e.target.value))}
        />

        <div className="live-metrics">
          <div className="metric-box">
            <span>FlowMind Score</span>
            <strong>{result?.cognitiveLoad || 0}%</strong>
          </div>
          <div className="metric-box">
            <span>NASA-TLX Score</span>
            <strong>{nasaTlxScore}%</strong>
          </div>
          <div className="metric-box">
            <span>Difference</span>
            <strong>
              {Math.abs((result?.cognitiveLoad || 0) - nasaTlxScore).toFixed(1)}%
            </strong>
          </div>
        </div>
      </div>

      <div className="chart-card">
        <h2>Privacy and Ethical Use</h2>
        <p className="digital-subtitle">
          Webcam is used only for real-time ergonomic posture estimation. No image,
          video, or camera frame is stored. Only numeric posture score, FlowMind
          cognitive load score, and NASA-TLX score are saved for validation and
          report generation.
        </p>
      </div>

      <div className="intelligence-card">
        <h2>Webcam Ergonomic Intelligence</h2>
        <div className="intelligence-grid">
          <div className="intelligence-box">
            <span>Posture Status</span>
            <strong>{postureIntelligence.postureStatus || "Analyzing"}</strong>
          </div>
          <div className="intelligence-box">
            <span>Ergonomic Risk</span>
            <strong>{postureIntelligence.ergonomicRisk || "Analyzing"}</strong>
          </div>
          <div className="intelligence-box wide-box">
            <span>Posture Message</span>
            <p>{postureIntelligence.postureMessage || "Waiting for posture signal..."}</p>
          </div>
          <div className="intelligence-box wide-box">
            <span>Recommended Action</span>
            <p>
              {postureIntelligence.recommendedAction ||
                "Posture recommendation will appear here."}
            </p>
          </div>
        </div>
      </div>

      <div className="warning-card">
        <h2>Early Overload Warning System</h2>
        <div className="warning-grid">
          <div className="warning-box">
            <span>Warning Score</span>
            <strong>{earlyWarning.warningScore ?? 0}%</strong>
          </div>
          <div className="warning-box">
            <span>Warning Level</span>
            <strong>{earlyWarning.warningLevel || "Analyzing"}</strong>
          </div>
          <div className="warning-box wide-box">
            <span>Warning Message</span>
            <p>{earlyWarning.warningMessage || "No warning signal yet."}</p>
          </div>
          <div className="warning-box wide-box">
            <span>Preventive Action</span>
            <p>
              {earlyWarning.preventiveAction ||
                "Preventive recommendation will appear here."}
            </p>
          </div>
        </div>
      </div>

      <div className="explain-card">
        <h2>Explainable AI: Why is Load High?</h2>
        <p className="explain-text">
          {explainability?.explanation ||
            "Analyzing which factors are increasing your cognitive load..."}
        </p>

        <div className="factor-list">
          {["tasks", "stress", "sleep", "deadline", "posture"].map((factor) => (
            <div className="factor-row" key={factor}>
              <span>{factor.charAt(0).toUpperCase() + factor.slice(1)}</span>
              <div className="factor-bar">
                <div
                  className="factor-fill"
                  style={{ width: `${contributions[factor] || 0}%` }}
                ></div>
              </div>
              <b>{contributions[factor] || 0}%</b>
            </div>
          ))}
        </div>

        <div className="top-factor-box">
          Main Overload Driver:{" "}
          <strong>{explainability?.top_factor || "Calculating..."}</strong>
        </div>
      </div>

      <div className="chart-card">
        <h2>Factor Contribution Breakdown</h2>
        <Bar data={explainabilityChartData} options={chartOptions} />
      </div>

      <div className="chart-card">
        <h2>Before vs After Cognitive Load</h2>
        <Bar data={chartData} options={chartOptions} />
      </div>

      <div className="chart-card">
        <h2>Real-Time Cognitive Load Timeline</h2>
        <div className="live-metrics">
          <div className="metric-box">
            <span>Latest Load</span>
            <strong>{latestLoad}%</strong>
          </div>
          <div className="metric-box">
            <span>Average Load</span>
            <strong>{averageLoad}%</strong>
          </div>
          <div className="metric-box">
            <span>Peak Load</span>
            <strong>{peakLoad}%</strong>
          </div>
          <div className="metric-box">
            <span>Trend</span>
            <strong
              className={
                trendStatus === "Increasing"
                  ? "trend-up"
                  : trendStatus === "Reducing"
                  ? "trend-down"
                  : "trend-stable"
              }
            >
              {trendStatus}
            </strong>
          </div>
        </div>
        <Line data={liveLineChartData} options={chartOptions} />
      </div>

      <div className="digital-twin-card">
        <h2>Cognitive Digital Twin Simulator</h2>
        <p className="digital-subtitle">
          Test what-if changes before applying them in real life.
        </p>

        <div className="scenario-buttons">
          {scenarioButtons.map((scenario) => (
            <button
              key={scenario.key}
              className={
                selectedScenario === scenario.key
                  ? "scenario-btn active-scenario"
                  : "scenario-btn"
              }
              onClick={() => runDigitalTwinSimulation(scenario.key)}
              disabled={isSimulating}
            >
              {scenario.label}
            </button>
          ))}
        </div>

        {isSimulating && (
          <p className="simulation-loading">Running digital twin simulation...</p>
        )}

        {digitalTwinResult && (
          <div className="digital-result-grid">
            <div className="digital-result-box">
              <span>Current Load</span>
              <strong>{digitalTwinResult.currentLoad}%</strong>
            </div>
            <div className="digital-result-box">
              <span>Predicted Load</span>
              <strong>{digitalTwinResult.predictedLoad}%</strong>
            </div>
            <div className="digital-result-box">
              <span>Expected Improvement</span>
              <strong>{digitalTwinResult.improvement}%</strong>
            </div>
            <div className="digital-result-box">
              <span>Impact</span>
              <strong>{digitalTwinResult.impact}</strong>
            </div>
          </div>
        )}

        {digitalTwinResult && (
          <div className="digital-action-box">
            <h3>Recommended What-if Action</h3>
            <p>{digitalTwinResult.action}</p>

            <h3>Simulated Inputs</h3>
            <p>
              Tasks: {digitalTwinResult.simulatedInputs?.tasks} | Stress:{" "}
              {digitalTwinResult.simulatedInputs?.stress} | Sleep:{" "}
              {digitalTwinResult.simulatedInputs?.sleep} | Deadline:{" "}
              {digitalTwinResult.simulatedInputs?.deadline} | Posture:{" "}
              {digitalTwinResult.simulatedInputs?.posture}
            </p>
          </div>
        )}
      </div>

      <div className="adaptive-card">
        <h2>Personal Adaptive Learning Engine</h2>
        <div className="adaptive-grid">
          <div className="adaptive-box">
            <span>Total Adaptive Sessions</span>
            <strong>{adaptiveProfile.totalSessions ?? 0}</strong>
          </div>
          <div className="adaptive-box">
            <span>Average Load</span>
            <strong>{adaptiveProfile.averageLoad ?? 0}%</strong>
          </div>
          <div className="adaptive-box">
            <span>Average Stress</span>
            <strong>{adaptiveProfile.averageStress ?? 0}/10</strong>
          </div>
          <div className="adaptive-box">
            <span>Average Sleep</span>
            <strong>{adaptiveProfile.averageSleep ?? 0}/10</strong>
          </div>
          <div className="adaptive-box">
            <span>Average Posture</span>
            <strong>{adaptiveProfile.averagePosture ?? 0}/10</strong>
          </div>
          <div className="adaptive-box wide-box">
            <span>Personal Pattern</span>
            <p>{adaptiveProfile.personalPattern || "No pattern detected yet."}</p>
          </div>
          <div className="adaptive-box wide-box">
            <span>Adaptive Recommendation</span>
            <p>
              {adaptiveProfile.adaptiveRecommendation ||
                "Recommendation will appear after more sessions."}
            </p>
          </div>
        </div>
      </div>

      <div className="experiment-card">
        <h2>Research Experiment Session</h2>
        <p>
          Save only meaningful/manual trials as valid research sessions. Auto logs
          are not counted as final experiment sessions.
        </p>

        <button
          className="save-experiment-btn"
          onClick={saveExperimentSession}
          disabled={isSavingExperiment}
        >
          {isSavingExperiment ? "Saving Session..." : "Save Experiment Session"}
        </button>

        {savedExperiment?.saved && (
          <div className="saved-session-box">
            <h3>Session Saved Successfully</h3>
            <p>
              <strong>Session ID:</strong> {savedExperiment.session?.sessionId}
            </p>
            <p>
              <strong>Baseline Load:</strong>{" "}
              {savedExperiment.session?.baselineLoad}% |{" "}
              <strong>FlowMind Load:</strong>{" "}
              {savedExperiment.session?.flowmindLoad}% |{" "}
              <strong>Improvement:</strong>{" "}
              {savedExperiment.session?.improvementPercent}%
            </p>
            <p>
              <strong>Top Factor:</strong> {savedExperiment.session?.topFactor}
            </p>
          </div>
        )}
      </div>

      <div className="report-card">
        <h2>FlowMind Cognitive Report Generator</h2>
        <p>
          {isStudent
            ? "Generate a student workload report containing academic inputs, cognitive load analysis, webcam ergonomic feedback, NASA-TLX validation, AI suggestions, digital twin simulation, adaptive profile, and validation summary."
            : "Generate a professor workload report containing professional inputs, cognitive load analysis, webcam ergonomic feedback, NASA-TLX validation, AI suggestions, digital twin simulation, adaptive profile, and validation summary."}
        </p>

        <button
          className="generate-report-btn"
          onClick={generateReport}
          disabled={isGeneratingReport}
        >
          {isGeneratingReport ? "Generating Report..." : "Generate PDF Report"}
        </button>

        {reportMessage && <p className="report-message">{reportMessage}</p>}
      </div>

      <div className="validation-card">
        <div className="validation-header">
          <div>
            <h2>Research-Grade Validation Dashboard</h2>
            <p>
              Auto logs are separated from manually saved experiment sessions.
              FlowMind score is compared with NASA-TLX score for validation.
            </p>
          </div>

          <button
            className="refresh-validation-btn"
            onClick={fetchValidationResults}
            disabled={isValidationLoading}
          >
            {isValidationLoading ? "Refreshing..." : "Refresh Validation"}
          </button>
        </div>

        <div className="validation-grid">
          <div className="validation-box">
            <span>RMSE</span>
            <strong>{modelMetrics.rmse ?? 0}</strong>
          </div>
          <div className="validation-box">
            <span>MAE</span>
            <strong>{modelMetrics.mae ?? 0}</strong>
          </div>
          <div className="validation-box">
            <span>R² Score</span>
            <strong>{modelMetrics.r2Score ?? 0}</strong>
          </div>
          <div className="validation-box">
            <span>Valid Experiment Sessions</span>
            <strong>{sessionMetrics.totalSessions ?? 0}</strong>
          </div>
          <div className="validation-box">
            <span>Auto Logs Ignored</span>
            <strong>{autoLogMetrics.totalAutoLogs ?? 0}</strong>
          </div>
          <div className="validation-box">
            <span>Duplicates Ignored</span>
            <strong>{experimentMetrics.duplicateSessionsIgnored ?? 0}</strong>
          </div>
          <div className="validation-box">
            <span>Baseline Avg Load</span>
            <strong>{sessionMetrics.averageLoad ?? 0}%</strong>
          </div>
          <div className="validation-box">
            <span>FlowMind Avg Load</span>
            <strong>{sessionMetrics.averageImprovedLoad ?? 0}%</strong>
          </div>
          <div className="validation-box">
            <span>Avg Reduction</span>
            <strong>{sessionMetrics.averageImprovement ?? 0}%</strong>
          </div>
          <div className="validation-box">
            <span>Reduction Rate</span>
            <strong>{sessionMetrics.averageImprovementPercent ?? 0}%</strong>
          </div>

          <div className="validation-box">
            <span>Avg NASA-TLX Score</span>
            <strong>{sessionMetrics.averageNasaTlxScore ?? 0}%</strong>
          </div>
          <div className="validation-box">
            <span>FlowMind-NASA Correlation</span>
            <strong>{sessionMetrics.flowmindNasaCorrelation ?? 0}</strong>
          </div>
          <div className="validation-box">
            <span>Avg FlowMind-NASA Difference</span>
            <strong>{sessionMetrics.averageFlowmindNasaDifference ?? 0}%</strong>
          </div>
        </div>

        <div className="risk-summary">
          <div className="risk-pill low-risk">
            Low Risk: {sessionMetrics.lowRiskSessions ?? 0}
          </div>
          <div className="risk-pill moderate-risk">
            Moderate Risk: {sessionMetrics.moderateRiskSessions ?? 0}
          </div>
          <div className="risk-pill high-risk">
            High Risk: {sessionMetrics.highRiskSessions ?? 0}
          </div>
        </div>

        <p className="validation-message">
          {sessionMetrics.message ||
            "Validation results will appear after saving experiment sessions."}
        </p>
      </div>

      <h2 className="section-title">Premium Dynamic Agentic AI Workflow</h2>

      <div className="agents premium-agents">
        {agentCards.map((agent, idx) => (
          <div key={idx} className="agent premium-agent-card">
            <div className="agent-header">
              <strong>{agent.name || agent.title}</strong>
              <span className={`status-badge ${getStatusClass(agent.status)}`}>
                {agent.status || "Normal"}
              </span>
            </div>

            <p className="agent-message">
              {agent.message || agent.output || "Waiting for agent response..."}
            </p>

            <div className="confidence-section">
              <div className="confidence-label">
                <span>Confidence</span>
                <b>{agent.confidence || 0}%</b>
              </div>
              <div className="confidence-bar">
                <div
                  className="confidence-fill"
                  style={{ width: `${agent.confidence || 0}%` }}
                ></div>
              </div>
            </div>

            <p className="agent-reason">
              <strong>Reason:</strong>{" "}
              {agent.reason || "Decision reason will appear after analysis."}
            </p>
          </div>
        ))}
      </div>

      <div className="final-grid">
        <div className="card">
          <h2>Optimized Daily Plan</h2>
          <ul className="timeline">
            {result?.plan?.map((item, idx) => (
              <li key={idx}>{item}</li>
            )) || <li>Generating optimized plan...</li>}
          </ul>
        </div>
      </div>

      <div className="impact-box">
        FlowMind reduces overload by converting scattered tasks into a calm,
        prioritized, explainable, and ergonomically safe action plan.
      </div>
    </div>
  );
}

export default App;