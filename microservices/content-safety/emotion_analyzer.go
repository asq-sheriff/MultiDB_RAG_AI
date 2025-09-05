package main

import (
	"fmt"
	"math"
	"regexp"
	"strings"
	"time"

	"go.uber.org/zap"
)

// EmotionAnalyzer handles emotion analysis for therapeutic conversations
type EmotionAnalyzer struct {
	logger           *zap.Logger
	emotionPatterns  map[EmotionLabel][]*regexp.Regexp
	valenceMappings  map[EmotionLabel]float64
	arousalMappings  map[EmotionLabel]float64
	crisisPatterns   map[string][]*regexp.Regexp
	supportTemplates map[string][]SupportRecommendation
}

// NewEmotionAnalyzer creates a new emotion analyzer
func NewEmotionAnalyzer(logger *zap.Logger) *EmotionAnalyzer {
	ea := &EmotionAnalyzer{
		logger: logger,
	}
	
	ea.loadEmotionPatterns()
	ea.loadValenceMappings()
	ea.loadArousalMappings()
	ea.loadCrisisPatterns()
	ea.loadSupportTemplates()
	
	logger.Info("✅ Emotion Analyzer initialized")
	return ea
}

// loadEmotionPatterns loads regex patterns for emotion detection
func (ea *EmotionAnalyzer) loadEmotionPatterns() {
	ea.emotionPatterns = map[EmotionLabel][]*regexp.Regexp{
		EmotionHappy: {
			regexp.MustCompile(`(?i)\b(?:happy|joy|joyful|cheerful|delighted|excited|thrilled)\b`),
			regexp.MustCompile(`(?i)\bfeeling\s+(?:good|great|wonderful|amazing|fantastic)\b`),
			regexp.MustCompile(`(?i)\b(?:love|loving|adore)\b`),
			regexp.MustCompile(`(?i)\b(?:smile|smiling|laughing|laugh)\b`),
		},
		EmotionSad: {
			regexp.MustCompile(`(?i)\b(?:sad|sadness|down|depressed|blue|melancholy)\b`),
			regexp.MustCompile(`(?i)\bfeeling\s+(?:down|low|terrible|awful|horrible)\b`),
			regexp.MustCompile(`(?i)\b(?:cry|crying|tears|weeping)\b`),
			regexp.MustCompile(`(?i)\b(?:grief|grieving|mourning)\b`),
		},
		EmotionAngry: {
			regexp.MustCompile(`(?i)\b(?:angry|anger|mad|furious|rage|irritated|annoyed)\b`),
			regexp.MustCompile(`(?i)\bfeeling\s+(?:angry|mad|frustrated|irritated)\b`),
			regexp.MustCompile(`(?i)\b(?:hate|hating|despise|resent)\b`),
			regexp.MustCompile(`(?i)\b(?:upset|outraged|livid)\b`),
		},
		EmotionAnxious: {
			regexp.MustCompile(`(?i)\b(?:anxious|anxiety|worried|worry|nervous|stressed)\b`),
			regexp.MustCompile(`(?i)\bfeeling\s+(?:anxious|worried|nervous|stressed|tense)\b`),
			regexp.MustCompile(`(?i)\b(?:panic|panicked|overwhelmed|frantic)\b`),
			regexp.MustCompile(`(?i)\b(?:fear|afraid|scared|frightened)\b`),
		},
		EmotionCalm: {
			regexp.MustCompile(`(?i)\b(?:calm|peaceful|serene|tranquil|relaxed)\b`),
			regexp.MustCompile(`(?i)\bfeeling\s+(?:calm|peaceful|relaxed|serene|content)\b`),
			regexp.MustCompile(`(?i)\b(?:zen|centered|balanced|composed)\b`),
			regexp.MustCompile(`(?i)\b(?:meditation|meditat|mindful)\b`),
		},
		EmotionLonely: {
			regexp.MustCompile(`(?i)\b(?:lonely|loneliness|alone|isolated|abandoned)\b`),
			regexp.MustCompile(`(?i)\bfeeling\s+(?:lonely|alone|isolated|abandoned)\b`),
			regexp.MustCompile(`(?i)\b(?:nobody|no one)\s+(?:cares|calls|visits)\b`),
			regexp.MustCompile(`(?i)\b(?:solitude|seclusion|disconnected)\b`),
		},
		EmotionFrustrated: {
			regexp.MustCompile(`(?i)\b(?:frustrated|frustration|stuck|blocked)\b`),
			regexp.MustCompile(`(?i)\bfeeling\s+(?:frustrated|stuck|helpless|powerless)\b`),
			regexp.MustCompile(`(?i)\bcan'?t\s+(?:do|handle|manage)\b`),
			regexp.MustCompile(`(?i)\b(?:giving up|hopeless|defeated)\b`),
		},
		EmotionExcited: {
			regexp.MustCompile(`(?i)\b(?:excited|excitement|enthusiastic|eager)\b`),
			regexp.MustCompile(`(?i)\bfeeling\s+(?:excited|enthusiastic|energetic|pumped)\b`),
			regexp.MustCompile(`(?i)\b(?:can'?t wait|looking forward|anticipating)\b`),
			regexp.MustCompile(`(?i)\b(?:thrilled|elated|ecstatic)\b`),
		},
		EmotionContent: {
			regexp.MustCompile(`(?i)\b(?:content|satisfied|pleased|comfortable)\b`),
			regexp.MustCompile(`(?i)\bfeeling\s+(?:content|satisfied|okay|fine|alright)\b`),
			regexp.MustCompile(`(?i)\b(?:grateful|thankful|appreciative)\b`),
			regexp.MustCompile(`(?i)\b(?:doing\s+(?:well|okay|fine))\b`),
		},
	}
}

