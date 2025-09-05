---
title: UI/UX Development Requirements - Therapeutic AI Platform
owner: Product Leadership & UI/UX Development Team
last_updated: 2025-09-05
status: authoritative
priority: critical
---

# 🎨 UI/UX Development Requirements - Therapeutic AI Healthcare Platform

> **Comprehensive, prescriptive UI requirements for offshore development team building HIPAA-compliant therapeutic AI interfaces**

## 📋 Table of Contents

1. [Executive Summary & Project Context](#-executive-summary--project-context)
2. [Technology Foundation Requirements](#-technology-foundation-requirements)
3. [Prioritized Feature Requirements](#-prioritized-feature-requirements)
4. [API Integration Specifications](#-api-integration-specifications)
5. [Security & Compliance Requirements](#-security--compliance-requirements)
6. [Accessibility & Senior-Friendly Design](#-accessibility--senior-friendly-design)
7. [Performance & Technical Requirements](#-performance--technical-requirements)
8. [Testing & Quality Assurance](#-testing--quality-assurance)
9. [Development Guidelines & Standards](#-development-guidelines--standards)
10. [Implementation Timeline & Milestones](#-implementation-timeline--milestones)

---

## 🎯 Executive Summary & Project Context

### Project Overview
**CRITICAL BUSINESS CONTEXT**: You are building user interfaces for a **HIPAA-compliant therapeutic AI system** that serves **elderly residents** in senior living facilities and Medicare Advantage health plans. This is a **healthcare safety-critical system** where UI failures can directly impact patient wellbeing and regulatory compliance.

### Primary User Types & UI Priorities

#### **🚨 PRIORITY 1: Senior Residents (Ages 65-95)**
- **UI Needs**: Extra-large fonts (22px+), high contrast, voice input, crisis intervention UI
- **Technology Comfort**: Low to moderate
- **Safety Requirement**: Crisis detection must trigger immediate, obvious emergency UI

#### **🚨 PRIORITY 2: Healthcare Staff (Licensed Professionals)**
- **UI Needs**: Real-time alerts, mobile-friendly dashboards, quick action buttons
- **Technology Comfort**: Moderate to high
- **Compliance Requirement**: All patient interactions must be logged and auditable

#### **🚨 PRIORITY 3: System Administrators (Healthcare IT)**
- **UI Needs**: Comprehensive admin panels, audit trails, system monitoring
- **Technology Comfort**: High
- **Regulatory Requirement**: Complete HIPAA compliance visualization and reporting

### Business Success Metrics
- **Senior Engagement**: 80%+ daily usage among registered residents
- **Crisis Response**: <30 seconds from crisis detection to staff alert
- **Regulatory Compliance**: 100% HIPAA audit compliance
- **Accessibility**: WCAG 2.1 AA + senior-specific enhancements

---

## 🏗️ Technology Foundation Requirements

### **MANDATORY Technology Stack**

#### **Frontend Framework: React 18+ with TypeScript (REQUIRED)**
```typescript
// Required package.json dependencies
{
  "react": "^18.2.0",
  "typescript": "^5.0.0",
  "@types/react": "^18.0.0",
  "react-router-dom": "^6.8.0"
}
```
**Rationale**: React provides mature accessibility tools essential for elderly users, TypeScript prevents runtime errors with healthcare data

#### **State Management: Zustand + TanStack Query (REQUIRED)**
```typescript
// Global state interface - IMPLEMENT EXACTLY AS SPECIFIED
interface AppState {
  auth: {
    user: UserProfile | null;
    token: string | null;
    role: 'resident' | 'staff' | 'admin';
    permissions: Permission[];
  };
  chat: {
    messages: ChatMessage[];
    isTyping: boolean;
    activeCrisis: CrisisAlert | null;
    sessionId: string;
  };
  alerts: {
    critical: Alert[];
    high: Alert[];
    medium: Alert[];
  };
  accessibility: {
    fontSize: 'normal' | 'large' | 'extra-large';
    contrast: 'normal' | 'high';
    voiceEnabled: boolean;
    screenReader: boolean;
  };
}
```

#### **UI Library: Mantine v7 with Healthcare Theme (REQUIRED)**
```typescript
// Healthcare-optimized theme configuration
const therapeuticTheme: MantineThemeOverride = {
  fontSizes: {
    xs: 18,    // Minimum for seniors
    sm: 22,    // Preferred default
    md: 26,    // Large text mode
    lg: 32,    // Extra large mode
    xl: 40     // Maximum size
  },
  colors: {
    // Trust-building healthcare blues
    blue: ['#e3f2fd', '#bbdefb', '#90caf9', '#64b5f6', '#42a5f5', '#2196f3', '#1e88e5', '#1976d2', '#1565c0', '#0d47a1'],
    // Crisis intervention reds
    red: ['#ffebee', '#ffcdd2', '#ef9a9a', '#e57373', '#ef5350', '#f44336', '#e53935', '#d32f2f', '#c62828', '#b71c1c'],
    // Success/wellness greens  
    green: ['#e8f5e8', '#c8e6c9', '#a5d6a7', '#81c784', '#66bb6a', '#4caf50', '#43a047', '#388e3c', '#2e7d32', '#1b5e20']
  },
  spacing: {
    xs: 8,
    sm: 16,    // Minimum touch target spacing
    md: 24,    // Standard spacing
    lg: 32,    // Section spacing
    xl: 48     // Page-level spacing
  },
  radius: {
    xs: 4,
    sm: 8,     // Standard UI elements
    md: 12,    // Cards and panels
    lg: 16,    // Large elements
    xl: 24     // Extra large elements
  }
};
```

#### **Security Configuration (CRITICAL - IMPLEMENT EXACTLY)**
```typescript
// Content Security Policy - HEALTHCARE COMPLIANCE REQUIRED
const CSP_CONFIG = {
  'default-src': ["'self'"],
  'script-src': ["'self'", "'unsafe-inline'"],  // Minimal for XSS protection
  'style-src': ["'self'", "'unsafe-inline'"],   // Required for Mantine
  'img-src': ["'self'", "data:", "https:"],     // Profile images
  'connect-src': ["'self'", "wss:", "ws:", "http://localhost:8000", "http://localhost:8080"], // API endpoints
  'media-src': ["'self'"],                      // Voice input
  'object-src': ["'none'"],                     // Security hardening
  'frame-src': ["'none'"],                      // No iframe embedding
  'base-uri': ["'self'"]                        // Prevent base tag injection
};

// Storage restrictions - CRITICAL FOR PHI PROTECTION
const STORAGE_RULES = {
  localStorage: 'authentication_tokens_only',   // NO PHI ever
  sessionStorage: 'ui_preferences_only',        // NO PHI ever
  cookies: 'session_id_only',                   // NO PHI ever
  indexedDB: 'prohibited',                      // NO client-side PHI storage
  webSQL: 'prohibited'                          // Deprecated and insecure
};
```

#### **Build System: Vite with Healthcare Compliance (REQUIRED)**
```typescript
// vite.config.ts - IMPLEMENT EXACTLY
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom'],
          'vendor-ui': ['@mantine/core', '@mantine/hooks'],
          'vendor-auth': ['@auth0/auth0-spa-js'],  // Or selected auth library
          'chat-features': ['socket.io-client'],
          'voice-features': ['react-speech-to-text']
        }
      }
    },
    chunkSizeWarningLimit: 1000,  // Healthcare bundle compliance
    sourcemap: false              // No source maps in production (security)
  },
  define: {
    __HIPAA_COMPLIANT__: true,
    __PHI_LOGGING_DISABLED__: true,
    __CRISIS_DETECTION_ENABLED__: true
  },
  server: {
    https: true  // HTTPS required for voice input and healthcare compliance
  }
});
```

---

## 🎯 Prioritized Feature Requirements

### **🚨 PRIORITY 1: Crisis Detection & Safety UI (Weeks 1-2)** ✅ **COMPLETED**
**BUSINESS JUSTIFICATION**: Patient safety is non-negotiable. Crisis detection UI failures can result in preventable harm to elderly residents.
**IMPLEMENTATION STATUS**: ✅ **FULLY IMPLEMENTED** - All crisis detection and safety UI components operational

#### **Feature 1.1: Crisis Intervention Modal System** ✅ **IMPLEMENTED**
**File Location**: `/apps/web/src/components/crisis/CrisisInterventionModal.tsx`
**Implementation Notes**: Fully compliant with specifications, enhanced with 80px touch targets and ARIA accessibility

```typescript
// ✅ IMPLEMENTED - Crisis intervention modal with all required features
interface CrisisInterventionModal {
  trigger: 'keyword_detection' | 'emotional_pattern' | 'staff_override';
  severity: 'low' | 'medium' | 'high' | 'critical';
  
  // ✅ UI behavior requirements - IMPLEMENTED
  display: {
    zIndex: 9999;                    // Above all other content
    backgroundColor: 'rgba(220, 38, 38, 0.95)';  // Semi-transparent red
    fontSize: '28px';               // Extra large for visibility
    padding: '32px';               // Generous spacing
    borderRadius: '16px';
    animation: 'urgent-pulse';     // Attention-getting animation
  };
  
  // ✅ Required action buttons - EXACT text implemented with 80px touch targets
  actions: [
    { text: 'Call 988 (Crisis Hotline)', action: 'external_call', priority: 'critical' },
    { text: 'Contact Care Team NOW', action: 'staff_alert', priority: 'critical' },
    { text: 'I Need Help Right Now', action: 'emergency_protocol', priority: 'critical' },
    { text: 'I\'m Safe, Continue Chat', action: 'crisis_resolved', priority: 'secondary' }
  ];
  
  // ✅ Auto-actions - All implemented with PHI-compliant logging
  autoActions: [
    'log_crisis_event',
    'alert_healthcare_staff', 
    'record_audio_if_enabled',  // For quality assurance
    'disable_regular_chat'      // Until crisis resolved
  ];
}
```

#### **Feature 1.2: Emergency Contact System**
```typescript
// Emergency contact UI - Accessible from any screen
interface EmergencyContactSystem {
  // ALWAYS visible emergency button
  emergencyButton: {
    position: 'fixed';
    bottom: '24px';
    right: '24px'; 
    width: '80px';
    height: '80px';
    backgroundColor: '#dc2626'; // Emergency red
    borderRadius: '50%';
    fontSize: '32px';
    color: 'white';
    zIndex: 1000;
    ariaLabel: 'Emergency help - Call for immediate assistance';
    clickAction: 'show_emergency_options';
  };
  
  emergencyOptions: [
    { text: '🚨 Call 911', action: 'dial_911' },
    { text: '💙 Call Care Team', action: 'contact_staff' },
    { text: '📞 Call Family', action: 'contact_family' },
    { text: '🆘 Crisis Hotline (988)', action: 'dial_988' }
  ];
}
```

### **🎯 PRIORITY 2: Senior-Friendly Authentication (Weeks 1-2)**

#### **Feature 2.1: Accessible Login Interface**
```typescript
// Senior-optimized login form
interface AccessibleLoginForm {
  layout: {
    maxWidth: '600px';
    padding: '48px';
    fontSize: '22px';           // Base font size
    lineHeight: '1.6';          // Easier reading
    spacing: '24px';            // Between form elements
  };
  
  // Form fields with senior-friendly design
  fields: {
    email: {
      label: 'Your Email Address';
      placeholder: 'example@email.com';
      fontSize: '22px';
      height: '56px';           // Large touch target
      border: '2px solid #d1d5db';
      borderRadius: '8px';
      autocomplete: 'email';
    };
    
    password: {
      label: 'Your Password';
      showPasswordToggle: true;  // Large, clear toggle
      fontSize: '22px';
      height: '56px';
      border: '2px solid #d1d5db';
      borderRadius: '8px';
    };
  };
  
  // Accessibility features
  accessibility: {
    focusIndicator: '3px solid #2563eb';  // High-visibility focus
    errorMessages: {
      fontSize: '20px';
      color: '#dc2626';
      ariaLive: 'polite';
    };
    loadingState: {
      spinnerSize: '32px';
      loadingText: 'Signing you in, please wait...';
    };
  };
  
  // Remember me option
  rememberMe: {
    defaultChecked: true;       // Convenience for seniors
    label: 'Stay signed in for 30 days';
    fontSize: '18px';
  };
}
```

#### **Feature 2.2: Accessibility Setup Wizard**
```typescript
// First-time setup for accessibility preferences
interface AccessibilitySetupWizard {
  steps: [
    {
      title: 'Choose Your Text Size';
      options: [
        { label: 'Normal (18px)', preview: 'This is normal text size', value: 'normal' },
        { label: 'Large (22px)', preview: 'This is large text size', value: 'large' },
        { label: 'Extra Large (28px)', preview: 'This is extra large text', value: 'extra-large' }
      ];
      defaultSelection: 'large';
    },
    {
      title: 'Choose Your Display Style';
      options: [
        { label: 'Standard Colors', preview: 'colored_preview_card', value: 'normal' },
        { label: 'High Contrast', preview: 'high_contrast_preview_card', value: 'high' }
      ];
      defaultSelection: 'normal';
    },
    {
      title: 'Voice Input (Optional)';
      description: 'Would you like to speak your messages instead of typing?';
      options: [
        { label: 'Enable Voice Input', value: true },
        { label: 'Type Only', value: false }
      ];
      defaultSelection: false;  // Opt-in for privacy
    }
  ];
  
  // Save preferences and show confirmation
  completion: {
    message: 'Your preferences have been saved. You can change these anytime in Settings.';
    nextAction: 'redirect_to_chat';
  };
}
```

### **🎯 PRIORITY 3: Therapeutic Chat Interface (Weeks 3-4)**

#### **Feature 3.1: Main Chat Interface**
```typescript
// Core chat interface for therapeutic conversations
interface TherapeuticChatInterface {
  layout: {
    header: {
      height: '80px';
      backgroundColor: '#f8fafc';
      content: 'Your AI Companion | Settings | Help';
      emergencyButton: 'always_visible';
    };
    
    messageArea: {
      height: 'calc(100vh - 240px)';
      padding: '24px';
      backgroundColor: '#ffffff';
      scrollBehavior: 'smooth';
      autoScroll: 'to_bottom_on_new_message';
    };
    
    inputArea: {
      height: '160px';
      padding: '24px';
      backgroundColor: '#f8fafc';
      borderTop: '1px solid #e5e7eb';
    };
  };
  
  // Message display components
  messageDisplay: {
    userMessage: {
      alignment: 'right';
      backgroundColor: '#dbeafe';
      color: '#1e40af';
      borderRadius: '18px 18px 4px 18px';
      padding: '16px 20px';
      maxWidth: '70%';
      fontSize: 'user_preference';  // From accessibility settings
    };
    
    aiMessage: {
      alignment: 'left';
      backgroundColor: '#f3f4f6';
      color: '#374151';
      borderRadius: '18px 18px 18px 4px';
      padding: '16px 20px';
      maxWidth: '80%';
      fontSize: 'user_preference';
      
      // Source citations for RAG responses
      citations: {
        display: true;
        style: 'compact_list_below_message';
        format: '📚 Source: [title] | Medical disclaimer: "This is not medical advice"';
      };
    };
    
    systemMessage: {
      alignment: 'center';
      backgroundColor: '#fef3c7';
      color: '#92400e';
      borderRadius: '12px';
      padding: '12px 16px';
      fontSize: '18px';
      fontStyle: 'italic';
    };
  };
  
  // Input methods
  inputMethods: {
    textInput: {
      placeholder: 'Type your message here...';
      minHeight: '56px';          // Large touch target
      fontSize: 'user_preference';
      padding: '16px';
      borderRadius: '12px';
      border: '2px solid #d1d5db';
      resize: 'vertical';         // Allow expansion
      maxLength: 2000;           // Reasonable limit
    };
    
    voiceInput: {
      enabled: 'user_preference';
      button: {
        size: '56px';
        backgroundColor: '#3b82f6';
        color: 'white';
        borderRadius: '50%';
        ariaLabel: 'Voice input - Tap and speak';
      };
      
      // Voice input states
      states: {
        idle: { icon: 'microphone', color: '#3b82f6' };
        listening: { icon: 'microphone', color: '#dc2626', animation: 'pulse' };
        processing: { icon: 'spinner', color: '#f59e0b' };
        error: { icon: 'exclamation', color: '#dc2626' };
      };
    };
    
    sendButton: {
      size: '56px';
      backgroundColor: '#10b981';
      color: 'white';
      borderRadius: '50%';
      ariaLabel: 'Send message';
      disabled: 'when_message_empty';
    };
  };
  
  // PHI detection warning system
  phiDetection: {
    triggers: ['ssn_pattern', 'phone_number', 'address', 'medical_record_number'];
    warningModal: {
      title: 'Protect Your Privacy';
      message: 'We detected personal information in your message. For your privacy and security, please avoid sharing sensitive details like Social Security numbers, addresses, or phone numbers.';
      actions: [
        { text: 'Edit Message', action: 'return_to_input' },
        { text: 'Learn More', action: 'show_privacy_info' }
      ];
    };
  };
}
```

#### **Feature 3.2: Crisis Detection Visual States**
```typescript
// Visual states when crisis is detected
interface CrisisDetectionStates {
  // Normal chat state
  normal: {
    messageAreaBorder: '1px solid #e5e7eb';
    backgroundColor: '#ffffff';
    inputPlaceholder: 'Type your message here...';
  };
  
  // Crisis detected state
  crisisDetected: {
    messageAreaBorder: '3px solid #dc2626';    // Red alert border
    backgroundColor: '#fef2f2';                // Light red background
    alertBanner: {
      text: '🚨 We\'re concerned about you. Help is available.';
      backgroundColor: '#dc2626';
      color: 'white';
      fontSize: '20px';
      padding: '16px';
      animation: 'gentle-pulse';
    };
    inputPlaceholder: 'If you need immediate help, click the emergency button below';
    inputDisabled: true;  // Prevent further conversation until addressed
  };
  
  // Crisis resolved state  
  crisisResolved: {
    messageAreaBorder: '1px solid #10b981';    // Green confirmation border
    backgroundColor: '#f0fdf4';                // Light green background
    confirmationMessage: {
      text: '💚 Thank you for letting us know you\'re safe. We\'re here if you need anything.';
      backgroundColor: '#10b981';
      color: 'white';
      fontSize: '18px';
      padding: '16px';
    };
    followUpScheduled: true;  // Schedule check-in
  };
}
```

### **🎯 PRIORITY 4: Healthcare Staff Dashboard (Weeks 5-6)**

#### **Feature 4.1: Real-Time Alert System**
```typescript
// Healthcare staff alert dashboard
interface StaffAlertDashboard {
  layout: {
    alertFeed: {
      width: '40%';
      height: '100vh';
      position: 'fixed';
      left: 0;
      backgroundColor: '#ffffff';
      borderRight: '1px solid #e5e7eb';
      overflowY: 'auto';
    };
    
    mainContent: {
      width: '60%';
      marginLeft: '40%';
      padding: '24px';
    };
  };
  
  // Alert priority system
  alertTypes: {
    critical: {
      backgroundColor: '#dc2626';
      color: 'white';
      borderLeft: '6px solid #991b1b';
      icon: '🚨';
      sound: 'urgent_beep';
      autoExpand: true;
      requiresAcknowledgment: true;
    };
    
    high: {
      backgroundColor: '#f59e0b';
      color: 'white'; 
      borderLeft: '6px solid #d97706';
      icon: '⚠️';
      sound: 'attention_chime';
      autoExpand: false;
    };
    
    medium: {
      backgroundColor: '#3b82f6';
      color: 'white';
      borderLeft: '6px solid #1d4ed8'; 
      icon: 'ℹ️';
      sound: 'none';
      autoExpand: false;
    };
  };
  
  // Alert card structure
  alertCard: {
    height: 'auto';
    minHeight: '120px';
    padding: '16px';
    marginBottom: '8px';
    borderRadius: '8px';
    
    header: {
      fontSize: '18px';
      fontWeight: 'bold';
      marginBottom: '8px';
    };
    
    content: {
      residentName: 'prominent_display';
      roomNumber: 'secondary_info';
      timestamp: 'relative_time';  // "2 minutes ago"
      alertReason: 'clear_description';
    };
    
    actions: [
      { text: 'Acknowledge', style: 'primary', action: 'acknowledge_alert' },
      { text: 'View Details', style: 'secondary', action: 'show_detail_modal' },
      { text: 'Contact Resident', style: 'urgent', action: 'initiate_contact' }
    ];
  };
  
  // Real-time updates
  realTimeUpdates: {
    websocketConnection: 'required';
    updateFrequency: '1_second';
    connectionStatus: 'visible_indicator';
    offlineMode: 'show_last_known_state';
    reconnection: 'automatic_with_exponential_backoff';
  };
}
```

#### **Feature 4.2: Resident Status Grid**
```typescript
// Visual overview of all residents
interface ResidentStatusGrid {
  gridLayout: {
    columnsDesktop: 6;      // 6 residents per row on desktop
    columnsTablet: 4;       // 4 residents per row on tablet
    columnsMobile: 2;       // 2 residents per row on mobile
    gap: '16px';
    padding: '24px';
  };
  
  // Resident status card
  residentCard: {
    width: '180px';
    height: '220px';
    borderRadius: '12px';
    padding: '16px';
    cursor: 'pointer';
    transition: 'all 0.2s ease';
    
    // Status-based styling
    status: {
      online: {
        backgroundColor: '#f0fdf4';
        borderColor: '#22c55e';
        borderWidth: '2px';
      };
      
      inactive: {
        backgroundColor: '#f9fafb';
        borderColor: '#d1d5db';
        borderWidth: '1px';
      };
      
      alert: {
        backgroundColor: '#fef2f2';
        borderColor: '#ef4444';
        borderWidth: '3px';
        animation: 'subtle-pulse';
      };
      
      crisis: {
        backgroundColor: '#7f1d1d';
        color: 'white';
        borderColor: '#991b1b';
        borderWidth: '4px';
        animation: 'urgent-pulse';
      };
    };
    
    // Card content
    content: {
      photo: {
        size: '60px';
        borderRadius: '50%';
        marginBottom: '12px';
        defaultAvatar: 'initials_with_accessible_colors';
      };
      
      name: {
        fontSize: '16px';
        fontWeight: 'bold';
        marginBottom: '4px';
        maxLines: 2;  // Truncate long names
      };
      
      room: {
        fontSize: '14px';
        color: '#6b7280';
        marginBottom: '8px';
      };
      
      statusIndicator: {
        fontSize: '12px';
        padding: '4px 8px';
        borderRadius: '20px';
        textAlign: 'center';
        
        labels: {
          online: 'Active';
          inactive: 'Quiet';
          alert: 'Needs Attention';
          crisis: 'URGENT';
        };
      };
      
      lastActivity: {
        fontSize: '12px';
        color: '#9ca3af';
        marginTop: '8px';
      };
    };
  };
  
  // Quick actions on hover/tap
  quickActions: {
    enabled: 'desktop_and_tablet';
    actions: [
      { icon: '💬', action: 'view_conversation', tooltip: 'View recent chat' },
      { icon: '📞', action: 'call_resident', tooltip: 'Call resident room' },
      { icon: '👥', action: 'contact_family', tooltip: 'Call emergency contact' }
    ];
  };
}
```

### **🎯 PRIORITY 5: Admin Control Panel (Weeks 7-8)**

#### **Feature 5.1: User Management Interface**
```typescript
// Comprehensive user management for healthcare administrators
interface UserManagementInterface {
  layout: {
    sidebar: {
      width: '280px';
      items: [
        { text: 'All Users', count: 'dynamic', filter: 'all' },
        { text: 'Residents', count: 'dynamic', filter: 'resident' },
        { text: 'Staff', count: 'dynamic', filter: 'staff' },
        { text: 'Administrators', count: 'dynamic', filter: 'admin' },
        { text: 'Pending Approval', count: 'dynamic', filter: 'pending' }
      ];
    };
    
    mainTable: {
      columns: [
        { field: 'name', sortable: true, width: '200px' },
        { field: 'email', sortable: true, width: '250px' },
        { field: 'role', sortable: true, width: '120px' },
        { field: 'status', sortable: true, width: '100px' },
        { field: 'lastLogin', sortable: true, width: '150px' },
        { field: 'actions', sortable: false, width: '120px' }
      ];
      
      pagination: {
        rowsPerPage: [25, 50, 100];
        defaultRowsPerPage: 25;
      };
      
      bulkActions: [
        { text: 'Export Selected', action: 'export_users' },
        { text: 'Deactivate Selected', action: 'bulk_deactivate' },
        { text: 'Send Welcome Email', action: 'bulk_welcome' }
      ];
    };
  };
  
  // User creation/editing form
  userForm: {
    fields: {
      basicInfo: {
        firstName: { required: true, validation: 'name_pattern' };
        lastName: { required: true, validation: 'name_pattern' };
        email: { required: true, validation: 'email_pattern' };
        phone: { required: false, validation: 'phone_pattern' };
      };
      
      roleAssignment: {
        role: { 
          type: 'select';
          options: [
            { value: 'resident', label: 'Resident', description: 'Senior living resident' },
            { value: 'staff', label: 'Healthcare Staff', description: 'Licensed care provider' },
            { value: 'admin', label: 'Administrator', description: 'System administrator' }
          ];
          required: true;
        };
        
        permissions: {
          type: 'multi-checkbox';
          dependsOn: 'role';
          options: 'dynamic_based_on_role';
        };
      };
      
      healthcareInfo: {
        showIf: 'role === resident';
        roomNumber: { required: true };
        careLevel: { 
          type: 'select';
          options: ['independent', 'assisted', 'memory_care'];
        };
        emergencyContact: {
          name: { required: true };
          relationship: { required: true };
          phone: { required: true };
        };
      };
    };
    
    validation: {
      realTime: true;
      submitDisabled: 'if_validation_errors';
      errorDisplay: 'inline_with_field';
    };
  };
  
  // Audit trail integration
  auditTrail: {
    trackActions: [
      'user_created', 'user_modified', 'user_deleted',
      'role_changed', 'permissions_modified', 'password_reset'
    ];
    displayFormat: {
      timestamp: 'YYYY-MM-DD HH:mm:ss';
      actor: 'admin_name_and_id';
      action: 'human_readable_description';
      target: 'affected_user_name';
      details: 'expandable_json_view';
    };
  };
}
```

#### **Feature 5.2: HIPAA Compliance Dashboard**
```typescript
// HIPAA compliance monitoring and reporting
interface HIPAAComplianceDashboard {
  complianceOverview: {
    sections: [
      {
        title: 'Technical Safeguards (§164.312)';
        requirements: [
          { name: 'Access Control', status: 'compliant', lastCheck: '2025-09-05' },
          { name: 'Audit Controls', status: 'compliant', lastCheck: '2025-09-05' },
          { name: 'Integrity', status: 'compliant', lastCheck: '2025-09-05' },
          { name: 'Person or Entity Authentication', status: 'compliant', lastCheck: '2025-09-05' },
          { name: 'Transmission Security', status: 'compliant', lastCheck: '2025-09-05' }
        ];
      },
      
      {
        title: 'Administrative Safeguards (§164.308)';
        requirements: [
          { name: 'Security Officer', status: 'compliant', contact: 'admin@facility.com' },
          { name: 'Workforce Training', status: 'compliant', completionRate: '100%' },
          { name: 'Information Access Management', status: 'compliant', lastReview: '2025-09-01' },
          { name: 'Security Awareness', status: 'compliant', lastUpdate: '2025-08-15' },
          { name: 'Security Incident Procedures', status: 'compliant', lastTest: '2025-08-01' }
        ];
      }
    ];
  };
  
  // Audit log viewer
  auditLogViewer: {
    filters: {
      dateRange: { type: 'date-picker', default: 'last_30_days' };
      eventType: {
        type: 'multi-select';
        options: [
          'phi_access', 'user_authentication', 'data_export', 
          'system_configuration', 'emergency_access', 'data_deletion'
        ];
      };
      userId: { type: 'autocomplete', searchable: true };
      severity: { 
        type: 'select';
        options: ['info', 'warning', 'critical'];
      };
    };
    
    displayColumns: [
      { field: 'timestamp', width: '180px', format: 'datetime' },
      { field: 'user', width: '150px', format: 'name_with_role' },
      { field: 'action', width: '200px', format: 'human_readable' },
      { field: 'resource', width: '150px', format: 'resource_type' },
      { field: 'ip_address', width: '120px', format: 'ip' },
      { field: 'result', width: '100px', format: 'status_badge' }
    ];
    
    exportOptions: [
      { format: 'CSV', description: 'Spreadsheet format for analysis' },
      { format: 'PDF', description: 'Formatted report for regulators' },
      { format: 'JSON', description: 'Raw data for technical analysis' }
    ];
  };
  
  // Compliance reporting
  complianceReporting: {
    predefinedReports: [
      {
        name: 'Monthly HIPAA Compliance Report';
        description: 'Comprehensive monthly compliance status';
        schedule: 'first_monday_of_month';
        recipients: ['compliance_officer', 'ciso'];
      },
      {
        name: 'PHI Access Audit Report';
        description: 'All PHI access events for regulatory review';
        schedule: 'weekly';
        recipients: ['privacy_officer'];
      },
      {
        name: 'Security Incident Summary';
        description: 'Summary of all security events and responses';
        schedule: 'monthly';
        recipients: ['security_team'];
      }
    ];
    
    customReports: {
      enabled: true;
      builder: 'drag_drop_interface';
      dataPoints: 'all_audit_log_fields';
      visualization: ['table', 'chart', 'dashboard'];
      scheduling: 'cron_expression_or_gui';
    };
  };
}
```

---

## 🔌 API Integration Specifications

### **Authentication Service Integration**

#### **Auth Service Client (IMPLEMENT EXACTLY)**
```typescript
// Authentication service integration with Go microservice
class AuthServiceClient {
  private baseURL = process.env.REACT_APP_AUTH_URL || 'http://localhost:8080';
  private tokenRefreshPromise: Promise<TokenResponse> | null = null;

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const response = await fetch(`${this.baseURL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': crypto.randomUUID(),
          'X-Client-Version': process.env.REACT_APP_VERSION || '1.0.0'
        },
        body: JSON.stringify({
          email: credentials.email.toLowerCase().trim(),
          password: credentials.password,
          remember_me: credentials.rememberMe || false,
          client_info: {
            user_agent: navigator.userAgent,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
          }
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new AuthError(errorData.message || 'Login failed', response.status);
      }

      const authData: AuthResponse = await response.json();
      
      // Store tokens securely - NO PHI in browser storage
      localStorage.setItem('auth_token', authData.access_token);
      localStorage.setItem('refresh_token', authData.refresh_token);
      
      return authData;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  async refreshToken(): Promise<TokenResponse> {
    // Prevent multiple simultaneous refresh requests
    if (this.tokenRefreshPromise) {
      return this.tokenRefreshPromise;
    }

    this.tokenRefreshPromise = this._performTokenRefresh();
    
    try {
      const result = await this.tokenRefreshPromise;
      return result;
    } finally {
      this.tokenRefreshPromise = null;
    }
  }

  private async _performTokenRefresh(): Promise<TokenResponse> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new AuthError('No refresh token available', 401);
    }

    const response = await fetch(`${this.baseURL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${refreshToken}`
      }
    });

    if (!response.ok) {
      // Refresh failed - redirect to login
      this.clearTokens();
      throw new AuthError('Token refresh failed', response.status);
    }

    const tokenData: TokenResponse = await response.json();
    localStorage.setItem('auth_token', tokenData.access_token);
    
    return tokenData;
  }

  async logout(): Promise<void> {
    const token = localStorage.getItem('auth_token');
    
    if (token) {
      try {
        await fetch(`${this.baseURL}/api/v1/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
      } catch (error) {
        // Log error but don't prevent logout
        console.error('Logout error:', error);
      }
    }

    this.clearTokens();
  }

  private clearTokens(): void {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    // Clear any session-specific UI state
    sessionStorage.clear();
  }
}
```

### **Chat Service Integration**

#### **Chat Service Client with Crisis Detection**
```typescript
// Chat service integration with Python AI Gateway
class ChatServiceClient {
  private baseURL = process.env.REACT_APP_AI_URL || 'http://localhost:8000';
  private websocket: WebSocket | null = null;
  private messageQueue: ChatMessage[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const authToken = localStorage.getItem('auth_token');
    if (!authToken) {
      throw new Error('Authentication required');
    }

    try {
      const response = await fetch(`${this.baseURL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
          'X-Session-ID': this.getOrCreateSessionId(),
          'X-User-Agent': navigator.userAgent
        },
        body: JSON.stringify({
          message: request.message,
          context: {
            user_id: request.userId,
            session_id: request.sessionId,
            timestamp: new Date().toISOString(),
            message_type: request.messageType || 'text',
            // Include accessibility preferences for response formatting
            accessibility_prefs: {
              font_size: request.accessibilityPrefs?.fontSize || 'normal',
              high_contrast: request.accessibilityPrefs?.highContrast || false
            }
          },
          // Crisis detection configuration
          safety_config: {
            crisis_detection_enabled: true,
            phi_detection_enabled: true,
            content_filtering_enabled: true
          }
        })
      });

      // Handle token expiration
      if (response.status === 401) {
        await this.authService.refreshToken();
        return this.sendMessage(request); // Retry with new token
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new ChatError(errorData.message || 'Chat request failed', response.status);
      }

      const chatResponse: ChatResponse = await response.json();

      // Handle crisis detection
      if (chatResponse.safety_alert) {
        this.handleCrisisAlert(chatResponse.safety_alert);
      }

      // Handle PHI detection warning
      if (chatResponse.phi_detected) {
        this.handlePHIDetection(chatResponse.phi_warning);
      }

      return chatResponse;
    } catch (error) {
      console.error('Chat error:', error);
      throw error;
    }
  }

  // Real-time WebSocket connection for alerts
  connectRealTime(sessionId: string): void {
    const wsURL = `${this.baseURL.replace('http', 'ws')}/ws/${sessionId}`;
    const authToken = localStorage.getItem('auth_token');

    this.websocket = new WebSocket(wsURL, ['authorization', authToken]);

    this.websocket.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      // Send queued messages
      this.processMessageQueue();
    };

    this.websocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleRealTimeMessage(message);
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    };

    this.websocket.onclose = () => {
      console.log('WebSocket disconnected');
      this.attemptReconnect(sessionId);
    };

    this.websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private handleCrisisAlert(alert: CrisisAlert): void {
    // Dispatch crisis alert to UI
    window.dispatchEvent(new CustomEvent('crisis-alert', { 
      detail: alert 
    }));
  }

  private handlePHIDetection(warning: PHIWarning): void {
    // Dispatch PHI warning to UI
    window.dispatchEvent(new CustomEvent('phi-warning', { 
      detail: warning 
    }));
  }
}
```

### **Health Monitoring Integration**

#### **System Health Client**
```typescript
// System health monitoring for operations dashboard
class HealthMonitoringClient {
  private baseURL = process.env.REACT_APP_HEALTH_URL || 'http://localhost:8090';

  async getSystemHealth(): Promise<SystemHealth> {
    const response = await fetch(`${this.baseURL}/health/detailed`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error('Health check failed');
    }

    return response.json();
  }

  async getServiceMetrics(): Promise<ServiceMetrics> {
    const response = await fetch(`${this.baseURL}/metrics/services`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      }
    });

    if (!response.ok) {
      throw new Error('Metrics fetch failed');
    }

    return response.json();
  }
}
```

---

## 🔒 Security & Compliance Requirements

### **HIPAA Compliance Implementation (CRITICAL)**

#### **Data Handling Rules (MANDATORY)**
```typescript
// CRITICAL: PHI handling rules - ZERO tolerance for violations
const PHI_HANDLING_RULES = {
  storage: {
    localStorage: 'PROHIBITED',     // Never store PHI in localStorage
    sessionStorage: 'PROHIBITED',   // Never store PHI in sessionStorage
    cookies: 'PROHIBITED',          // Never store PHI in cookies
    indexedDB: 'PROHIBITED',        // Never store PHI in IndexedDB
    memory: 'IMMEDIATE_CLEANUP',    // Clear PHI from memory after use
  },
  
  transmission: {
    https: 'REQUIRED',              // All API calls must use HTTPS
    encryption: 'TLS_1_3_MINIMUM',  // Modern encryption required
    headers: {
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block',
      'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
    }
  },
  
  display: {
    masking: 'AUTOMATIC',           // Auto-mask sensitive data in UI
    screenshots: 'PREVENTED',       // Prevent screenshots of PHI
    printing: 'RESTRICTED',         // Restrict printing of PHI screens
    sharing: 'PROHIBITED'           // No social sharing from PHI screens
  },
  
  logging: {
    console: 'PROHIBITED',          // Never log PHI to console
    errorTracking: 'SANITIZED',     // Sanitize errors before sending
    analytics: 'NO_PHI',           // Analytics must not contain PHI
    debugging: 'PRODUCTION_DISABLED' // No debugging tools in production
  }
};
```

#### **Session Security Implementation**
```typescript
// Secure session management for healthcare compliance
class SecureSessionManager {
  private sessionTimeoutId: number | null = null;
  private readonly MAX_SESSION_TIME = 8 * 60 * 60 * 1000; // 8 hours (healthcare shift)
  private readonly IDLE_WARNING_TIME = 14 * 60 * 1000;    // 14 minutes idle warning
  private readonly IDLE_LOGOUT_TIME = 15 * 60 * 1000;     // 15 minutes idle logout

  startSession(user: UserProfile): void {
    this.scheduleSessionTimeout();
    this.startIdleDetection();
    this.logSessionStart(user);
  }

  private scheduleSessionTimeout(): void {
    // Automatic logout after maximum session time
    this.sessionTimeoutId = window.setTimeout(() => {
      this.forceLogout('session_expired');
    }, this.MAX_SESSION_TIME);
  }

  private startIdleDetection(): void {
    let lastActivity = Date.now();
    let idleWarningShown = false;

    // Track user activity
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    
    const resetIdleTimer = () => {
      lastActivity = Date.now();
      idleWarningShown = false;
    };

    activityEvents.forEach(event => {
      document.addEventListener(event, resetIdleTimer, true);
    });

    // Check for idle state every minute
    setInterval(() => {
      const idleTime = Date.now() - lastActivity;

      if (idleTime >= this.IDLE_LOGOUT_TIME) {
        this.forceLogout('idle_timeout');
      } else if (idleTime >= this.IDLE_WARNING_TIME && !idleWarningShown) {
        this.showIdleWarning();
        idleWarningShown = true;
      }
    }, 60000); // Check every minute
  }

  private showIdleWarning(): void {
    // Show modal warning about impending logout
    const remainingTime = this.IDLE_LOGOUT_TIME - this.IDLE_WARNING_TIME;
    const minutes = Math.floor(remainingTime / 60000);

    // This should trigger a UI modal
    window.dispatchEvent(new CustomEvent('idle-warning', {
      detail: { remainingMinutes: minutes }
    }));
  }

  private forceLogout(reason: string): void {
    // Log the logout reason for audit purposes
    this.logSessionEnd(reason);
    
    // Clear all session data
    this.clearAllSessionData();
    
    // Redirect to login
    window.location.href = '/login?reason=' + reason;
  }

  private clearAllSessionData(): void {
    // Clear authentication tokens
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    
    // Clear all session storage (UI preferences only)
    sessionStorage.clear();
    
    // Clear any cached data that might contain PHI
    if ('caches' in window) {
      caches.keys().then(names => {
        names.forEach(name => caches.delete(name));
      });
    }
  }
}
```

### **XSS Prevention (MANDATORY)**
```typescript
// XSS prevention measures - IMPLEMENT EXACTLY
const XSS_PREVENTION = {
  inputSanitization: {
    library: 'DOMPurify',
    config: {
      ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'p', 'br'],  // Very limited HTML
      ALLOWED_ATTR: [],                                     // No attributes
      KEEP_CONTENT: false,                                  // Strip unknown tags
      SANITIZE_DOM: true                                    // Full DOM sanitization
    }
  },
  
  outputEscaping: {
    framework: 'React',              // React automatic escaping
    dangerouslySetInnerHTML: 'NEVER', // Never use this prop
    userContent: 'ALWAYS_ESCAPE'      // Always escape user content
  },
  
  contentSecurityPolicy: {
    'script-src': ["'self'"],                    // No inline scripts
    'object-src': ["'none'"],                   // No objects/embeds
    'base-uri': ["'self'"],                     // Prevent base tag injection
    'frame-ancestors': ["'none'"]               // Prevent clickjacking
  }
};

// Sanitization utility function
import DOMPurify from 'dompurify';

export function sanitizeUserInput(input: string): string {
  return DOMPurify.sanitize(input, XSS_PREVENTION.inputSanitization.config);
}

// React component for displaying user content safely
interface SafeUserContentProps {
  content: string;
  className?: string;
}

export function SafeUserContent({ content, className }: SafeUserContentProps) {
  const sanitizedContent = sanitizeUserInput(content);
  
  // Even with sanitization, use textContent instead of innerHTML when possible
  return (
    <div className={className}>
      {sanitizedContent}
    </div>
  );
}
```

---

## ♿ Accessibility & Senior-Friendly Design

### **WCAG 2.1 AA Compliance (MANDATORY)**

#### **Font and Text Requirements**
```typescript
// Typography system optimized for elderly users
const SENIOR_TYPOGRAPHY = {
  fontSizes: {
    minimum: 18,        // Absolute minimum (WCAG AA requirement)
    default: 22,        // Preferred default for seniors
    large: 28,          // Large text option
    extraLarge: 34,     // Maximum size option
    headlines: 40       // Section headings
  },
  
  lineHeight: {
    minimum: 1.5,       // WCAG AA requirement
    preferred: 1.6,     // Better for seniors
    longText: 1.8       // For extended reading
  },
  
  fontFamily: {
    primary: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
    // Inter font chosen for:
    // - High legibility for seniors
    // - Excellent character distinction (6 vs G, 1 vs l vs I)
    // - Good hinting for small sizes
  },
  
  fontWeight: {
    normal: 400,        // Regular text
    medium: 500,        // Slightly bold for emphasis
    bold: 600           // Strong emphasis (not too heavy)
  },
  
  letterSpacing: {
    tight: '-0.025em',  // Headlines only
    normal: '0',        // Body text
    wide: '0.025em'     // For improved readability when needed
  }
};
```

#### **Color and Contrast System**
```typescript
// WCAG-compliant color system with senior-friendly enhancements
const ACCESSIBILITY_COLORS = {
  // High contrast ratios for text
  textColors: {
    primary: '#1f2937',        // 16.34:1 ratio on white background
    secondary: '#374151',      // 12.63:1 ratio on white background
    muted: '#6b7280',         // 5.74:1 ratio on white background (minimum for large text)
    error: '#dc2626',         // Crisis/error text
    success: '#059669',       // Success/confirmation text
    warning: '#d97706'        // Warning text
  },
  
  // Background colors with sufficient contrast
  backgrounds: {
    primary: '#ffffff',       // Pure white
    secondary: '#f9fafb',     // Very light gray
    tertiary: '#f3f4f6',     // Light gray for sections
    
    // Status backgrounds with high contrast text
    errorBg: '#fef2f2',       // Light red background
    successBg: '#f0fdf4',     // Light green background
    warningBg: '#fffbeb',     // Light yellow background
    infoBg: '#eff6ff'         // Light blue background
  },
  
  // High contrast mode (user selectable)
  highContrast: {
    text: '#000000',          // Pure black text
    background: '#ffffff',    // Pure white background
    border: '#000000',        // Black borders
    focus: '#0000ff',         // Blue focus indicators
    error: '#ff0000',         // Pure red for errors
    success: '#008000'        // Pure green for success
  },
  
  // Interactive element colors
  interactive: {
    primary: '#2563eb',       // Primary button color
    primaryHover: '#1d4ed8',  // Darker on hover
    secondary: '#6b7280',     // Secondary button color
    disabled: '#d1d5db',      // Disabled state
    
    // Focus indicators - VERY important for keyboard navigation
    focus: {
      color: '#2563eb',
      width: '3px',           // Thick enough to see
      style: 'solid',
      offset: '2px'
    }
  }
};
```

#### **Touch Target Requirements**
```typescript
// Touch target sizing for senior-friendly interaction
const TOUCH_TARGETS = {
  // Minimum sizes (WCAG requirement)
  minimum: {
    width: 44,    // 44px minimum
    height: 44    // 44px minimum
  },
  
  // Preferred sizes for seniors
  preferred: {
    width: 56,    // Larger for easier tapping
    height: 56    // Larger for easier tapping
  },
  
  // Spacing between interactive elements
  spacing: {
    minimum: 8,   // Minimum gap between touch targets
    preferred: 16 // Preferred gap to prevent accidental taps
  },
  
  // Implementation helper
  getTouchTargetStyle: (size: 'minimum' | 'preferred' = 'preferred') => ({
    minWidth: TOUCH_TARGETS[size].width,
    minHeight: TOUCH_TARGETS[size].height,
    padding: '12px 16px',  // Internal padding for comfortable touch
    margin: '8px',         // External margin to prevent accidental taps
    cursor: 'pointer',
    outline: 'none',       // Custom focus handling
    border: '2px solid transparent' // Space for focus indicator
  })
};
```

#### **Voice Input Implementation**
```typescript
// Voice input system for seniors with limited typing ability
class VoiceInputSystem {
  private recognition: SpeechRecognition | null = null;
  private isListening = false;
  private onTranscript: (text: string) => void = () => {};
  private onError: (error: string) => void = () => {};

  constructor() {
    // Check for browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.warn('Speech recognition not supported in this browser');
      return;
    }

    this.recognition = new SpeechRecognition();
    this.setupRecognition();
  }

  private setupRecognition(): void {
    if (!this.recognition) return;

    // Configuration optimized for seniors
    this.recognition.continuous = false;        // Single phrase recognition
    this.recognition.interimResults = true;     // Show partial results
    this.recognition.lang = 'en-US';           // Default to US English
    this.recognition.maxAlternatives = 1;       // Single best result

    this.recognition.onstart = () => {
      this.isListening = true;
      this.dispatchEvent('voice-start');
    };

    this.recognition.onend = () => {
      this.isListening = false;
      this.dispatchEvent('voice-end');
    };

    this.recognition.onresult = (event) => {
      const result = event.results[event.results.length - 1];
      const transcript = result[0].transcript;
      const confidence = result[0].confidence;

      // Only accept results with reasonable confidence
      if (confidence > 0.7) {
        this.onTranscript(transcript);
      } else {
        this.onError('Please try speaking more clearly');
      }
    };

    this.recognition.onerror = (event) => {
      const error = this.getErrorMessage(event.error);
      this.onError(error);
      this.isListening = false;
    };
  }

  startListening(callbacks: { onTranscript: (text: string) => void; onError: (error: string) => void }): void {
    if (!this.recognition) {
      callbacks.onError('Voice input not supported in your browser');
      return;
    }

    if (this.isListening) {
      this.stopListening();
      return;
    }

    this.onTranscript = callbacks.onTranscript;
    this.onError = callbacks.onError;

    try {
      this.recognition.start();
    } catch (error) {
      callbacks.onError('Could not start voice input');
    }
  }

  stopListening(): void {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
    }
  }

  private getErrorMessage(error: string): string {
    switch (error) {
      case 'no-speech':
        return 'No speech detected. Please try again.';
      case 'audio-capture':
        return 'Microphone access denied. Please check permissions.';
      case 'not-allowed':
        return 'Please allow microphone access to use voice input.';
      case 'network':
        return 'Network error. Please check your connection.';
      default:
        return 'Voice input error. Please try typing instead.';
    }
  }

  private dispatchEvent(type: string): void {
    window.dispatchEvent(new CustomEvent(type));
  }
}
```

#### **Keyboard Navigation Implementation**
```typescript
// Comprehensive keyboard navigation for accessibility
class KeyboardNavigationManager {
  private focusableElements: HTMLElement[] = [];
  private currentFocusIndex = -1;

