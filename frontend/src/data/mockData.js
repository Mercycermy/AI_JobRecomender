export const experienceLevels = [
  'Internship',
  'Junior (0-2 yr)',
  'Mid (3-5 yr)',
  'Senior (6+ yr)',
]

export const categories = [
  'Engineering',
  'Design',
  'Data Science',
  'Product',
  'Marketing',
]

export const fallbackQuestions = [
  {
    id: 'q1',
    number: 1,
    total: 5,
    stem: 'Which kind of work gives you the most energy?',
    options: [
      'Designing user-facing experiences',
      'Finding patterns in data',
      'Building reliable systems',
      'Planning product direction',
    ],
  },
  {
    id: 'q2',
    number: 2,
    total: 5,
    stem: 'How do you usually solve a new technical problem?',
    options: [
      'Sketch the user journey first',
      'Explore examples and datasets',
      'Break it into modules',
      'Define goals and tradeoffs',
    ],
  },
  {
    id: 'q3',
    number: 3,
    total: 5,
    stem: 'Which skill would you most like to sharpen next?',
    options: ['SQL', 'React', 'Stakeholder research', 'Model evaluation'],
  },
  {
    id: 'q4',
    number: 4,
    total: 5,
    stem: 'What kind of feedback feels most useful to you?',
    options: [
      'A visual critique',
      'A measurable benchmark',
      'A code review',
      'A strategic roadmap',
    ],
  },
  {
    id: 'q5',
    number: 5,
    total: 5,
    stem: 'Pick the outcome you want from your next role.',
    options: [
      'Craft polished products',
      'Make smarter decisions with data',
      'Own complex systems',
      'Lead cross-functional momentum',
    ],
  },
]

export const jobRecommendations = [
  {
    id: 'product-analyst',
    title: 'Product Analyst',
    company: 'SignalWorks Labs',
    category: 'Product',
    experience: 'Mid (3-5 yr)',
    match: 92,
    skills: ['SQL', 'Experimentation', 'Storytelling'],
    readiness: 86,
  },
  {
    id: 'frontend-engineer',
    title: 'Frontend Engineer',
    company: 'Northstar AI',
    category: 'Engineering',
    experience: 'Junior (0-2 yr)',
    match: 78,
    skills: ['React', 'Accessibility', 'APIs'],
    readiness: 81,
  },
  {
    id: 'data-associate',
    title: 'Data Associate',
    company: 'Kinetic Careers',
    category: 'Data Science',
    experience: 'Junior (0-2 yr)',
    match: 71,
    skills: ['Python', 'Dashboards', 'Statistics'],
    readiness: 72,
  },
  {
    id: 'ux-researcher',
    title: 'UX Researcher',
    company: 'Brightpath Studio',
    category: 'Design',
    experience: 'Mid (3-5 yr)',
    match: 64,
    skills: ['Interviews', 'Synthesis', 'Journey Maps'],
    readiness: 69,
  },
  {
    id: 'growth-marketer',
    title: 'Growth Marketer',
    company: 'LaunchGrid',
    category: 'Marketing',
    experience: 'Senior (6+ yr)',
    match: 48,
    skills: ['Lifecycle', 'Analytics', 'Copywriting'],
    readiness: 58,
  },
  {
    id: 'ml-ops-specialist',
    title: 'ML Ops Specialist',
    company: 'ModelForge',
    category: 'Engineering',
    experience: 'Senior (6+ yr)',
    match: 43,
    skills: ['Pipelines', 'Monitoring', 'Cloud'],
    readiness: 54,
  },
]

export const skillGaps = [
  {
    skill: 'Experiment Design',
    level: 'Intermediate',
    current: 52,
    required: 85,
    priority: 96,
  },
  {
    skill: 'SQL Window Functions',
    level: 'Advanced',
    current: 62,
    required: 90,
    priority: 88,
  },
  {
    skill: 'Portfolio Storytelling',
    level: 'Intermediate',
    current: 58,
    required: 82,
    priority: 80,
  },
  {
    skill: 'Stakeholder Mapping',
    level: 'Beginner',
    current: 45,
    required: 70,
    priority: 74,
  },
]