// loadValenceMappings loads valence scores for emotions (-1 negative, +1 positive)
func (ea *EmotionAnalyzer) loadValenceMappings() {
	ea.valenceMappings = map[EmotionLabel]float64{
		EmotionHappy:      0.8,
		EmotionExcited:    0.7,
		EmotionContent:    0.4,
		EmotionCalm:       0.2,
		EmotionNeutral:    0.0,
		EmotionFrustrated: -0.3,
		EmotionAnxious:    -0.5,
		EmotionLonely:     -0.6,
		EmotionAngry:      -0.7,
		EmotionSad:        -0.8,
	}
}

// loadArousalMappings loads arousal scores for emotions (-1 low, +1 high)
func (ea *EmotionAnalyzer) loadArousalMappings() {
	ea.arousalMappings = map[EmotionLabel]float64{
		EmotionExcited:    0.8,
		EmotionAngry:      0.6,
		EmotionAnxious:    0.5,
		EmotionHappy:      0.3,
		EmotionFrustrated: 0.2,
		EmotionNeutral:    0.0,
		EmotionContent:    -0.2,
		EmotionSad:        -0.3,
		EmotionLonely:     -0.4,
		EmotionCalm:       -0.7,
	}
}

// loadCrisisPatterns loads crisis detection patterns for emotions
func (ea *EmotionAnalyzer) loadCrisisPatterns() {
	ea.crisisPatterns = map[string][]*regexp.Regexp{
		"suicidal": {
			regexp.MustCompile(`(?i)\b(?:kill myself|end my life|suicide|suicidal)\b`),
			regexp.MustCompile(`(?i)\b(?:want to die|better off dead|no point living)\b`),
			regexp.MustCompile(`(?i)\b(?:planning to|going to)\s+(?:end it|kill myself)\b`),
		},
		"self_harm": {
			regexp.MustCompile(`(?i)\b(?:cut myself|self harm|hurt myself)\b`),
			regexp.MustCompile(`(?i)\b(?:cutting|razor|blade)\s+(?:myself|arms|wrists)\b`),
			regexp.MustCompile(`(?i)\bself[\s-]injury\b`),
		},
		"extreme_distress": {
			regexp.MustCompile(`(?i)\b(?:can'?t take it|can'?t go on|unbearable)\b`),
			regexp.MustCompile(`(?i)\b(?:completely hopeless|totally helpless)\b`),
			regexp.MustCompile(`(?i)\b(?:severe|extreme)\s+(?:pain|suffering|depression)\b`),
		},
		"crisis_emergency": {
			regexp.MustCompile(`(?i)\bemergency\b`),
			regexp.MustCompile(`(?i)\bcall\s+(?:911|ambulance|help)\b`),
			regexp.MustCompile(`(?i)\b(?:overdose|pills|medication)\s+(?:to end|too many)\b`),
		},
	}
}