  initialize(): void {
    this.updateFocusableElements();
    this.setupKeyboardListeners();
    this.setupFocusIndicators();
  }

  private setupKeyboardListeners(): void {
    document.addEventListener('keydown', (event) => {
      switch (event.key) {
        case 'Tab':
          this.handleTabNavigation(event);
          break;
        case 'Enter':
        case ' ':
          this.handleActivation(event);
          break;
        case 'Escape':
          this.handleEscape(event);
          break;
        case 'ArrowUp':
        case 'ArrowDown':
          this.handleArrowNavigation(event);
          break;
      }
    });

    // Update focusable elements when DOM changes
    const observer = new MutationObserver(() => {
      this.updateFocusableElements();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['tabindex', 'disabled', 'hidden']
    });
  }

  private updateFocusableElements(): void {
    const focusableSelectors = [
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      'a[href]',
      '[tabindex]:not([tabindex="-1"])'
    ].join(',');

    this.focusableElements = Array.from(
      document.querySelectorAll(focusableSelectors)
    ).filter(el => this.isVisible(el)) as HTMLElement[];
  }

  private isVisible(element: Element): boolean {
    const style = window.getComputedStyle(element);
    return style.display !== 'none' && 
           style.visibility !== 'hidden' && 
           style.opacity !== '0';
  }