export const learningResources = [
  {
    skill: 'Experiment Design',
    title: 'A/B Testing Foundations',
    platform: 'Coursera',
    level: 'Intermediate',
    hours: 8,
    url: 'https://www.coursera.org/',
  },
  {
    skill: 'Experiment Design',
    title: 'Product Metrics Playbook',
    platform: 'Reforge',
    level: 'Advanced',
    hours: 6,
    url: 'https://www.reforge.com/',
  },
  {
    skill: 'SQL Window Functions',
    title: 'Advanced SQL for Analytics',
    platform: 'Mode',
    level: 'Intermediate',
    hours: 5,
    url: 'https://mode.com/sql-tutorial/',
  },
  {
    skill: 'SQL Window Functions',
    title: 'Query Patterns for Product Data',
    platform: 'DataCamp',
    level: 'Advanced',
    hours: 7,
    url: 'https://www.datacamp.com/',
  },
  {
    skill: 'Portfolio Storytelling',
    title: 'Case Study Narrative Clinic',
    platform: 'ADPList',
    level: 'Beginner',
    hours: 3,
    url: 'https://adplist.org/',
  },
]

export const resumeTips = [
  {
    section: 'Summary',
    icon: '01',
    tips: [
      'Lead with a measurable role target, not a generic objective.',
      'Name your strongest domain signal in the first sentence.',
    ],
  },
  {
    section: 'Experience',
    icon: '02',
    tips: [
      'Turn project bullets into impact statements with metrics.',
      'Show the decision you influenced, not only the task you completed.',
    ],
  },
  {
    section: 'Skills',
    icon: '03',
    tips: [
      'Group tools by workflow: analysis, delivery, collaboration.',
      'Keep your top matched skills visible above older tools.',
    ],
  },
  {
    section: 'Keywords',
    icon: '04',
    tips: [
      'Mirror job posting language for core skills without keyword stuffing.',
      'Include role-specific nouns such as experimentation, dashboards, APIs, and research synthesis.',
    ],
  },
]

export const adminMetrics = [
  {
    label: 'Active Assessments',
    value: '128',
    delta: '+18%',
    tone: 'good',
  },
  {
    label: 'Jobs Indexed',
    value: '31.4k',
    delta: '+2.1k',
    tone: 'good',
  },
  {
    label: 'Question Coverage',
    value: '84%',
    delta: '12 gaps',
    tone: 'warn',
  },
  {
    label: 'Model Drift',
    value: 'Low',
    delta: '0.08',
    tone: 'good',
  },
]

export const adminJobs = [
  {
    id: 'job-1032',
    title: 'Product Analyst',
    category: 'Product',
    source: 'CSV import',
    status: 'Published',
    quality: 94,
    updated: '2h ago',
  },
  {
    id: 'job-1047',
    title: 'Frontend Engineer',
    category: 'Engineering',
    source: 'Manual review',
    status: 'Published',
    quality: 88,
    updated: '6h ago',
  },
  {
    id: 'job-1088',
    title: 'ML Ops Specialist',
    category: 'Engineering',
    source: 'Vector rebuild',
    status: 'Needs review',
    quality: 61,
    updated: '1d ago',
  },
  {
    id: 'job-1104',
    title: 'Growth Marketer',
    category: 'Marketing',
    source: 'CSV import',
    status: 'Draft',
    quality: 53,
    updated: '2d ago',
  },
]

export const adminQuestions = [
  {
    id: 'aq-01',
    stem: 'Which kind of work gives you the most energy?',
    type: 'Preference',
    status: 'Live',
    signal: 'Role affinity',
  },
  {
    id: 'aq-02',
    stem: 'How do you usually solve a new technical problem?',
    type: 'Behavioral',
    status: 'Live',
    signal: 'Problem framing',
  },
  {
    id: 'aq-03',
    stem: 'Which skill would you most like to sharpen next?',
    type: 'Gap probe',
    status: 'Needs review',
    signal: 'Learning intent',
  },
]

export const adminResources = [
  {
    id: 'ar-01',
    title: 'A/B Testing Foundations',
    skill: 'Experiment Design',
    platform: 'Coursera',
    status: 'Verified',
    score: 91,
  },
  {
    id: 'ar-02',
    title: 'Advanced SQL for Analytics',
    skill: 'SQL Window Functions',
    platform: 'Mode',
    status: 'Verified',
    score: 87,
  },
  {
    id: 'ar-03',
    title: 'Case Study Narrative Clinic',
    skill: 'Portfolio Storytelling',
    platform: 'ADPList',
    status: 'Review',
    score: 68,
  },
]

export const adminActivity = [
  {
    time: '09:42',
    title: 'Job vectors rebuilt',
    detail: '31,408 rows processed with 98.6% usable skill coverage.',
  },
  {
    time: '10:18',
    title: 'Question gap detected',
    detail: 'Marketing senior roles need additional strategic planning prompts.',
  },
  {
    time: '11:05',
    title: 'Resource audit completed',
    detail: 'Two stale links were queued for replacement.',
  },
]