// loadSupportTemplates loads support recommendation templates
func (ea *EmotionAnalyzer) loadSupportTemplates() {
	ea.supportTemplates = map[string][]SupportRecommendation{
		"crisis": {
			{
				Type:         "immediate_crisis_support",
				Description:  "Contact crisis support immediately for safety",
				Priority:     "critical",
				ResourceLinks: []string{"https://988lifeline.org", "tel:988"},
			},
			{
				Type:         "emergency_services",
				Description:  "Call emergency services if in immediate danger",
				Priority:     "critical",
				ResourceLinks: []string{"tel:911", "https://www.emergencysos.com"},
			},
		},
		"high_distress": {
			{
				Type:         "professional_support",
				Description:  "Consider reaching out to a mental health professional",
				Priority:     "high",
				ResourceLinks: []string{"https://www.psychologytoday.com", "https://www.betterhelp.com"},
			},
			{
				Type:         "crisis_text_line",
				Description:  "Text-based crisis support available 24/7",
				Priority:     "high",
				ResourceLinks: []string{"https://www.crisistextline.org", "sms:741741"},
			},
		},
		"moderate_support": {
			{
				Type:         "self_care_strategies",
				Description:  "Focus on self-care and stress management techniques",
				Priority:     "medium",
				ResourceLinks: []string{"https://www.mindful.org", "https://www.headspace.com"},
			},
			{
				Type:         "social_support",
				Description:  "Connect with friends, family, or support groups",
				Priority:     "medium",
				ResourceLinks: []string{"https://www.nami.org", "https://www.supportgroups.com"},
			},
		},
		"positive_reinforcement": {
			{
				Type:         "maintain_wellness",
				Description:  "Continue positive practices and self-care",
				Priority:     "low",
				ResourceLinks: []string{"https://www.wellness.com", "https://www.gratitude-app.com"},
			},
			{
				Type:         "mindfulness",
				Description:  "Practice mindfulness and present-moment awareness",
				Priority:     "low",
				ResourceLinks: []string{"https://www.calm.com", "https://insighttimer.com"},
			},
		},
	}
}

// AnalyzeEmotion performs comprehensive emotion analysis
func (ea *EmotionAnalyzer) AnalyzeEmotion(content string, ctx *RequestContext) (*EmotionAnalysisResult, error) {
	ea.logger.Info("Analyzing emotion",
		zap.String("request_id", ctx.RequestID),
		zap.String("user_id", ctx.UserID),
		zap.Int("content_length", len(content)),
	)

	startTime := time.Now()

	// 1. Detect emotions using pattern matching
	emotionScores := ea.detectEmotions(content)

	// 2. Determine primary emotion
	primaryEmotion := ea.getPrimaryEmotion(emotionScores)

	// 3. Calculate valence and arousal
	valence := ea.calculateValence(emotionScores)
	arousal := ea.calculateArousal(emotionScores)

	// 4. Calculate confidence
	confidence := ea.calculateEmotionConfidence(emotionScores)

	// 5. Detect crisis indicators
	crisisIndicators := ea.detectCrisisIndicators(content)
	isCrisis := len(crisisIndicators) > 0

	// 6. Generate support recommendations
	supportRecommendations := ea.generateSupportRecommendations(primaryEmotion, crisisIndicators, emotionScores)

	// 7. Determine intervention level
	interventionLevel := ea.determineInterventionLevel(primaryEmotion, crisisIndicators, valence, arousal)

	processingTime := float64(time.Since(startTime).Nanoseconds()) / 1e6

	result := &EmotionAnalysisResult{
		Label:                   primaryEmotion,
		Valence:                valence,
		Arousal:                arousal,
		Confidence:             confidence,
		EmotionScores:          emotionScores,
		CrisisIndicators:       crisisIndicators,
		SupportRecommendations: supportRecommendations,
		IsCrisis:               isCrisis,
		InterventionLevel:      interventionLevel,
		ProcessingTimeMS:       processingTime,
	}

	ea.logger.Info("Emotion analysis completed",
		zap.String("request_id", ctx.RequestID),
		zap.String("primary_emotion", string(primaryEmotion)),
		zap.Float64("valence", valence),
		zap.Float64("arousal", arousal),
		zap.Bool("is_crisis", isCrisis),
		zap.Float64("processing_time_ms", processingTime),
	)

	return result, nil
}