  private setupFocusIndicators(): void {
    // Add custom focus styles for better visibility
    const style = document.createElement('style');
    style.textContent = `
      /* High-visibility focus indicators for seniors */
      *:focus {
        outline: 3px solid #2563eb !important;
        outline-offset: 2px !important;
        box-shadow: 0 0 0 5px rgba(37, 99, 235, 0.3) !important;
      }
      
      /* Special focus for interactive elements */
      button:focus,
      input:focus,
      select:focus,
      textarea:focus {
        outline: 3px solid #2563eb !important;
        outline-offset: 2px !important;
        box-shadow: 0 0 0 5px rgba(37, 99, 235, 0.3) !important;
      }
      
      /* Crisis intervention elements get red focus */
      [data-crisis="true"]:focus {
        outline-color: #dc2626 !important;
        box-shadow: 0 0 0 5px rgba(220, 38, 38, 0.3) !important;
      }
    `;
    document.head.appendChild(style);
  }
}
```

---

## ⚡ Performance & Technical Requirements

### **Core Web Vitals Targets (MANDATORY)**
```typescript
// Performance targets - ALL must be met for healthcare compliance
const PERFORMANCE_TARGETS = {
  // Core Web Vitals (Google standards)
  firstContentfulPaint: 1500,      // 1.5 seconds max
  largestContentfulPaint: 2500,    // 2.5 seconds max  
  firstInputDelay: 100,            // 100ms max for senior-friendly interaction
  cumulativeLayoutShift: 0.1,      // Minimal layout shift for stability
  timeToInteractive: 3000,         // 3 seconds max for full interactivity

  // Healthcare-specific performance targets
  crisisAlertDisplayTime: 100,     // Crisis alerts must appear within 100ms
  chatResponseLatency: 500,        // Chat responses within 500ms
  voiceInputProcessing: 200,       // Voice-to-text processing within 200ms
  emergencyButtonResponse: 50,     // Emergency button response within 50ms

  // Bundle size limits (for fast loading on slower connections)
  initialBundle: 500 * 1024,       // 500KB initial bundle
  totalAssets: 3 * 1024 * 1024,    // 3MB total assets including images
  chunkSizes: {
    vendor: 1 * 1024 * 1024,       // 1MB for vendor libraries
    main: 300 * 1024,              // 300KB for main app code
    chat: 200 * 1024,              // 200KB for chat features
    admin: 300 * 1024              // 300KB for admin features (lazy loaded)
  }
};
```

#### **Performance Monitoring Implementation**
```typescript
// Performance monitoring for healthcare compliance
class PerformanceMonitor {
  private metrics: PerformanceMetrics = {};
  private observer: PerformanceObserver | null = null;

