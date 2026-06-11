# AI Ethics and Policy Considerations for the Macao Smart Travel Guide Project

## 1. Project Scope and AI Use Cases

This project plans to use Alibaba's QwenPaw Agent as its core AI capability, delivered through a mobile app or WeChat Mini Program, to provide smart travel guidance for visitors to Macao. Planned features include registration and preference collection, location-based guidance in historic districts, AI-generated multilingual text and audio explanations based on user photos, personalised route planning, decision support using crowd and weather information, saved itineraries, arrival greetings, local food recommendations, and gamified check-ins through a check-in wall.

The project may use AI for natural language generation, multilingual translation, speech synthesis, image understanding, route and recommendation decisions, crowd trend analysis, user preference modelling, and agent-based task orchestration. This document focuses on the ethical, privacy, safety, cultural, and governance issues that may arise from those capabilities in the Macao tourism context, and sets out policy and control measures for implementation.

## 2. Guiding Principles

The competition guidelines highlight four priorities: respect for interviewees, information accuracy, cultural sensitivity, and transparent labelling. Drawing on IBM's discussion of trustworthy AI, including explainability, fairness, robustness, transparency, and privacy, as well as SAP's emphasis on human well-being, human oversight, bias management, privacy and security, inclusion, and continuous monitoring, this project adopts the following principles:

1. Put visitor safety and independent decision-making first. AI should support decisions; it should not replace the judgement of visitors, tour guides, public authorities, or emergency services.
2. Collect only what is necessary. The system should collect only the data needed to provide the requested functions, and should treat location data, photos, movement traces, flight and hotel details, and contact information as highly sensitive data.
3. Be transparent, explainable, and easy to opt out of. Users should know which content is AI-generated, what data is being used, and why a recommendation is being made. They should be able to turn off personalisation, withdraw consent, or delete their data.
4. Keep information accurate, traceable, and correctable. Historical and cultural content should distinguish between historical records, official information, folklore, and AI inference. Higher-risk content should be backed by reliable sources or reviewed by a human.
5. Respect Macao's cultural diversity. Explanations should work across Chinese, Portuguese, Cantonese, English, and other language contexts. The system should not reduce Macao to a gambling label, nor should it make stereotyped recommendations based on country or region, age, spending power, language, or travel style.
6. Maintain human oversight and accountability. The project team should assign clear responsibility for data, models, content, compliance, and user feedback, and should maintain review, logging, appeal, and incident response processes.

## 3. Key Ethical Risks and Governance Measures

