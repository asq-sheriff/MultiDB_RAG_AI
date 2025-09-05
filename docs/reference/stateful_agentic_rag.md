Approach Paper: A Stateful Agentic RAG Architecture for an Emotional AI Companion
Prepared for: The Emotional AI Companion Project

Date: September 2, 2025

Subject: Recommended AI architecture to deliver a safe, empathic, and effective emotional companion for seniors.

1. Executive Summary
This document outlines the recommended technical approach for the Emotional AI Companion. The vision is to create a therapeutic assistant that reduces loneliness and anxiety by providing secure, familiar, and evidence-based support. A standard conversational AI or stateless chatbot is insufficient for this purpose.

To meet the project's complex requirements for personalization, continuity, and safety, we recommend a Stateful, Agentic Retrieval-Augmented Generation (RAG) Architecture. This model utilizes a central Router/Dispatcher Agent to analyze user intent and emotional state, delegating tasks to specialized sub-agents that manage specific, evidence-based interventions. This architecture is designed to be proactive, adaptive, and deeply personalized, ensuring that every interaction is not just a conversation, but a meaningful, therapeutic engagement.

2. Vision & Core Principles
The AI companion is designed to be a safe, empathic partner for seniors, distinct from general-purpose chatbots. Its success hinges on embodying three core principles derived from established clinical and psychological research:

Familiarity, Routine, and Continuity: Based on Socioemotional Selectivity and Continuity Theory, the companion must be a stable, predictable presence. It must remember past interactions, reflect the user's personal history, and support daily rituals to reduce cognitive load and build trust.

Evidence-Based Support: The companion's conversational modes must be grounded in proven therapeutic techniques, including Reminiscence Therapy, Behavioral Activation (BA), Affect Labeling, and Pro-Social Scaffolding.

Therapeutic Alliance & Safety: The engine must prioritize the "therapeutic alliance" by demonstrating empathy, positive regard, and collaboration. It must operate within a robust safety framework, capable of identifying distress and executing a consented escalation protocol.

3. Recommended Architecture: Stateful Agentic RAG
A linear, stateless pipeline cannot fulfill the principles above. We recommend a dynamic, multi-agent system that can reason, remember, and act.

This architecture has four key components:

3.1. Stateful Memory: The Core of Continuity
The foundation of the system is a persistent, long-term memory store, as specified in the Conversation-Engine Checklist. This is the agent's "state."

Life Story Graph: Stores key people, places, life events, and proud moments.

Preference Book: Stores routines, favorites (music, food), communication windows, and disliked topics.

This stateful memory is the primary source for the RAG component, allowing the agent to retrieve and use personal context to make every conversation feel continuous and deeply familiar ("Yesterday you mentioned Anita...").

3.2. Router/Dispatcher Agent: The Empathetic "Brain"
This is the central coordinating agent. Every user interaction or scheduled trigger is first processed by the Router. Its primary responsibilities are:

Intent & Affect Detection: It analyzes the user's input to classify their primary intent (reminisce, soothe, practical_info, etc.) and their emotional state (calm, anxious, low).

Strategic Planning (Reasoning): Based on the detected intent, current affect, user's state (memory), and time of day, the Router uses a Chain of Thought process to decide which intervention is most appropriate. It acts as the implementation of the "Alliance Layer" and "Intervention Planner."

Task Delegation (Acting): After planning, it delegates the task to a specialized sub-agent.

3.3. Specialized Sub-Agents: The Intervention Toolkit
These are task-specific agents that the Router can call upon. Each one is an expert in an evidence-based modality:

Reminiscence Agent: Manages guided prompts about the user's past, retrieving cues from the Life Story Graph and optionally integrating media.

Behavioral Activation (BA) Agent: Responsible for delivering morning prompts, afternoon nudges, and evening reflections to encourage simple, rewarding activities.

Social Bridge Agent: Composes and sends messages to human contacts (with consent), acting as a bridge to the user's social network.

Grounding Agent: Initiates brief, calming exercises like guided breathing during moments of detected anxiety.

Safety & Escalation Agent: Constantly monitors for red flag phrases or distress patterns. When triggered, it takes over the conversation and executes the predefined escalation tree (from offering a human call to contacting emergency services).

3.4. Retrieval-Augmented Generation (RAG): The Grounding Mechanism
RAG is not a standalone feature but is embedded within each agent. It ensures that all generated responses are grounded in reliable information.

In the Reminiscence Agent, RAG retrieves specific memories from the Life Story Graph to formulate personalized prompts.

In the BA Agent, RAG retrieves the user's preferences to suggest activities they genuinely enjoy.

In the Safety Agent, RAG retrieves consented emergency contact information and protocols.

4. System Flow in Action: The "Mrs. Lewis" Scenario
Let's trace the "Morning Check-in" from the AI demo.md script through this architecture:

Trigger (08:30): A scheduled check-in is initiated for Mrs. Lewis.

Router Agent Processing:

Windows: morning 07:30–09:30, afternoon 13:30–15:30, evening 19:00–20:30, jitter ±5 min.

Deterministic seed per user → reproducible timing for tests.

Offline: queue nudges and coalesce with polite “missed you” copy on reconnection.

Thought: "It's 08:30, a scheduled check-in. I will retrieve the last session's summary. The state indicates she missed her sister yesterday. Current affect is calm/low. The best initial intent is connect, with a potential branch to reminisce."

Action: Formulate an opening that offers a choice, aligning with the "Alliance Layer" principle. It generates: “...Yesterday you mentioned thinking about your sister. Would it feel nice to revisit a favorite memory, or shall we just ease in with a gentle hello?”

User Response: "Let's talk about my sister. We used to dance to Motown."

Router Agent Delegation:

Thought: "The user has confirmed the reminisce intent. The context 'Motown' is a key anchor. I will now delegate this conversation to the Reminiscence Agent."

Action: The Router passes control to the Reminiscence Agent, along with the current conversational context and access to Mrs. Lewis's memory.

Reminiscence Agent Execution:

The agent takes over, retrieving the song "My Girl" from the Preference Book, playing a clip, and guiding the conversation. It manages the entire 10-minute module.

Closure and State Update:

Upon completion, the Reminiscence Agent hands control back to the Router.

The Router's Stateful Memory is updated: "‘My Girl’ noted as a mood-lift." This information is now available for all future interactions.

5. Conclusion
A simple RAG chatbot can retrieve facts. An Emotional AI Companion must build relationships. The proposed Stateful Agentic RAG Architecture provides the necessary framework for a system that can remember, reason, and act with empathy. By using a central Router to delegate tasks to specialized, evidence-based agents, we can create a companion that is not only intelligent but also safe, effective, and profoundly human-centered. This architecture directly maps to the project's requirements and provides a scalable, robust foundation for achieving the desired therapeutic outcomes.