// detectEmotions detects emotions using pattern matching
func (ea *EmotionAnalyzer) detectEmotions(content string) []EmotionScore {
	emotionScores := []EmotionScore{}
	words := strings.Fields(content)
	wordCount := len(words)

	for emotion, patterns := range ea.emotionPatterns {
		matches := 0
		totalConfidence := 0.0

		for _, pattern := range patterns {
			patternMatches := pattern.FindAllString(content, -1)
			matches += len(patternMatches)
			totalConfidence += float64(len(patternMatches)) * 0.8 // Base confidence
		}

		if matches > 0 {
			// Calculate confidence based on match count and content length
			confidence := math.Min(totalConfidence/float64(wordCount+1), 1.0)
			emotionScores = append(emotionScores, EmotionScore{
				Emotion:    emotion,
				Confidence: confidence,
			})
		}
	}

	// If no emotions detected, default to neutral
	if len(emotionScores) == 0 {
		emotionScores = append(emotionScores, EmotionScore{
			Emotion:    EmotionNeutral,
			Confidence: 0.6,
		})
	}

	return emotionScores
}

// getPrimaryEmotion gets the primary emotion from scores
func (ea *EmotionAnalyzer) getPrimaryEmotion(emotionScores []EmotionScore) EmotionLabel {
	if len(emotionScores) == 0 {
		return EmotionNeutral
	}

	// Return emotion with highest confidence
	maxConfidence := 0.0
	primaryEmotion := EmotionNeutral

	for _, score := range emotionScores {
		if score.Confidence > maxConfidence {
			maxConfidence = score.Confidence
			primaryEmotion = score.Emotion
		}
	}

	return primaryEmotion
}

// calculateValence calculates emotional valence (-1 negative, +1 positive)
func (ea *EmotionAnalyzer) calculateValence(emotionScores []EmotionScore) float64 {
	if len(emotionScores) == 0 {
		return 0.0
	}

	totalWeight := 0.0
	weightedValence := 0.0

	for _, score := range emotionScores {
		valence, exists := ea.valenceMappings[score.Emotion]
		if !exists {
			valence = 0.0
		}
		weight := score.Confidence

		weightedValence += valence * weight
		totalWeight += weight
	}

	if totalWeight > 0 {
		return weightedValence / totalWeight
	}
	return 0.0
}

// calculateArousal calculates emotional arousal (-1 low, +1 high)
func (ea *EmotionAnalyzer) calculateArousal(emotionScores []EmotionScore) float64 {
	if len(emotionScores) == 0 {
		return 0.0
	}

	totalWeight := 0.0
	weightedArousal := 0.0

	for _, score := range emotionScores {
		arousal, exists := ea.arousalMappings[score.Emotion]
		if !exists {
			arousal = 0.0
		}
		weight := score.Confidence

		weightedArousal += arousal * weight
		totalWeight += weight
	}

	if totalWeight > 0 {
		return weightedArousal / totalWeight
	}
	return 0.0
}

// calculateEmotionConfidence calculates overall confidence in emotion detection
func (ea *EmotionAnalyzer) calculateEmotionConfidence(emotionScores []EmotionScore) float64 {
	if len(emotionScores) == 0 {
		return 0.0
	}

	// Use highest confidence score
	maxConfidence := 0.0
	for _, score := range emotionScores {
		if score.Confidence > maxConfidence {
			maxConfidence = score.Confidence
		}
	}

	// Adjust based on number of detected emotions (more = less certain)
	adjustment := 1.0 / (1.0 + float64(len(emotionScores))*0.1)

	return maxConfidence * adjustment
}

// detectCrisisIndicators detects crisis indicators requiring immediate attention
func (ea *EmotionAnalyzer) detectCrisisIndicators(content string) []CrisisIndicator {
	indicators := []CrisisIndicator{}

	for crisisType, patterns := range ea.crisisPatterns {
		for _, pattern := range patterns {
			matches := pattern.FindAllStringIndex(content, -1)
			for range matches {
				severity := ea.getCrisisSeverity(crisisType)
				requiresImmediate := crisisType == "suicidal" || crisisType == "crisis_emergency"

				indicator := CrisisIndicator{
					Type:                        crisisType,
					Description:                 fmt.Sprintf("Crisis indicator detected: %s", crisisType),
					Severity:                    severity,
					Confidence:                  0.9,
					RequiresImmediateAttention:  requiresImmediate,
				}
				indicators = append(indicators, indicator)
			}
		}
	}

	return indicators
}

// getCrisisSeverity gets severity level for crisis type
func (ea *EmotionAnalyzer) getCrisisSeverity(crisisType string) RiskLevel {
	severityMapping := map[string]RiskLevel{
		"suicidal":         RiskCritical,
		"self_harm":        RiskHigh,
		"crisis_emergency": RiskCritical,
		"extreme_distress": RiskHigh,
	}
	
	if severity, exists := severityMapping[crisisType]; exists {
		return severity
	}
	return RiskMedium
}

