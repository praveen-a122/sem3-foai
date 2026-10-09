What These 30 Papers Actually Did (In Simple Terms)

Across all 30 papers, researchers explored games as medicine and measurement tools for aging brains. Instead of relying solely on pills or stressful paper-and-pencil tests, they used games for three primary purposes:



Active Therapy (Rehabilitation): Players exercise specific brain circuits (memory, planning, attention) or combine body movement with gaming (exergames) to stimulate blood flow and neuroplasticity.



Stealth Cognitive Testing (Screening): When an older adult plays a game, the software silently tracks reaction speed, errors, eye movements, or tablet tremors. Because the player is having fun, it reduces test anxiety while providing doctors with accurate cognitive data.



Emotional Well-being: Games combat isolation, apathy, and depression by keeping seniors engaged and motivated.



┌────────────────────────────────────────────────────────

│                   FINAL REVISED SHORTLIST (17 PAPERS)                  │

├────────────────────────────────────────────────────────

│ 1. GAME FRONTEND \& TELEMETRY LOGGERS (PyGame / Mobile)                 │

│    • Jadhav \& Vishwakarma (2026) \[P] - Pygame card \& sorting puzzles   │

│    • Sirály et al. (2015) \[P] - Pair-matching game linked to memory    │

│    • Amaro et al. (2024) \[P] - Autobiographical card memory tasks      │

│    • Paletta et al. (2020) \[P] - Eye-gaze tracking reaction trials     │

│                                                                        │

│ 2. MESA ASSESSMENT \& SCREENING AGENTS (Clinical Logic)                 │

│    • Oliveira et al. (2022) \[P] - CogWorldTravel remote CSI scoring    │

│    • Torabgar et al. (2025) \[P] - ML behavioral engagement telemetry   │

│    • Paletta et al. (2021) \[P] - Clinical decision support profiles    │

│                                                                        │

│ 3. MESA ADAPTIVE AGENT \& FEEDBACK LOOP (Dynamic Difficulty)            │

│    • Eun et al. (2022) \[P] - Real-time AI difficulty adjustment        │

│    • Mezrar \& Bendella (2022) \[T] - Preventing dropout \& test anxiety  │

│    • Goumopoulos et al. (2023) \[P] - Multimodal difficulty scaling     │

│    • Choi et al. (2025) \[P] - Frontal lobe progression monitoring      │

│                                                                        │

│ 4. THEORETICAL VALIDATION \& COURSE JUSTIFICATION                       │

│    • Ballesteros et al. (2018) \[T] - Neuroplasticity mechanism         │

│    • Guzmán et al. (2024) \[T] - Cognitive Reserve hypothesis           │

│    • Zhao et al. (2020) \[T] - Baseline efficacy for MCI vs. Dementia   │

│    • Ning et al. (2020) \[T] - Multi-stage dementia assessment model    │

└────────────────────────────────────────────────────────



Complete Shortlist (17 Papers) Segregated by Project Architecture

&#x20;                      MESA MULTI-AGENT ARCHITECTURE

&#x20;┌──────────────────────────────────────────────────────────────────

&#x20;│                                                                                │

&#x20;│   ┌─────────────────┐                 ┌──────────────────┐         │

&#x20;│   │  \[Layer 1] PyGame    │                 │  \[Layer 2] Mesa       │          │

&#x20;│   │  Frontend \& Tasks    │ ──Telemetry───► │  Assessment Agent   │          │

&#x20;│   │  (Reaction, Errors)  │                 │  (MMSE/MoCA Scoring)  │          │

&#x20;│   └─────────────────┘                 **└────────┬─────────┘**         │

&#x20;│              ▲                                         │                      │

&#x20;│              │ Feedback Loop:                          │ Cognitive             │

&#x20;│              │ Difficulty Adaptation                   ▼ Stage Alert          │

&#x20;│   ┌───────┴─────────┐                 ┌──────────────────┐   	  │

&#x20;│   │  \[Layer 3] Mesa      │                 │  \[Layer 4] Theoretical│   		  │

&#x20;│   │  Adaptive Agent      │                 │  Validation Layer     │   		  │

&#x20;│   │  (Fatigue / Anxiety) │                 │  (Reserve/Plasticity) │   		  │

&#x20;│   └─────────────────┘                 └──────────────────┘   	  │

&#x20;└──────────────────────────────────────────────────────────────────







What other ppl are doing and project scope: 

Dr. Sajitha Krishnan's core requirement: dynamic, performance-based difficulty adjustment for elderly users via agentic feedback loops, while elevating the technical scope to clinical digital phenotyping.

An analysis of the Question Pool (Sheet 2) and Case study topics (Sheet 1) reveals the core evaluation criteria and where this project fits into the course expectations:



What Sheet 1 and Sheet 2 Reveal (Base Level Expectations)

Course Context \& Core Evaluator:



Course: 22AIE201: Fundamentals of AI (3rd Sem, B.Tech AIE, Amrita Vishwa Vidyapeetham).



Faculty / Evaluator: Dr. Sajitha Krishnan.



Faculty Directives for Teams (from Sheet 1 notes):



“Find out the dataset... Perform multiagent...”



“Multiagen
t. Refer government sites... feedback loop to ensure the quality”



“Single agent to decide the difficulty level based on the performance — suggesting elder people or adolescent” (Team 3 – AI Chess Bot).



“Smart parking system - MESA github codes” (Team 9).



The Base Requirement:



Mesa is non-negotiable: Every team is expected to build an Agent-Based Model (ABM) using the Python mesa library (defining custom mesa.Agent, mesa.Model, scheduling with BaseScheduler/RandomActivation, and a spatial grid or state space).



Datasets are mandatory: Real-world or benchmark datasets must feed or validate the model parameters rather than using arbitrary hardcoded simulation values.



Where This Fits in the Question Pool (Sheet 2):



The pool explicitly lists:



\#14: Healthcare tracking system



\#28: Memory game



\#36: Making a 2D game



\#38: Web cam based eye tracker (Direct tie-in to Paletta et al. MIRA)



\#41: Matching the tiles (Direct tie-in to Sirály et al. Find-the-Pairs)