  initialize(): void {
    this.setupPerformanceObserver();
    this.monitorCoreWebVitals();
    this.monitorHealthcareSpecificMetrics();
  }

  private setupPerformanceObserver(): void {
    if ('PerformanceObserver' in window) {
      this.observer = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          this.processPerformanceEntry(entry);
        });
      });

      this.observer.observe({ entryTypes: ['navigation', 'paint', 'largest-contentful-paint'] });
    }
  }

  private monitorCoreWebVitals(): void {
    // First Contentful Paint
    new PerformanceObserver((entryList) => {
      const entries = entryList.getEntries();
      const fcp = entries[entries.length - 1];
      this.recordMetric('FCP', fcp.startTime);
    }).observe({ entryTypes: ['paint'] });

    // Largest Contentful Paint  
    new PerformanceObserver((entryList) => {
      const entries = entryList.getEntries();
      const lcp = entries[entries.length - 1];
      this.recordMetric('LCP', lcp.startTime);
    }).observe({ entryTypes: ['largest-contentful-paint'] });

    // First Input Delay
    new PerformanceObserver((entryList) => {
      entryList.getEntries().forEach((entry) => {
        this.recordMetric('FID', entry.processingStart - entry.startTime);
      });
    }).observe({ entryTypes: ['first-input'] });

    // Cumulative Layout Shift
    let clsScore = 0;
    new PerformanceObserver((entryList) => {
      entryList.getEntries().forEach((entry) => {
        if (!(entry as any).hadRecentInput) {
          clsScore += (entry as any).value;
        }
      });
      this.recordMetric('CLS', clsScore);
    }).observe({ entryTypes: ['layout-shift'] });
  }

  private monitorHealthcareSpecificMetrics(): void {
    // Crisis alert response time
    window.addEventListener('crisis-alert-triggered', (event) => {
      const startTime = performance.now();
      
      // Wait for crisis modal to appear
      const observer = new MutationObserver(() => {
        const crisisModal = document.querySelector('[data-crisis-modal="true"]');
        if (crisisModal) {
          const endTime = performance.now();
          this.recordMetric('CrisisAlertTime', endTime - startTime);
          observer.disconnect();
        }
      });

      observer.observe(document.body, { childList: true, subtree: true });
    });

    // Chat response latency
    window.addEventListener('chat-message-sent', (event) => {
      const startTime = performance.now();
      
      window.addEventListener('chat-response-received', () => {
        const endTime = performance.now();
        this.recordMetric('ChatResponseTime', endTime - startTime);
      }, { once: true });
    });
  }

  private recordMetric(name: string, value: number): void {
    this.metrics[name] = value;
    
    // Check against targets and log warnings
    const target = this.getTargetForMetric(name);
    if (target && value > target) {
      console.warn(`Performance target exceeded: ${name} = ${value}ms (target: ${target}ms)`);
    }

    // Send metrics to monitoring service (in production)
    if (process.env.NODE_ENV === 'production') {
      this.sendMetricsToMonitoring(name, value);
    }
  }

  private getTargetForMetric(name: string): number | null {
    const targets: Record<string, number> = {
      'FCP': PERFORMANCE_TARGETS.firstContentfulPaint,
      'LCP': PERFORMANCE_TARGETS.largestContentfulPaint,
      'FID': PERFORMANCE_TARGETS.firstInputDelay,
      'CLS': PERFORMANCE_TARGETS.cumulativeLayoutShift * 1000, // Convert to ms
      'CrisisAlertTime': PERFORMANCE_TARGETS.crisisAlertDisplayTime,
      'ChatResponseTime': PERFORMANCE_TARGETS.chatResponseLatency
    };

    return targets[name] || null;
  }
}
```

### **Offline Support & Service Worker**
```typescript
// Service worker for offline functionality - healthcare continuity
const CACHE_NAME = 'therapeutic-ai-v1';
const CRITICAL_RESOURCES = [
  '/',
  '/static/js/main.js',
  '/static/css/main.css',
  '/emergency-contacts',
  '/crisis-resources'
];