// generateSupportRecommendations generates appropriate support recommendations
func (ea *EmotionAnalyzer) generateSupportRecommendations(primaryEmotion EmotionLabel, crisisIndicators []CrisisIndicator, emotionScores []EmotionScore) []SupportRecommendation {
	recommendations := []SupportRecommendation{}

	// Crisis-based recommendations (highest priority)
	if len(crisisIndicators) > 0 {
		criticalIndicators := ea.filterCrisisIndicatorsBySeverity(crisisIndicators, RiskCritical)
		highIndicators := ea.filterCrisisIndicatorsBySeverity(crisisIndicators, RiskHigh)

		if len(criticalIndicators) > 0 {
			recommendations = append(recommendations, ea.supportTemplates["crisis"]...)
		} else if len(highIndicators) > 0 {
			recommendations = append(recommendations, ea.supportTemplates["high_distress"]...)
		}
	}

	// Emotion-based recommendations
	negativeEmotions := []EmotionLabel{EmotionSad, EmotionAngry, EmotionAnxious, EmotionLonely, EmotionFrustrated}
	positiveEmotions := []EmotionLabel{EmotionHappy, EmotionExcited, EmotionContent, EmotionCalm}

	if ea.contains(negativeEmotions, primaryEmotion) {
		// Check if already have crisis recommendations
		if !ea.hasCriticalPriority(recommendations) {
			highDistressEmotions := []EmotionLabel{EmotionSad, EmotionAnxious, EmotionLonely}
			if ea.contains(highDistressEmotions, primaryEmotion) {
				recommendations = append(recommendations, ea.supportTemplates["high_distress"]...)
			} else {
				recommendations = append(recommendations, ea.supportTemplates["moderate_support"]...)
			}
		}
	} else if ea.contains(positiveEmotions, primaryEmotion) {
		recommendations = append(recommendations, ea.supportTemplates["positive_reinforcement"]...)
	} else {
		// Neutral or other emotions
		recommendations = append(recommendations, ea.supportTemplates["moderate_support"]...)
	}

	return ea.removeDuplicateRecommendations(recommendations)
}

// determineInterventionLevel determines level of intervention needed
func (ea *EmotionAnalyzer) determineInterventionLevel(primaryEmotion EmotionLabel, crisisIndicators []CrisisIndicator, valence, arousal float64) RiskLevel {
	// Crisis indicators override everything
	if len(crisisIndicators) > 0 {
		maxSeverity := RiskNone
		for _, indicator := range crisisIndicators {
			if ea.isHigherRisk(indicator.Severity, maxSeverity) {
				maxSeverity = indicator.Severity
			}
		}
		return maxSeverity
	}

	// High negative valence with high arousal = high risk
	if valence <= -0.6 && arousal >= 0.4 {
		return RiskHigh
	}

	// Moderate negative valence = medium risk
	if valence <= -0.3 {
		return RiskMedium
	}

	// Slightly negative or neutral = low risk
	if valence <= 0.2 {
		return RiskLow
	}

	// Positive valence = no intervention needed
	return RiskNone
}

// Helper functions

func (ea *EmotionAnalyzer) contains(slice []EmotionLabel, item EmotionLabel) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

func (ea *EmotionAnalyzer) filterCrisisIndicatorsBySeverity(indicators []CrisisIndicator, severity RiskLevel) []CrisisIndicator {
	filtered := []CrisisIndicator{}
	for _, indicator := range indicators {
		if indicator.Severity == severity {
			filtered = append(filtered, indicator)
		}
	}
	return filtered
}

func (ea *EmotionAnalyzer) hasCriticalPriority(recommendations []SupportRecommendation) bool {
	for _, rec := range recommendations {
		if rec.Priority == "critical" {
			return true
		}
	}
	return false
}

func (ea *EmotionAnalyzer) removeDuplicateRecommendations(recommendations []SupportRecommendation) []SupportRecommendation {
	seen := make(map[string]bool)
	result := []SupportRecommendation{}

	for _, rec := range recommendations {
		key := rec.Type + rec.Description
		if !seen[key] {
			seen[key] = true
			result = append(result, rec)
		}
	}

	return result
}

func (ea *EmotionAnalyzer) isHigherRisk(a, b RiskLevel) bool {
	riskOrder := map[RiskLevel]int{
		RiskNone:     0,
		RiskLow:      1,
		RiskMedium:   2,
		RiskHigh:     3,
		RiskCritical: 4,
	}
	return riskOrder[a] > riskOrder[b]
}