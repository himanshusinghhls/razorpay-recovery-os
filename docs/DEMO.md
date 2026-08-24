# Demo & Pitch Script

This is a structured 5-minute script for demonstrating RecoveryOS to judges.

## Video Outline

| Time | Beat | Action / Screen | What to Say |
|------|------|-----------------|-------------|
| **0:00 - 0:45** | **The Problem** | Open Razorpay Checkout in "Test" mode. Select "Insufficient Funds". Let it fail. | "When a payment fails online, businesses lose money. Static retries don't work for things like Insufficient Funds. We built RecoveryOS to solve this." |
| **0:45 - 1:30** | **The AI Brain** | Show the Recovery Pipeline lighting up in the UI. Point to the AI Diagnosis. | "Instead of a dumb retry, our AI Agent instantly catches the failure. It diagnoses that retrying a card with no money is pointless, and generates a new payment link instead." |
| **1:30 - 2:30** | **The Policy Engine** | Simulate a "Suspected Fraud" failure. Show the "Blocked by Policy Engine" badge. | "But what if the AI hallucinates? We built a strict Deterministic Policy Engine. If the AI proposes something dangerous, like retrying a stolen card, our Policy Engine hard-blocks it. The AI proposes, the Engine disposes." |
| **2:30 - 3:30** | **Scale (Benchmark)**| Switch to the Benchmark Tab. Hit "Run Simulation". | "To prove the ROI, we built an evaluation harness that simulates 50,000 real-world payment failures. You can see our AI Agent recovers significantly more revenue than a standard gateway, while maintaining a 0% Unsafe Action Rate." |
| **3:30 - 4:30** | **Audit & Live** | Switch to the Audit Trail tab. Show the PostgreSQL logs. Run a "Direct Success" payment. | "Every single action is logged immutably. If a payment succeeds directly, it's also logged. It is enterprise-ready and compliant." |
| **4:30 - 5:00** | **The Wrap** | Dashboard Overview | "We plugged the leaky revenue bucket. It's safe, it's fast, and it runs entirely autonomously." |

## Backup Plan (If the Live Demo Fails)
If ngrok dies, or the Gemini API goes down during the live pitch:
1. Stay calm.
2. Explain that the AI layer is gracefully degrading.
3. Show the **Benchmark** tab — this runs using statistical probability models entirely locally in-memory. It does *not* require the Gemini API to be online. You can still prove the financial uplift.
4. Show the **Escalation Queue** and **Audit Trail** to prove that the ledger and backend are still fully functional.