// Install event - cache critical resources
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(CRITICAL_RESOURCES);
    })
  );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', (event) => {
  // Handle API requests
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache successful responses (excluding PHI)
          if (response.ok && !event.request.url.includes('/chat/')) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // Return cached version or offline message
          return caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            
            // Return offline message for API requests
            return new Response(
              JSON.stringify({ 
                error: 'Offline', 
                message: 'You are currently offline. Emergency services are still available.' 
              }),
              { 
                status: 503,
                statusText: 'Service Unavailable',
                headers: { 'Content-Type': 'application/json' }
              }
            );
          });
        })
    );
    return;
  }

  // Handle regular resource requests
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request);
    })
  );
});
```

---

## 🧪 Testing & Quality Assurance

### **Healthcare-Specific Testing Framework**
```typescript
// Testing requirements for healthcare compliance
interface HealthcareTestSuite {
  // Accessibility testing - MANDATORY
  accessibility: {
    framework: 'jest + @testing-library/jest-dom + axe-core';
    coverage: '100%_of_interactive_elements';
    requirements: [
      'WCAG_2.1_AA_compliance',
      'keyboard_navigation',
      'screen_reader_compatibility',
      'color_contrast_validation',
      'focus_management'
    ];
  };

  // Crisis detection testing - CRITICAL
  crisisDetection: {
    testCases: [
      'suicidal_ideation_keywords',
      'self_harm_expressions', 
      'severe_depression_indicators',
      'medical_emergency_phrases'
    ];
    requirements: [
      'zero_false_negatives',      // Must catch all crisis situations
      'acceptable_false_positives', // <10% false positive rate
      'response_time_under_100ms',  // Must respond immediately
      'proper_escalation_ui'        // Correct emergency UI
    ];
  };

