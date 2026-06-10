# qwenpaw-ai-agent-competition

Team project repository for the "千模百炼 AI 开发者学生竞赛".

## Project Overview

An AI-powered travel companion for exploring Macau's historic districts. Delivered as a WeChat Mini Program / mobile app, it provides real-time location-based commentary, intelligent route planning, and a gamified experience for tourists.

## Core Features

### 1. Historic District Guide (核心：旧区位置讲解)
- **Location-aware commentary**: When users enter a district, the app generates contextual descriptions (history, landmarks, culture) based on their current location.
- **Audio narration**: All content is delivered with voice commentary.
- **Tour route generation**: Automatically creates optimized walking routes with guided narration.

### 2. Intelligent Route Planning (核心路线规划)
- **Route optimization**: Combines local attractions and trending spots into curated routes.
- **Dynamic adjustments**: Fine-tunes routes based on crowd levels, weather, and seasonality.
- **Map visualization**: Highlights key stops and connections on a map; tapping a stop reveals a timeline with detailed content.
- **Itinerary view**: A memo-style trip plan for easy reference.
- **Gamification**: Check-in points to encourage exploration (similar to Duolingo's engagement model).

#### Input Factors
- Real-time crowd levels (人流)
- Weather conditions (天气)
- Optimal local routes (本身地区的最优化路线)
- User-defined travel type and purpose (用户自定义的旅游类型和目的)
- Macau festivals and cultural events (澳门节庆和文化活动)
- Casino shuttle bus routes (发财车路线)

### 3. User Management (基础功能)
- **Registration & Login**: Collects name, contact (email/phone), origin country, language preference, visit duration, and travel type (solo, family, post-conference leisure).
- **Preference Checklist**: Understands what the user wants to explore in Macau (entertainment, culture, history, etc.).
- **Tutorial**: An onboarding video walkthrough of app features.
- **Personal Center**: Profile and trip management.

### 4. Human-in-the-Loop Curation (人工调度)
- **Offline research data**: Uses the team's existing Xiaohongshu dataset (100 high-engagement notes + 751 comments, 2023–2025) as a static source for POI popularity, pain points, and route priors. No real-time social media monitoring or ongoing crawling in the competition scope.
- **Crowd intelligence**: Monitors crowd levels at ports and attractions when available (via CrowdPass or similar data sources).
- **Manual curation & feedback**: Team-reviewed content updates and in-app user feedback replace live social listening for knowledge iteration.

## Current Stage

Feature and framework design finalized. Moving into implementation.

## Project Goal

Build an interactive AI Agent application prototype based on QwenPaw that delivers a seamless, personalized tour experience for Macau visitors.

## Team Collaboration

- Keep docs updated as decisions become clearer.
- Use `docs/idea-pool.md` to collect and compare project ideas.
- Use `docs/team-roles.md` to clarify ownership and collaboration boundaries.
- Keep frontend, backend, RAG, assets, and scripts work in their dedicated folders.
- Prefer small, frequent commits with clear commit messages.
- Discuss major architecture, product, and competition-track decisions before implementation.
