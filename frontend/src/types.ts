export interface ResumeAnalysis {
  skills: string[];
  projects: { name: string; description: string; tech: string[] }[];
  yearsOfExperience: number;
  techStack: string[];
  weakAreas: string[];
  summary: string;
}

export interface JDAnalysis {
  requiredSkills: string[];
  preferredSkills: string[];
  responsibilities: string[];
  level: string;
  csFundamentals: string[];
  typicalAlgorithmTopics: string[];
  summary: string;
}

export interface CrossAnalysis {
  matchScore: number;
  strongPoints: string[];
  weakPoints: string[];
  mustAskProjects: string[];
  mustAskFundamentals: string[];
  mustAskCoding: string[];
  strategy: string;
}

export interface RoundRecord {
  roundNumber: number;
  depth: number;
  questionType: string;
  topic: string;
  question: string;
  answer: string;
  score: number;
  briefFeedback: string;
  coveredWeakness: string | null;
  detailedFeedback?: DetailedFeedback;
}

export interface DetailedFeedback {
  scoreBreakdown: { accuracy: number; depth: number; clarity: number; practicality: number };
  whatWasGood: string[];
  whatWasMissing: string[];
  modelAnswerOutline: string[];
  keyTakeaways: string[];
  recommendedResources: string[];
}

export interface LLMReport {
  overallVerdict: string;
  strengthsSummary: string[];
  weaknessesSummary: string[];
  detailedRoundAnalysis: {
    roundNumber: number;
    questionType: string;
    topic: string;
    score: number;
    briefRecap: string;
    gapAnalysis: string;
    thinkingFramework: string;
    modelResponse: string[];
  }[];
  improvementPlan: {
    area: string;
    priority: string;
    actionItems: string[];
    estimatedTimeframe: string;
  }[];
  nextInterviewPrep: {
    focusAreas: string[];
    mockSuggestions: string[];
    resources: string[];
  };
}

export interface InterviewReport {
  sessionId: string;
  totalRounds: number;
  rounds: RoundRecord[];
  metrics: {
    overallScore: number;
    weaknessCoverage: number;
    depthAdaptability: number | null;
    knowledgeAuthenticity: number | null;
    improvementTrajectory: number;
  };
  weakPointsRemaining: string[];
  weakPointsCovered: string[];
  llmReport: LLMReport;
}

export interface StartResponse {
  sessionId: string;
  maxRounds: number;
  analysis: {
    resume: ResumeAnalysis;
    jd: JDAnalysis;
    matchScore: number;
    strongPoints: string[];
    weakPoints: string[];
    mustAskProjects: string[];
    mustAskFundamentals: string[];
    mustAskCoding: string[];
  };
  firstQuestion: {
    round: number;
    depth: number;
    questionType: string;
    topic: string;
    content: string;
  };
}