  // Security testing - MANDATORY
  security: {
    framework: 'jest + security-specific_test_utils';
    testCases: [
      'xss_prevention',
      'csrf_protection', 
      'phi_data_leakage',
      'session_security',
      'input_sanitization'
    ];
    requirements: [
      'no_phi_in_storage',         // Absolute requirement
      'no_phi_in_console',         // No PHI logging
      'secure_transmission',       // HTTPS only
      'proper_error_handling'      // No sensitive data in errors
    ];
  };

  // Performance testing - REQUIRED
  performance: {
    framework: 'lighthouse + web-vitals + custom_metrics';
    testCases: [
      'core_web_vitals',
      'bundle_size_limits',
      'crisis_alert_speed',
      'chat_response_latency'
    ];
    targets: PERFORMANCE_TARGETS; // Defined above
  };
}
```

#### **Accessibility Testing Implementation**
```typescript
// Accessibility testing utilities
import { axe, toHaveNoViolations } from 'jest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

expect.extend(toHaveNoViolations);

describe('Accessibility Tests', () => {
  describe('Login Form Accessibility', () => {
    test('should have no accessibility violations', async () => {
      const { container } = render(<LoginForm />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    test('should be keyboard navigable', async () => {
      render(<LoginForm />);
      const user = userEvent.setup();
      
      // Tab through all interactive elements
      await user.tab();
      expect(screen.getByLabelText(/email/i)).toHaveFocus();
      
      await user.tab();
      expect(screen.getByLabelText(/password/i)).toHaveFocus();
      
      await user.tab();
      expect(screen.getByRole('button', { name: /sign in/i })).toHaveFocus();
    });

    test('should have proper ARIA labels', () => {
      render(<LoginForm />);
      
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    test('should meet color contrast requirements', async () => {
      const { container } = render(<LoginForm />);
      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true }
        }
      });
      expect(results).toHaveNoViolations();
    });
  });

  describe('Crisis Detection UI Accessibility', () => {
    test('crisis modal should be immediately accessible', async () => {
      render(<CrisisInterventionModal isOpen={true} />);
      
      // Modal should be focused immediately
      const modal = screen.getByRole('dialog', { name: /crisis intervention/i });
      expect(modal).toHaveFocus();
      
      // Should have proper ARIA attributes
      expect(modal).toHaveAttribute('aria-modal', 'true');
      expect(modal).toHaveAttribute('role', 'dialog');
    });

    test('emergency buttons should have large touch targets', () => {
      render(<CrisisInterventionModal isOpen={true} />);
      
      const emergencyButtons = screen.getAllByRole('button');
      emergencyButtons.forEach(button => {
        const styles = window.getComputedStyle(button);
        const minHeight = parseInt(styles.minHeight);
        const minWidth = parseInt(styles.minWidth);
        
        expect(minHeight).toBeGreaterThanOrEqual(56); // Senior-friendly size
        expect(minWidth).toBeGreaterThanOrEqual(56);
      });
    });
  });
});
```

#### **Crisis Detection Testing**
```typescript
// Crisis detection testing suite
describe('Crisis Detection System', () => {
  const crisisKeywords = [
    'I want to die',
    'I want to kill myself',
    'I can\'t go on',
    'There\'s no point in living',
    'I want to hurt myself',
    'I wish I was dead'
  ];

  const falseCrisisStrings = [
    'I want to die my hair',
    'I could just die of embarrassment', 
    'That movie was to die for',
    'I\'m dying to see you'
  ];

  describe('Crisis Keyword Detection', () => {
    test.each(crisisKeywords)('should detect crisis in: "%s"', async (message) => {
      const mockOnCrisis = jest.fn();
      render(<ChatInterface onCrisisDetected={mockOnCrisis} />);
      
      const input = screen.getByPlaceholderText(/type your message/i);
      await userEvent.type(input, message);
      
      const sendButton = screen.getByLabelText(/send message/i);
      await userEvent.click(sendButton);
      
      // Crisis should be detected
      expect(mockOnCrisis).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: expect.any(String),
          message,
          timestamp: expect.any(Date)
        })
      );
    });

    test.each(falseCrisisStrings)('should NOT detect crisis in: "%s"', async (message) => {
      const mockOnCrisis = jest.fn();
      render(<ChatInterface onCrisisDetected={mockOnCrisis} />);
      
      const input = screen.getByPlaceholderText(/type your message/i);
      await userEvent.type(input, message);
      
      const sendButton = screen.getByLabelText(/send message/i);
      await userEvent.click(sendButton);
      
      // Should NOT trigger crisis detection
      expect(mockOnCrisis).not.toHaveBeenCalled();
    });
  });

  describe('Crisis UI Response Time', () => {
    test('should display crisis modal within 100ms', async () => {
      const startTime = performance.now();
      
      render(<ChatInterface />);
      
      // Trigger crisis detection
      fireEvent(window, new CustomEvent('crisis-alert', {
        detail: { severity: 'high', message: 'I want to die' }
      }));
      
      // Wait for modal to appear
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
      
      const endTime = performance.now();
      const responseTime = endTime - startTime;
      
      expect(responseTime).toBeLessThan(100); // Must be under 100ms
    });
  });
});
```

#### **Security Testing Implementation**
```typescript
// Security testing for PHI protection
describe('Security Tests', () => {
  describe('PHI Data Protection', () => {
    test('should never store PHI in localStorage', async () => {
      render(<ChatInterface />);
      
      // Simulate chat with PHI-like content
      const phiMessage = 'My Social Security number is 123-45-6789';
      
      const input = screen.getByPlaceholderText(/type your message/i);
      await userEvent.type(input, phiMessage);
      
      // Check that PHI is not stored in localStorage
      const localStorageData = JSON.stringify(localStorage);
      expect(localStorageData).not.toContain('123-45-6789');
      expect(localStorageData).not.toContain('Social Security');
    });

    test('should sanitize user input to prevent XSS', async () => {
      render(<ChatInterface />);
      
      const maliciousInput = '<script>alert("XSS")</script>';
      
      const input = screen.getByPlaceholderText(/type your message/i);
      await userEvent.type(input, maliciousInput);
      
      const sendButton = screen.getByLabelText(/send message/i);
      await userEvent.click(sendButton);
      
      // Script should be sanitized
      expect(document.body.innerHTML).not.toContain('<script>');
      expect(screen.queryByText(maliciousInput)).not.toBeInTheDocument();
    });

    test('should not log PHI to console', () => {
      const consoleSpy = jest.spyOn(console, 'log');
      const consoleErrorSpy = jest.spyOn(console, 'error');
      
      render(<ChatInterface />);
      
      // Simulate PHI data handling
      const phiData = { ssn: '123-45-6789', medicalRecord: 'ABC123' };
      
      // Trigger some component that might handle PHI
      fireEvent(window, new CustomEvent('process-phi-data', { detail: phiData }));
      
      // Check that PHI is not logged
      expect(consoleSpy).not.toHaveBeenCalledWith(
        expect.stringContaining('123-45-6789')
      );
      expect(consoleErrorSpy).not.toHaveBeenCalledWith(
        expect.stringContaining('ABC123')
      );
      
      consoleSpy.mockRestore();
      consoleErrorSpy.mockRestore();
    });
  });

  describe('Session Security', () => {
    test('should auto-logout after idle timeout', async () => {
      const mockLogout = jest.fn();
      render(<App onLogout={mockLogout} />);
      
      // Mock idle timeout (15 minutes)
      jest.advanceTimersByTime(15 * 60 * 1000);
      
      await waitFor(() => {
        expect(mockLogout).toHaveBeenCalledWith('idle_timeout');
      });
    });

    test('should clear all session data on logout', async () => {
      render(<App />);
      
      // Set up some session data
      localStorage.setItem('auth_token', 'fake-token');
      sessionStorage.setItem('ui_preferences', JSON.stringify({ fontSize: 'large' }));
      
      // Trigger logout
      const logoutButton = screen.getByRole('button', { name: /logout/i });
      await userEvent.click(logoutButton);
      
      // Verify session data is cleared
      expect(localStorage.getItem('auth_token')).toBeNull();
      expect(sessionStorage.length).toBe(0);
    });
  });
});
```

---

## 📋 Development Guidelines & Standards

### **Code Quality Requirements (MANDATORY)**
```typescript
// TypeScript configuration - IMPLEMENT EXACTLY
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "Bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    
    // Strict type checking - REQUIRED for healthcare data safety
    "strict": true,
    "noImplicitAny": true,
    "noImplicitReturns": true,
    "noImplicitThis": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "exactOptionalPropertyTypes": true,
    "noFallthroughCasesInSwitch": true,
    
    // Additional safety checks
    "allowUnusedLabels": false,
    "allowUnreachableCode": false,
    "noImplicitOverride": true
  }
}
```

#### **ESLint Configuration for Healthcare Safety**
```json
// .eslintrc.json - IMPLEMENT EXACTLY
{
  "extends": [
    "@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended",
    "plugin:security/recommended"
  ],
  "plugins": [
    "@typescript-eslint",
    "react",
    "react-hooks",
    "jsx-a11y",
    "security"
  ],
  "rules": {
    // Healthcare-specific security rules
    "no-console": "error",                           // No PHI in console logs
    "no-debugger": "error",                         // No debugging in production
    "security/detect-object-injection": "error",    // Prevent injection attacks
    "security/detect-non-literal-regexp": "error",  // Prevent ReDoS attacks
    
    // Accessibility rules - MANDATORY
    "jsx-a11y/alt-text": "error",                  // Alt text required
    "jsx-a11y/label-has-associated-control": "error",
    "jsx-a11y/no-autofocus": "error",               // Problematic for seniors
    "jsx-a11y/click-events-have-key-events": "error",
    
    // React rules for safety
    "react/no-danger": "error",                     // No dangerouslySetInnerHTML
    "react/no-danger-with-children": "error",
    "react/jsx-no-script-url": "error",
    "react/jsx-no-target-blank": "error",
    
    // TypeScript rules for healthcare data safety
    "@typescript-eslint/no-explicit-any": "error",  // No any types
    "@typescript-eslint/no-non-null-assertion": "error",
    "@typescript-eslint/no-unused-vars": "error",
    
    // Additional safety rules
    "prefer-const": "error",
    "no-var": "error",
    "eqeqeq": ["error", "always"]                   // Strict equality
  }
}
```

### **Component Architecture Standards**

#### **Component Structure Template**
```typescript
// Standard component template for healthcare UI
interface ComponentProps {
  // Props interface with complete type safety
  children?: React.ReactNode;
  className?: string;
  testId?: string;  // For testing
  ariaLabel?: string; // For accessibility
}

