import { useEffect, useState, useRef } from "react";
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
  const [result, setResult] = useState(null);
  const [postureScore, setPostureScore] = useState(5);
  const [loadHistory, setLoadHistory] = useState(Array(20).fill(0));

  // Digital Twin states
  const [digitalTwinResult, setDigitalTwinResult] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState("");
  const [isSimulating, setIsSimulating] = useState(false);

  // Validation states
  const [validationData, setValidationData] = useState(null);
  const [isValidationLoading, setIsValidationLoading] = useState(false);

  const videoRef = useRef(null);
  const postureHistoryRef = useRef([]);
  const cameraRef = useRef(null);

  // ------------------------------
  // MediaPipe Pose - Posture Detection
  // ------------------------------
  useEffect(() => {
    const isVisible = (point) =>
      point && (point.visibility === undefined || point.visibility > 0.45);

    const clampScore = (value) => Math.min(10, Math.max(1, value));

    const getAverageScore = (newScore) => {
      // Last 5 readings average:
      // stable enough for demo, but still changes when posture changes.
      const history = postureHistoryRef.current;
      history.push(newScore);

      if (history.length > 5) {
        history.shift();
      }

      const average =
        history.reduce((sum, value) => sum + value, 0) / history.length;

      return Math.round(clampScore(average));
    };

    const pose = new mpPose.Pose({
      locateFile: (file) =>
        `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`,
    });

    pose.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      enableSegmentation: false,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    pose.onResults((results) => {
      const landmarks = results.poseLandmarks;

      if (!landmarks) {
        return;
      }

      const nose = landmarks[0];
      const leftShoulder = landmarks[11];
      const rightShoulder = landmarks[12];
      const leftHip = landmarks[23];
      const rightHip = landmarks[24];

      const shouldersVisible =
        isVisible(leftShoulder) && isVisible(rightShoulder);
      const hipsVisible = isVisible(leftHip) && isVisible(rightHip);
      const noseVisible = isVisible(nose);

      if (!shouldersVisible) {
        return;
      }

      const shoulderCenterX = (leftShoulder.x + rightShoulder.x) / 2;
      const shoulderTilt = Math.abs(leftShoulder.y - rightShoulder.y);

      let hipTilt = 0;
      let torsoLean = 0;

      if (hipsVisible) {
        const hipCenterX = (leftHip.x + rightHip.x) / 2;
        hipTilt = Math.abs(leftHip.y - rightHip.y);
        torsoLean = Math.abs(shoulderCenterX - hipCenterX);
      }

      let headOffset = 0;

      if (noseVisible) {
        headOffset = Math.abs(nose.x - shoulderCenterX);
      }

      // Score logic:
      // Straight shoulders + balanced hips + centered head = high score.
      // Tilted shoulders, tilted hips, side lean, or head offset reduce score.
      let rawScore =
        10 -
        shoulderTilt * 35 -
        hipTilt * 25 -
        torsoLean * 18 -
        headOffset * 10;

      rawScore = clampScore(rawScore);

      const stableScore = getAverageScore(rawScore);
      setPostureScore(stableScore);
    });

    if (videoRef.current) {
      cameraRef.current = new cam.Camera(videoRef.current, {
        onFrame: async () => {
          if (videoRef.current) {
            await pose.send({ image: videoRef.current });
          }
        },
        width: 640,
        height: 480,
      });

      cameraRef.current.start();
    }

    return () => {
      if (cameraRef.current) {
        cameraRef.current.stop();
      }
    };
  }, []);

  // ------------------------------
  // Fetch backend every 2 seconds
  // ------------------------------
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch("http://127.0.0.1:8000/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tasks,
            stress,
            sleep,
            deadline,
            webcam_posture: postureScore,
          }),
        });

        const data = await response.json();

        setResult(data);
        setLoadHistory((prev) => [
          ...prev.slice(1),
          data.cognitiveLoad || 0,
        ]);
      } catch (err) {
        console.error("Backend error:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [tasks, stress, sleep, deadline, postureScore]);

  // ------------------------------
  // Digital Twin Simulation
  // ------------------------------
  const runDigitalTwinSimulation = async (scenarioType) => {
    try {
      setSelectedScenario(scenarioType);
      setIsSimulating(true);

      const response = await fetch(
        "http://127.0.0.1:8000/digital-twin-simulation",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tasks,
            stress,
            sleep,
            deadline,
            webcam_posture: postureScore,
            scenario_type: scenarioType,
          }),
        }
      );

      const data = await response.json();
      setDigitalTwinResult(data);
    } catch (err) {
      console.error("Digital twin simulation error:", err);
    } finally {
      setIsSimulating(false);
    }
  };

  // ------------------------------
  // Validation Dashboard Fetch
  // ------------------------------
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

  // ------------------------------
  // Before vs After Chart
  // ------------------------------
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

  // ------------------------------
  // Explainable AI Chart
  // ------------------------------
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
        backgroundColor: [
          "#38bdf8",
          "#f472b6",
          "#a78bfa",
          "#fb923c",
          "#22c55e",
        ],
        borderRadius: 10,
      },
    ],
  };

  // ------------------------------
  // Live Timeline Calculations
  // ------------------------------
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
        ticks: { color: "#cbd5e1" },
        grid: { color: "rgba(148, 163, 184, 0.12)" },
      },
      y: {
        min: 0,
        max: 100,
        ticks: { color: "#cbd5e1" },
        grid: { color: "rgba(148, 163, 184, 0.12)" },
      },
    },
  };

  // ------------------------------
  // Premium Dynamic Agent Cards
  // ------------------------------
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
      status:
        sleep <= 4 || postureScore <= 5 || stress >= 7 ? "Watch" : "Normal",
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

  return (
    <div className="container premium">
      <h1>FlowMind</h1>
      <p className="subtitle">
        Agentic AI Life OS + Real-time Ergonomic Feedback
      </p>

      <div className="grid">
        {/* User Input */}
        <div className="card">
          <h2>User Input</h2>

          <label>Tasks: {tasks}</label>
          <input
            type="range"
            min="1"
            max="12"
            value={tasks}
            onChange={(e) => setTasks(Number(e.target.value))}
          />

          <label>Stress: {stress}/10</label>
          <input
            type="range"
            min="1"
            max="10"
            value={stress}
            onChange={(e) => setStress(Number(e.target.value))}
          />

          <label>Sleep: {sleep}</label>
          <input
            type="range"
            min="1"
            max="10"
            value={sleep}
            onChange={(e) => setSleep(Number(e.target.value))}
          />

          <label>Deadline: {deadline}/10</label>
          <input
            type="range"
            min="1"
            max="10"
            value={deadline}
            onChange={(e) => setDeadline(Number(e.target.value))}
          />

          <h3>Webcam Feed (Posture Detection)</h3>
          <video
            ref={videoRef}
            width="100%"
            height="240"
            autoPlay
            muted
          ></video>

          <p>Posture Score: {postureScore}/10</p>
        </div>

        {/* Cognitive Load */}
        <div className="card score-card">
          <h2>Cognitive Load Score</h2>
          <div className="score">{result?.cognitiveLoad || 0}%</div>
          <p>{result?.risk || "Calculating..."}</p>
        </div>

        {/* AI Suggestion */}
        <div className="card">
          <h2>AI Suggestion</h2>
          <details open>
            <summary>Click to view recommendation</summary>
            <p>{result?.suggestion || "Analyzing workload..."}</p>
          </details>
        </div>
      </div>

      {/* Explainable AI Panel */}
      <div className="explain-card">
        <h2>Explainable AI: Why is Load High?</h2>

        <p className="explain-text">
          {explainability?.explanation ||
            "Analyzing which factors are increasing your cognitive load..."}
        </p>

        <div className="factor-list">
          <div className="factor-row">
            <span>Tasks</span>
            <div className="factor-bar">
              <div
                className="factor-fill"
                style={{ width: `${contributions.tasks || 0}%` }}
              ></div>
            </div>
            <b>{contributions.tasks || 0}%</b>
          </div>

          <div className="factor-row">
            <span>Stress</span>
            <div className="factor-bar">
              <div
                className="factor-fill"
                style={{ width: `${contributions.stress || 0}%` }}
              ></div>
            </div>
            <b>{contributions.stress || 0}%</b>
          </div>

          <div className="factor-row">
            <span>Sleep</span>
            <div className="factor-bar">
              <div
                className="factor-fill"
                style={{ width: `${contributions.sleep || 0}%` }}
              ></div>
            </div>
            <b>{contributions.sleep || 0}%</b>
          </div>

          <div className="factor-row">
            <span>Deadline</span>
            <div className="factor-bar">
              <div
                className="factor-fill"
                style={{ width: `${contributions.deadline || 0}%` }}
              ></div>
            </div>
            <b>{contributions.deadline || 0}%</b>
          </div>

          <div className="factor-row">
            <span>Posture</span>
            <div className="factor-bar">
              <div
                className="factor-fill"
                style={{ width: `${contributions.posture || 0}%` }}
              ></div>
            </div>
            <b>{contributions.posture || 0}%</b>
          </div>
        </div>

        <div className="top-factor-box">
          Main Overload Driver:{" "}
          <strong>{explainability?.top_factor || "Calculating..."}</strong>
        </div>
      </div>

      {/* Explainability Chart */}
      <div className="chart-card">
        <h2>Factor Contribution Breakdown</h2>
        <Bar data={explainabilityChartData} options={chartOptions} />
      </div>

      {/* Before vs After Chart */}
      <div className="chart-card">
        <h2>Before vs After Cognitive Load</h2>
        <Bar data={chartData} options={chartOptions} />
      </div>

      {/* Real-Time Cognitive Load Timeline */}
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

      {/* Digital Twin Simulator */}
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

      {/* Validation Dashboard */}
      <div className="validation-card">
        <div className="validation-header">
          <div>
            <h2>Validation Dashboard</h2>
            <p>
              Model performance and session-based improvement metrics for
              research validation.
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
            <span>Total Sessions</span>
            <strong>{sessionMetrics.totalSessions ?? 0}</strong>
          </div>

          <div className="validation-box">
            <span>Average Load</span>
            <strong>{sessionMetrics.averageLoad ?? 0}%</strong>
          </div>

          <div className="validation-box">
            <span>Average Improved Load</span>
            <strong>{sessionMetrics.averageImprovedLoad ?? 0}%</strong>
          </div>

          <div className="validation-box">
            <span>Avg Improvement</span>
            <strong>{sessionMetrics.averageImprovement ?? 0}%</strong>
          </div>

          <div className="validation-box">
            <span>Improvement Rate</span>
            <strong>{sessionMetrics.averageImprovementPercent ?? 0}%</strong>
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
            "Validation results will appear after session logs are collected."}
        </p>
      </div>

      {/* Premium Agent Workflow */}
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

      {/* Optimized Plan */}
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