const ROLE_FILTER_LABELS = {
  'backend-dev': 'Backend Developer',
  'frontend-dev': 'Frontend Developer',
  'fullstack-dev': 'Full Stack Developer',
  'mobile-dev': 'Mobile Developer',
  devops: 'DevOps Engineer',
  'data-analyst': 'Data Analyst',
  'data-scientist': 'Data Scientist',
  'ml-engineer': 'Machine Learning Engineer',
  'ui-ux-designer': 'UI UX Designer',
  'graphic-designer': 'Graphic Designer',
  'project-manager': 'Project Manager',
  sales: 'Sales Representative',
  'digital-marketer': 'Digital Marketer',
  accounting: 'Accountant',
  admin: 'Administration HR',
  architect: 'Architect',
  teacher: 'Teacher',
  transport: 'Transport Logistics',
  'software-engineering': 'Software Engineering',
  'data-ai': 'Data AI',
  design: 'Design',
  operations: 'Operations',
}

export function formatRoleFilterLabel(value) {
  if (!value) {
    return 'All roles'
  }
  const key = String(value).trim()
  return ROLE_FILTER_LABELS[key] || key
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function getProfileRoleFilter(profile) {
  const rawRole =
    profile?.target_role ||
    profile?.detected_role ||
    profile?.top_category ||
    profile?.category ||
    profile?.detected_domain ||
    ''
  const role = String(rawRole || '').trim()
  return ROLE_FILTER_LABELS[role] || role.replace(/[_-]/g, ' ')
}