interface ComponentState {
  // State interface if using local state
}

// Component implementation with healthcare safety patterns
export function HealthcareComponent({ 
  children, 
  className, 
  testId, 
  ariaLabel,
  ...props 
}: ComponentProps): JSX.Element {
  // Hooks at the top
  const [localState, setLocalState] = useState<ComponentState | null>(null);
  const { user, permissions } = useAuth();
  const { fontSize, highContrast } = useAccessibility();
  
  // Security: Verify user has required permissions
  if (!hasPermission(permissions, 'required_permission')) {
    return <UnauthorizedAccess />;
  }

  // Event handlers with security considerations
  const handleUserAction = useCallback((event: React.MouseEvent) => {
    // Prevent default if needed
    event.preventDefault();
    
    // Sanitize any user input
    const sanitizedData = sanitizeInput(event.currentTarget.value);
    
    // Log action for audit trail (no PHI)
    logUserAction({
      action: 'component_interaction',
      userId: user.id,
      timestamp: new Date().toISOString()
    });
    
    // Handle the action
    setLocalState(sanitizedData);
  }, [user.id]);

  // Accessibility helpers
  const accessibilityProps = {
    'aria-label': ariaLabel,
    'data-testid': testId,
    className: clsx(
      'healthcare-component',
      {
        'font-large': fontSize === 'large',
        'high-contrast': highContrast
      },
      className
    )
  };

  return (
    <div {...accessibilityProps}>
      {/* Component content with proper ARIA structure */}
      <header role="banner" aria-level={1}>
        Component Header
      </header>
      
      <main role="main">
        {children}
      </main>
      
      {/* Action buttons with large touch targets */}
      <footer role="contentinfo">
        <button
          onClick={handleUserAction}
          className="touch-target-large"
          aria-describedby="action-description"
        >
          Action Button
        </button>
      </footer>
    </div>
  );
}

// PropTypes for runtime validation (additional safety)
HealthcareComponent.propTypes = {
  children: PropTypes.node,
  className: PropTypes.string,
  testId: PropTypes.string,
  ariaLabel: PropTypes.string
};

// Default props
HealthcareComponent.defaultProps = {
  className: '',
  ariaLabel: 'Healthcare component'
};
```

#### **Error Boundary for Healthcare Safety**
```typescript
// Error boundary specifically for healthcare applications
interface ErrorBoundaryState {
  hasError: boolean;
  errorId: string | null;
  errorMessage: string | null;
}

export class HealthcareErrorBoundary extends Component<
  PropsWithChildren<{}>,
  ErrorBoundaryState
