
```markdown
## Generate a Frontend Product Requirements Document (PRD) for MultiDB-Chatbot

### Context & Background
You are analyzing a HIPAA-compliant therapeutic AI chatbot system designed for senior living facilities. The backend architecture includes:
- Multi-database setup (PostgreSQL, MongoDB, Redis, ScyllaDB)
- Microservices architecture with Go business services and Python AI services
- Real-time PHI detection and crisis intervention capabilities
- Comprehensive audit logging and security controls

### Your Role
Act as a **Senior Product Manager and Lead Frontend Architect** with expertise in:
- Healthcare technology and HIPAA compliance visualization
- Accessibility standards (WCAG 2.1 AA) for elderly users
- Modern frontend architectures and state management
- Converting complex backend capabilities into intuitive UIs

### Target Audience
An offshore frontend development team with:
- Strong technical skills in React/Vue/Angular
- Zero knowledge of therapeutic AI or HIPAA regulations
- No prior context about this specific project
- Need for explicit, unambiguous requirements

### Document Requirements

Generate a comprehensive Frontend PRD with the following structure:

#### 1. Executive Summary
- Product vision and Phase 1 objectives
- Key user personas and their primary goals
- Success metrics and KPIs

#### 2. Technical Foundation
- **Architecture Pattern**: Specify frontend architecture (e.g., micro-frontends, monolithic SPA)
- **State Management**: Define approach (Redux, Zustand, Context API)
- **Design System**: Component library requirements and accessibility standards
- **Security Visualization**: How to display HIPAA compliance features to build trust

#### 3. User Flows & Wireframes
For each major flow, provide:
- User journey map
- Low-fidelity wireframe descriptions
- State transitions and error scenarios
- Loading states and fallback UI

#### 4. Detailed Feature Specifications

For each feature, include:
- **Epic/Feature Name**
- **User Stories** (As a... I want... So that...)
- **Acceptance Criteria** (Given... When... Then...)
- **UI Components Required**
- **API Dependencies** (endpoint, request/response format)
- **Error Handling** (validation, network errors, timeouts)
- **Analytics Events** to track

##### Core Features to Detail:
1. **Authentication & Session Management**
   - Login/logout flows
   - Session timeout warnings (visual countdown)
   - Multi-factor authentication UI (future-ready)
   - Password reset flow

2. **Senior Resident Chat Interface**
   - Message composition with real-time PHI detection
   - AI response rendering with typing indicators
   - Citation display for RAG-sourced information
   - Crisis intervention UI state changes
   - Voice input capability (accessibility)
   - Font size/contrast controls

3. **Healthcare Staff Dashboard**
   - Real-time alert feed with severity indicators
   - Resident status grid view
   - Conversation transcript viewer (read-only)
   - Emergency response quick actions
   - Shift handover notes interface

4. **Administrator Control Panel**
   - User management CRUD operations
   - Role assignment interface
   - Audit log viewer with advanced filtering
   - System health monitoring widgets
   - Compliance report generation

5. **HIPAA Compliance Visualizations**
   - PHI access consent status indicators
   - Active audit logging notifications
   - Data encryption status badges
   - Emergency access override UI

#### 5. API Integration Specifications

For each endpoint:
```typescript
// Example format
interface Endpoint {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  path: string;
  headers: Record<string, string>;
  requestBody?: object;
  responseBody: object;
  errorCodes: Array<{code: number, meaning: string}>;
  rateLimit: string;
}
```

#### 6. Non-Functional Requirements
- **Performance**: Specific metrics (FCP, TTI, bundle size limits)
- **Security**: CSP headers, XSS prevention, secure storage
- **Accessibility**: WCAG 2.1 AA with senior-specific enhancements
- **Internationalization**: Language support requirements
- **Browser Support**: Specific versions and graceful degradation
- **Offline Behavior**: Service worker strategy
- **Error Tracking**: Sentry/similar integration requirements

#### 7. Development Guidelines
- **Component Structure**: Atomic design principles
- **Testing Requirements**: Unit, integration, E2E coverage targets
- **Code Quality**: Linting rules, TypeScript strictness
- **Documentation**: Storybook/similar component documentation
- **CI/CD Integration**: Build and deployment requirements

#### 8. Design Assets & Resources
- Brand guidelines and color system
- Typography scale for elderly users
- Icon library requirements
- Micro-interaction patterns
- Loading and empty states

#### 9. Phase 1 Delivery Milestones
- Week 1-2: Design system and authentication
- Week 3-4: Senior resident chat interface
- Week 5-6: Healthcare staff dashboard
- Week 7-8: Admin panel and testing
- Week 9-10: Integration, accessibility audit, and deployment

#### 10. Success Criteria & Metrics
- User engagement metrics
- Performance benchmarks
- Accessibility compliance scores
- Error rate thresholds
- User satisfaction targets

### Additional Instructions:
1. **Be Prescriptive**: Don't say "consider using" - say "implement using X because Y"
2. **Include Rationale**: Explain WHY each requirement exists (HIPAA, UX, performance)
3. **Provide Examples**: Include code snippets, screenshot descriptions, or interaction patterns
4. **Address Edge Cases**: Account for slow networks, large datasets, concurrent users
5. **Define Dependencies**: Clearly state what backend APIs must be ready for each feature

### Deliverable Format:
- Single markdown document with clear hierarchy
- Include a table of contents
- Use diagrams where helpful (mermaid syntax for flow charts)
- Provide a glossary of healthcare/technical terms
- End with a FAQ section addressing likely developer questions
```

Key improvements in this version:

1. **Added Context**: Provides upfront context about the system being built
2. **Clearer Structure**: Separates instructions from expected content sections
3. **More Specificity**: Defines exact technical requirements (state management, error handling)
4. **Added Missing Elements**: Design system, testing, deployment, offline behavior
5. **Better API Specs**: TypeScript interface example for clarity
6. **Prescriptive Guidance**: Explicit instruction to be directive rather than suggestive
7. **Success Metrics**: Added measurable outcomes
8. **Development Timeline**: Included delivery milestones
9. **Edge Cases**: Addressed error states and exceptional flows
10. **Visual Requirements**: Added design system and accessibility enhancements specific to elderly users