| Scenario | Data or AI capability involved | Main risks | Governance measures |
| --- | --- | --- | --- |
| Registration and preference settings | Name, arrival date, length of stay, language, country or region, travel interests, travel type, email address, or phone number | Overcollection, stereotyped recommendations based on nationality or spending preferences, leakage of contact details | Limit mandatory fields to account identification and basic language settings; make travel interests, country or region, and arrival date optional; state the purpose and retention period clearly; allow users to edit, export, and delete account data |
| Location-based guidance and map cookies | Real-time location, route history, arrival status, map cookies | Continuous tracking, leakage of movement history, users mistaking the system for public-safety-level monitoring | Request location permission through a separate notice; use real-time location only during guidance by default; avoid long-term storage of precise movement traces; blur or delete routes after the trip; provide a manual location selection mode |
| Photo-based explanations | User-uploaded photos, image recognition, text generation, speech synthesis | Capturing bystanders, licence plates, children, or private spaces; misleading explanations caused by recognition errors; photos being reused for training or other purposes | Warn users before upload not to capture other people's faces or private areas; apply local or server-side redaction where needed; do not perform face recognition or identity recognition; use photos only for the current explanation by default and exclude them from training unless explicit separate consent is obtained |
| Historical and cultural explanations | Official materials, open data, resident oral histories, AI-generated content | Confusing historical facts with legends, amplifying misinformation, presenting one-sided views of history, religion, communities, or the gaming industry | Label the source type for each explanation; clearly distinguish folklore, oral recollections, and AI-generated additions; use neutral, respectful, non-sensational language for sensitive topics; maintain a human-reviewed knowledge base for important attractions |
| Oral history from local residents | Audio recordings, transcripts, names, ages, community experiences | Use without consent, exposure of personal experiences, harm caused by secondary sharing | Explain the purpose, display scope, retention period, and withdrawal method before interviews; obtain explicit consent; anonymise by default; do not publish, or else redact, details about family, health, home address, financial circumstances, and similar matters; keep consent records |
| Multilingual and audio guidance | Translation, speech synthesis, preferences of visitors from different countries or regions | Translation errors, cultural offence, incorrect action guidance delivered by audio | Maintain glossaries for high-frequency languages such as Chinese, English, Portuguese, and Cantonese; use official or widely accepted translations for key cultural terms; use template-based wording for navigation and safety notices; conduct multilingual sampling checks before launch |
| Route planning | Crowd levels, weather, festivals, map routes, user interests, hotel or casino shuttle routes, flight and hotel information | Recommending unsafe or unreachable routes; ignoring the needs of older adults, children, or wheelchair users; overreliance on predictions | Show constraints and uncertainty in route suggestions; provide modes such as less walking, family-friendly, accessible, avoid crowds, and culture-first; preserve the user's ability to adjust points manually; when weather or transport conditions change, tell users to rely on official real-time information |
| Crowd prediction and social media popularity | Border checkpoint crowds, attraction crowds, weather, festival data, public popularity signals from Xiaohongshu, Douyin, Zhihu, and similar platforms | Scraping in breach of platform rules, inferring individual behaviour from social media popularity, biased popularity signals pushing visitors toward overly commercial or influencer-driven routes | Prefer official, licensed, or aggregated data; comply with platform terms and robots.txt rules; process only aggregated popularity signals; do not store personal accounts, comment profiles, or user identities; label results as estimates rather than facts |
| Food and spending recommendations | User budget, cuisine preferences, location, opening hours, booking information | Commercial bias, undisclosed advertising, price discrimination, excessive collection of payment or booking information | Clearly distinguish algorithmic recommendations, sponsored or partner content, and user favourites; do not apply unfair differentiated pricing based on nationality, device, or spending capacity; route bookings through third-party platforms where possible and do not store payment credentials |
| Check-in wall and gamification | Attraction check-ins, check-in photos, points, or streak records | Encouraging excessive use, revealing movements publicly, unhealthy engagement by minors | Make check-ins private by default; require a second confirmation before public sharing; limit social display and streak-based incentives for minor accounts; provide a switch to turn off gamified prompts |

## 4. User Data Policy

The project should explain its data processing rules in clear language when users first open the service, request permissions, or trigger sensitive functions. Data should be managed in four categories:

1. Account and contact information: email addresses, phone numbers, or other identifiers should be used only for login, security verification, and account recovery. They should not be used for marketing unless the user actively subscribes.
2. Travel preferences and itinerary information: arrival date, length of stay, interests, travel type, flights, and hotel details should be used only to generate routes and reminders. Flight and hotel information should be optional; users should still be able to use basic guidance without providing it.
3. Location and image data: real-time location, photos, and route traces are highly sensitive data. By default, they should be used only for the current session or current trip. Precise route traces should not be retained long term, and photos should not be included in training data by default.
4. Oral history and community materials: interview materials should be used only after separate consent from interviewees, with the scope of authorisation recorded. Content involving privacy or identifiable personal details should be anonymised.

User rights should include the ability to view saved data, correct data, withdraw consent, turn off personalised recommendations, delete itineraries and accounts, report inaccurate content, and request correction of information about themselves. If the project involves cross-border transfers of personal data, changes to the original collection purpose, processing of sensitive data, or extended retention periods, it should conduct a compliance assessment under Macao's Personal Data Protection Act and the requirements of the Personal Data Protection Bureau. If the service provides generative AI to the public in mainland China or processes personal information of individuals in mainland China, the project should also consider the Personal Information Protection Law and the Interim Measures for the Management of Generative AI Services, including requirements on necessity, separate consent, transparency in automated decision-making, personal information protection obligations, accuracy of generated content, and complaint handling.

## 5. Generated Content Policy

AI-generated content should follow these rules:

1. Clear labelling: pages, audio, and itineraries should state that the content is AI-assisted and may contain omissions or errors. For dynamic information such as opening hours, ticket prices, transport, weather, crowd levels, and border clearance, users should be told to rely on official channels or on-site notices.
2. Source classification: historical and cultural content should be classified as official materials, academic or published materials, oral history, public online materials, or AI-synthesised content. When multiple source types are combined, the source types should remain visible.
3. Careful expression of uncertainty: predictive content must not be presented as fact. The system should say "expected to be crowded", "estimated based on public popularity signals", or "allow extra time for border clearance", rather than "it will definitely be crowded".
4. Sensitive topics: topics such as the history of the gaming industry, colonial history, religious sites, communities, and language identity should be handled in objective, respectful, non-inflammatory, and non-discriminatory language. The system must not encourage gambling, illegal currency exchange, fare evasion, entry into restricted areas, or other unlawful conduct.
5. Safety boundaries: the system should not provide professional advice on medical, legal, investment, immigration, or gambling-related decisions. If users encounter illness, become lost, face sudden severe weather, experience a traffic incident, or feel unsafe, the system should direct them to official hotlines, on-site staff, or emergency services.
6. Correction process: each explanation and route suggestion should include a way to report an error. The system should record the issue type, trigger location, model version, input summary, and resolution.