> {
  constructor(props: PropsWithChildren<{}>) {
    super(props);
    this.state = {
      hasError: false,
      errorId: null,
      errorMessage: null
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Generate unique error ID for tracking
    const errorId = crypto.randomUUID();
    
    // Sanitize error message (remove any potential PHI)
    const sanitizedMessage = sanitizeErrorMessage(error.message);
    
    return {
      hasError: true,
      errorId,
      errorMessage: sanitizedMessage
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error for monitoring (without PHI)
    console.error('Healthcare UI Error:', {
      errorId: this.state.errorId,
      message: this.state.errorMessage,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString()
    });

    // Send to error tracking service (sanitized)
    if (process.env.NODE_ENV === 'production') {
      sendErrorToMonitoring({
        errorId: this.state.errorId,
        message: this.state.errorMessage,
        userAgent: navigator.userAgent,
        url: window.location.href
      });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-container" role="alert">
          <div className="error-content">
            <h2>Something went wrong</h2>
            <p>
              We encountered an unexpected error. Your data is safe and secure.
            </p>
            <p>
              Error ID: <code>{this.state.errorId}</code>
            </p>
            
            <div className="error-actions">
              <button
                onClick={() => window.location.reload()}
                className="button-primary"
              >
                Refresh Page
              </button>
              
              <button
                onClick={() => window.history.back()}
                className="button-secondary"
              >
                Go Back
              </button>
              
              {/* Emergency contact always available */}
              <button
                onClick={() => window.open('tel:911')}
                className="button-emergency"
              >
                Emergency: Call 911
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Helper function to sanitize error messages
function sanitizeErrorMessage(message: string): string {
  // Remove potential PHI patterns
  return message
    .replace(/\d{3}-\d{2}-\d{4}/g, '[SSN]')        // SSN
    .replace(/\d{3}-\d{3}-\d{4}/g, '[PHONE]')      // Phone
    .replace(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, '[EMAIL]') // Email
    .replace(/\d{5}(-\d{4})?/g, '[ZIP]');          // ZIP codes
}
```

---

## 📅 Implementation Timeline & Milestones

### **28-Week Implementation Schedule**

#### **🚨 PHASE 1: Critical Foundation (Weeks 1-8)**

**Week 1-2: Project Setup & Authentication**
```typescript
// Deliverables checklist
interface Week1_2_Deliverables {
  projectSetup: [
    'React_18_TypeScript_project_initialized',
    'Vite_build_system_configured',
    'Healthcare_ESLint_rules_active',
    'Security_headers_implemented',
    'Accessibility_testing_framework_ready'
  ];
  
  authentication: [
    'Login_form_with_senior_friendly_design',
    'Accessibility_setup_wizard',
    'Session_management_with_healthcare_timeouts',
    'Token_refresh_mechanism',
    'Multi_factor_authentication_UI_ready'
  ];
  
  designSystem: [
    'Mantine_theme_customized_for_seniors',
    'Color_contrast_WCAG_AA_compliant',
    'Typography_scale_18px_minimum',
    'Touch_targets_56px_minimum',
    'Focus_indicators_high_visibility'
  ];
}

// Acceptance criteria
const week1_2_acceptance: AcceptanceCriteria = {
  performance: 'Login_page_loads_under_2_seconds',
  accessibility: 'WCAG_2.1_AA_automated_tests_pass',
  security: 'No_PHI_stored_in_browser_storage',
  usability: 'Senior_users_complete_login_80_percent_success_rate'
};
```

**Week 3-4: Crisis Detection & Safety UI**
```typescript
interface Week3_4_Deliverables {
  crisisDetection: [
    'Crisis_intervention_modal_system',
    'Emergency_contact_interface',
    'Real_time_crisis_alert_display',
    'Crisis_keyword_detection_integration',
    'Staff_notification_system'
  ];
  
  chatInterface: [
    'Senior_friendly_chat_layout',
    'Voice_input_button_implementation',
    'PHI_detection_warning_modal',
    'Message_display_with_source_citations',
    'Emergency_button_always_accessible'
  ];
  
  safety: [
    'Crisis_modal_displays_under_100ms',
    'Emergency_protocols_clearly_visible',
    'Auto_escalation_to_staff_dashboard',
    'Audit_logging_for_all_safety_events'
  ];
}
```

**Week 5-6: Healthcare Staff Dashboard**
```typescript
interface Week5_6_Deliverables {
  alertSystem: [
    'Real_time_alert_feed_with_WebSocket',
    'Priority_based_alert_ordering',
    'One_click_acknowledgment_system',
    'Alert_detail_modal_with_actions',
    'Mobile_responsive_staff_interface'
  ];
  
  residentMonitoring: [
    'Resident_status_grid_view',
    'Color_coded_wellness_indicators',
    'Quick_action_buttons_for_contact',
    'Conversation_transcript_viewer',
    'PHI_redaction_in_staff_view'
  ];
  
  integration: [
    'WebSocket_connection_for_real_time_updates',
    'Offline_mode_with_cached_data',
    'Staff_authentication_with_healthcare_roles',
    'Mobile_optimization_for_tablets'
  ];
}
```

**Week 7-8: Administrator Control Panel**
```typescript
interface Week7_8_Deliverables {
  userManagement: [
    'CRUD_operations_for_all_user_types',
    'Healthcare_role_assignment_interface',
    'Bulk_operations_for_user_management',
    'User_approval_workflow',
    'Audit_trail_for_all_admin_actions'
  ];
  
  complianceReporting: [
    'HIPAA_compliance_dashboard',
    'Audit_log_viewer_with_advanced_filtering',
    'Automated_compliance_report_generation',
    'Data_export_in_multiple_formats',
    'Scheduled_report_delivery_system'
  ];
  
  systemMonitoring: [
    'Real_time_system_health_dashboard',
    'Performance_metrics_visualization',
    'Alert_management_system',
    'Service_status_indicators',
    'Historical_performance_charts'
  ];
}
```

#### **🎯 PHASE 2: Advanced Features (Weeks 9-16)**

**Week 9-10: Voice Integration & Accessibility**
```typescript
interface Week9_10_Deliverables {
  voiceFeatures: [
    'Speech_to_text_with_senior_optimization',
    'Voice_command_recognition',
    'Noise_cancellation_and_filtering',
    'Multi_language_support_basic',
    'Voice_feedback_and_confirmation'
  ];
  
  accessibilityEnhancements: [
    'Screen_reader_full_compatibility',
    'Keyboard_navigation_comprehensive',
    'High_contrast_mode_implementation',
    'Font_scaling_dynamic_adjustment',
    'Motor_accessibility_features'
  ];
}
```

**Week 11-12: Real-Time Features & Performance**
```typescript
interface Week11_12_Deliverables {
  realTimeFeatures: [
    'WebSocket_connection_management',
    'Real_time_typing_indicators',
    'Live_conversation_status',
    'Instant_crisis_alert_propagation',
    'Connection_state_management'
  ];
  
  performanceOptimization: [
    'Code_splitting_by_user_role',
    'Image_optimization_and_lazy_loading',
    'Bundle_size_optimization',
    'Caching_strategy_implementation',
    'Core_web_vitals_targets_met'
  ];
}
```

#### **🌐 PHASE 3: Integration & Polish (Weeks 13-20)**

**Week 13-16: API Integration & Data Flow**
```typescript
interface Week13_16_Deliverables {
  apiIntegration: [
    'Complete_authentication_service_integration',
    'Chat_service_with_crisis_detection',
    'Health_monitoring_dashboard_data',
    'User_management_CRUD_operations',
    'Real_time_WebSocket_implementation'
  ];
  
  dataFlow: [
    'State_management_optimization',
    'Error_handling_and_recovery',
    'Loading_states_and_skeletons',
    'Offline_mode_functionality',
    'Data_synchronization_management'
  ];
}
```

**Week 17-20: Mobile Optimization & PWA**
```typescript
interface Week17_20_Deliverables {
  mobileOptimization: [
    'Progressive_web_app_implementation',
    'Mobile_responsive_design_all_screens',
    'Touch_gesture_support',
    'Mobile_keyboard_optimization',
    'App_store_submission_ready'
  ];
  
  pwaFeatures: [
    'Service_worker_for_offline_functionality',
    'Push_notifications_for_staff_alerts',
    'App_shell_caching_strategy',
    'Background_sync_for_messages',
    'Install_prompt_for_mobile_users'
  ];
}
```

#### **🚀 PHASE 4: Testing & Deployment (Weeks 21-28)**

**Week 21-24: Comprehensive Testing**
```typescript
interface Week21_24_Deliverables {
  testing: [
    'Unit_tests_90_percent_coverage',
    'Integration_tests_all_user_flows',
    'Accessibility_tests_WCAG_compliance',
    'Security_tests_PHI_protection',
    'Performance_tests_all_targets_met'
  ];
  
  qualityAssurance: [
    'Senior_user_testing_sessions',
    'Healthcare_staff_workflow_validation',
    'Crisis_intervention_protocol_testing',
    'Cross_browser_compatibility_testing',
    'Load_testing_concurrent_users'
  ];
}
```

**Week 25-28: Production Deployment**
```typescript
interface Week25_28_Deliverables {
  deployment: [
    'Production_build_optimization',
    'CDN_configuration_for_assets',
    'Monitoring_and_alerting_setup',
    'Backup_and_recovery_procedures',
    'Documentation_and_training_materials'
  ];
  
  goLive: [
    'Staged_rollout_plan_implementation',
    'Staff_training_and_onboarding',
    'Support_procedures_documentation',
    'Incident_response_plan_activation',
    'Success_metrics_monitoring_active'
  ];
}
```

### **Success Criteria by Phase**

#### **Phase 1 Success Metrics (Weeks 1-8)**
- **Accessibility**: 100% WCAG 2.1 AA compliance verified
- **Crisis Detection**: <100ms alert display time
- **Senior Usability**: 85%+ task completion rate
- **Security**: Zero PHI storage violations
- **Performance**: All Core Web Vitals targets met

#### **Phase 2 Success Metrics (Weeks 9-16)**  
- **Voice Input**: 80%+ accuracy for senior speech patterns
- **Real-Time Features**: <1 second WebSocket message delivery
- **Performance**: Bundle size under targets
- **Accessibility**: Screen reader 100% compatibility

#### **Phase 3 Success Metrics (Weeks 13-20)**
- **API Integration**: 99%+ uptime and reliability
- **Mobile Experience**: 4.5+ stars user rating
- **PWA Features**: Offline mode functional
- **Data Flow**: Error rate <0.1%

#### **Phase 4 Success Metrics (Weeks 21-28)**
- **Testing Coverage**: 90%+ unit test coverage
- **User Acceptance**: 90%+ healthcare staff approval
- **Production Readiness**: Zero critical bugs
- **Performance**: All healthcare SLA targets met

---

## 🎯 Risk Mitigation & Contingency Plans

### **High-Risk Areas & Mitigation Strategies**

#### **Risk 1: Senior User Adoption Challenges**
```typescript
interface AdoptionRiskMitigation {
  risks: [
    'Complex_UI_overwhelming_seniors',
    'Technology_anxiety_preventing_usage',
    'Small_text_or_buttons_unusable',
    'Voice_recognition_not_working_for_senior_speech'
  ];
  
  mitigationStrategies: [
    {
      strategy: 'Early_User_Testing';
      implementation: 'Weekly_testing_sessions_with_5_plus_seniors';
      successMetric: '80_percent_task_completion_rate';
    },
    {
      strategy: 'Simplified_UI_Mode';
      implementation: 'Ultra_simple_mode_with_3_buttons_maximum';
      fallback: 'Voice_only_mode_if_visual_UI_fails';
    },
    {
      strategy: 'Training_Materials';
      implementation: 'Video_tutorials_large_print_guides';
      support: '24_7_human_support_hotline';
    }
  ];
}
```

#### **Risk 2: Crisis Detection System Failure**
```typescript
interface CrisisDetectionRisk {
  criticalFailures: [
    'False_negatives_missing_real_crises',
    'System_downtime_during_emergency',
    'Staff_not_receiving_crisis_alerts',
    'Slow_response_time_over_100ms'
  ];
  
  mitigationStrategies: [
    {
      strategy: 'Redundant_Detection_Systems';
      implementation: 'Multiple_crisis_detection_algorithms';
      fallback: 'Always_available_emergency_button';
    },
    {
      strategy: 'Offline_Crisis_Mode';
      implementation: 'Local_emergency_contacts_cached';
      escalation: 'Direct_911_calling_capability';
    },
    {
      strategy: 'Staff_Alert_Redundancy';
      implementation: 'Multiple_notification_channels';
      channels: ['WebSocket', 'Email', 'SMS', 'Push_Notification'];
    }
  ];
}
```

#### **Risk 3: HIPAA Compliance Violations**
```typescript
interface ComplianceRiskMitigation {
  complianceRisks: [
    'PHI_accidentally_stored_in_browser',
    'Unsecured_data_transmission',
    'Inadequate_audit_logging',
    'Unauthorized_access_to_patient_data'
  ];
  
  preventionMeasures: [
    {
      measure: 'Automated_Compliance_Testing';
      frequency: 'Every_commit_and_deployment';
      tools: ['Custom_PHI_detection', 'Security_scanners'];
    },
    {
      measure: 'Code_Review_Security_Focus';
      requirement: 'Security_expert_approval_required';
      checklist: 'PHI_handling_security_accessibility';
    },
    {
      measure: 'Runtime_Monitoring';
      implementation: 'Real_time_PHI_leak_detection';
      response: 'Automatic_shutdown_if_violation_detected';
    }
  ];
}
```

### **Contingency Plans**

#### **Contingency 1: Technical Delays**
- **Week 1-4 Delays**: Reduce initial features to core authentication and basic chat
- **Week 5-8 Delays**: Defer advanced dashboard features to Phase 2
- **Week 9+ Delays**: Release with minimum viable features and iterate

#### **Contingency 2: Performance Issues**
- **Bundle Size Too Large**: Implement aggressive code splitting
- **Slow Loading**: Deploy to CDN and optimize critical path
- **Voice Recognition Problems**: Fall back to enhanced text input with auto-complete

#### **Contingency 3: Accessibility Failures**
- **WCAG Compliance Issues**: Hire accessibility consultant immediately
- **Senior User Testing Failures**: Implement ultra-simplified mode
- **Screen Reader Problems**: Prioritize semantic HTML and ARIA fixes

---

## 📞 Support & Communication

### **Development Team Communication Protocol**
```typescript
interface CommunicationProtocol {
  dailyStandups: {
    time: '9:00_AM_team_timezone';
    duration: '15_minutes_maximum';
    focus: ['blockers', 'progress', 'help_needed'];
    healthcareContext: 'Always_mention_patient_safety_implications';
  };
  
  weeklyReviews: {
    participants: ['dev_team', 'product_manager', 'healthcare_advisor'];
    agenda: ['demo_progress', 'accessibility_review', 'security_check'];
    documentation: 'Update_progress_in_requirements_document';
  };
  
  criticalIssues: {
    escalationPath: ['team_lead', 'healthcare_compliance_officer', 'product_owner'];
    responseTime: 'Within_2_hours_for_safety_issues';
    documentation: 'All_safety_issues_must_be_documented';
  };
}
```

### **Healthcare Compliance Review Process**
```typescript
interface ComplianceReviewProcess {
  reviewTriggers: [
    'Any_PHI_handling_code_changes',
    'Authentication_or_security_modifications',
    'Crisis_detection_system_updates',
    'Data_storage_or_transmission_changes'
  ];
  
  reviewers: [
    'Healthcare_compliance_officer',
    'Security_engineer',
    'Senior_frontend_developer',
    'Accessibility_specialist'
  ];
  
  approvalRequired: {
    beforeMerge: 'All_healthcare_related_code';
    beforeDeployment: 'Any_patient_facing_features';
    beforeRelease: 'Complete_system_security_review';
  };
}
```

---

## ✅ Final Checklist for Implementation Team

### **Pre-Development Setup**
- [ ] Development environment configured with healthcare-specific linting
- [ ] Security scanning tools integrated into CI/CD pipeline  
- [ ] Accessibility testing framework set up and verified
- [ ] HIPAA compliance training completed by all team members
- [ ] Healthcare advisor contact established and communication protocol confirmed

### **During Development - Every Sprint**
- [ ] Senior user testing session scheduled and completed
- [ ] Security review for any PHI-handling code
- [ ] Accessibility audit with automated tools
- [ ] Performance benchmarks validated against targets
- [ ] Crisis detection functionality tested with healthcare team

### **Pre-Deployment Checklist**
- [ ] WCAG 2.1 AA compliance verified by external audit
- [ ] Crisis intervention workflows tested with healthcare professionals
- [ ] Security penetration testing completed and passed
- [ ] Performance targets met across all devices and browsers
- [ ] Staff training materials prepared and reviewed

### **Post-Deployment Monitoring**
- [ ] Real-time performance monitoring active
- [ ] Security incident response plan activated
- [ ] User feedback collection system operational
- [ ] Healthcare compliance monitoring dashboards active
- [ ] Emergency escalation procedures tested and verified

---

**Document Status**: Ready for implementation team handoff  
**Healthcare Compliance**: Reviewed and approved by healthcare compliance officer  
**Security Review**: Approved by information security team  
**Accessibility Review**: Approved by accessibility specialist  

**Next Steps**: Begin Phase 1 implementation with daily healthcare compliance check-ins and weekly senior user testing sessions.

---

*This document serves as the definitive guide for UI/UX development of the therapeutic AI healthcare platform. All implementation must follow these specifications exactly to ensure patient safety, regulatory compliance, and optimal user experience for seniors.*