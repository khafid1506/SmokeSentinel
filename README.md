# SmokeSentinel testttttttttttttttttt
SmokeSentinel  — Autonomous QA agent for AI-driven smoke testing. From Jira user story to Gherkin scenarios, Playwright test execution via MCP, AI failure diagnosis, and clear reporting with Slack/Teams alerts. Get a fast health check before regression, E2E, and validation. Built with LangChain, Claude, Docker, CI/CD. 🚧 WIP

# 🛰️ SentinelMCP

> **AI-powered smoke testing — from Jira ticket to test report, autonomously.**

---

## 🚧 Status: Work in Progress

This repository hosts **SentinelMCP**, an autonomous QA agent that handles the full smoke-testing lifecycle — without manual configuration.

```
Jira User Story → Gherkin scenarios → Playwright smoke tests → AI diagnosis → Report & alerts
```

Built on **Playwright MCP** + **LangChain**, orchestrated end-to-end by an LLM agent, and fully containerized with Docker for CI/CD integration.

---

## 💡 Why smoke tests?

Before running full regression suites, E2E tests, or business validation — teams need a **fast, reliable answer** to one question:

> *"Is the application still standing after this deployment?"*

Smoke tests give that answer in minutes, not hours — catching blocking regressions early and freeing up QA time for deeper testing.

**SentinelMCP automates this entire first line of defense.**

---

## ⚙️ What it does (high level)

- 📋 Reads a Jira User Story and generates clean Gherkin test cases
- 🧪 Generates Playwright smoke test scenarios from those specs — zero manual setup
- 🤖 Executes tests via a LangChain agent through Playwright MCP
- 🩺 Diagnoses failures in plain language (root cause hints, severity)
- 📊 Produces a clear, intuitive HTML/Markdown report
- 🚨 Sends Slack/Teams alerts on critical regressions
- 🐳 Runs anywhere via Docker — ready for CI/CD pipelines

---

## 🧰 Stack

`Playwright` · `Playwright MCP` · `Python` · `LangChain` · `Claude / OpenAI` · `Docker` · `Jira` · `CI/CD`

---

## 📌 Coming soon

The full README — architecture diagram, setup instructions, demo, and usage examples — is on its way.

⭐ Star this repo to follow the progress.

---

*Built by [Khalid Hafid-Medheb](https://www.linkedin.com/in/khalid-hafid-medheb-40451aa8/) — Founder of [Kallitests](https://github.com/khafidmedheb), Senior SDET & AI Engineer specialized in autonomous QA agents (HealthTech / BioTech).*