## 6. Fairness, Inclusion, and Cultural Sensitivity

Macao receives a wide range of visitors, including travellers from mainland China, Hong Kong and Macao residents, Portuguese-speaking visitors, English-speaking visitors, families with children, older adults, business travellers attending events or conferences, people with limited mobility, and first-time visitors. The recommendation system should not serve only high-spending users or popular routes, and should not lock users from a particular country, region, or language group into a narrow set of spending or attraction categories.

The project should support different route goals, such as history and culture, family-friendly travel, accessibility, short visits, indoor rainy-day options, low-budget travel, local small businesses, festivals, and avoiding crowds. For people with limited mobility, the system should prioritise information on slopes, stairs, walking distance, public transport transfers, and toilets. For language and cultural differences, it should avoid joking or sensational descriptions of religions, temples, Portuguese-style architecture, the gaming industry, or community life.

## 7. Human Oversight and Project Governance

The project team should establish a lightweight but enforceable governance process:

1. Responsibilities: appoint owners for data protection, content review, model and safety work, and user feedback.
2. Pre-launch assessment: conduct an AI risk assessment for each new feature, focusing on whether it introduces sensitive personal data, automated decision-making, cross-border data transfer, use by minors, publication of oral history, or high-impact recommendations.
3. Content review: review attraction knowledge bases, gaming-related content, historically sensitive content, oral history materials, and multilingual templates before launch. For real-time AI-generated content, use mechanisms such as sensitive-term detection, fact checks, and source prompts.
4. Logs and audits: retain the system logs needed for security investigation and issue reproduction, but de-identify them and avoid storing full photos, precise movement traces, or highly sensitive inputs.
5. Vendor management: define data processing boundaries, retention periods, security measures, and retraining restrictions with QwenPaw, map providers, speech providers, cloud providers, booking partners, and data suppliers.
6. Safety testing: regularly test for prompt injection, unauthorised access, incorrect navigation, privacy leakage, protection of minors, hallucinated content, and multilingual mistranslation.
7. Feedback loop: route user feedback through a tiered handling process. Issues involving safety, privacy, discrimination, unlawful content, or cultural offence should be prioritised, and relevant templates or features should be taken offline where necessary.

## 8. User Notice Examples for the Product

First-use notice:

> This service uses AI to generate Macao travel guidance, routes, and explanations. AI-generated content may contain errors or omissions. Please refer to official channels or on-site notices for opening hours, transport, crowd levels, border clearance, and weather information. You can turn off personalised recommendations, withdraw location or photo permissions, and delete saved itineraries at any time.

Photo upload notice:

> Please avoid uploading photos that clearly show other people's faces, children, licence plates, identity documents, hotel room numbers, or private spaces. Photos are used only for attraction recognition and explanation generation in this session by default, and are not used for model training.

Route planning notice:

> Routes are generated by AI based on your preferences, maps, weather, events, and estimated crowd levels. They are for reference only. You can manually adjust the order of attractions. In the event of traffic control, severe weather, or physical discomfort, please follow on-site staff and official guidance first.

Oral history display notice:

> This content is based on oral history materials authorised by interviewees and has been anonymised. Oral recollections may differ from formal historical records. The system will try to distinguish personal memories, folklore, and historical records.

## 9. References

- IBM: What Is AI Ethics? https://www.ibm.com/cn-zh/think/topics/ai-ethics
- SAP: What Is AI Ethics? The Role of Ethics in AI https://www.sap.com/taiwan/resources/what-is-ai-ethics
- Macao SAR Government: Personal Data Protection Bureau and Personal Data Protection Act service information https://www.gov.mo/zh-hans/services/ps-2039/
- Cyberspace Administration of China: Personal Information Protection Law of the People's Republic of China https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm
- Ministry of Industry and Information Technology: Interim Measures for the Management of Generative AI Services https://www.miit.gov.cn/zcfg/qtl/art/2023/art_f4e8f71ae1dc43b0980b962907b7738f.html
