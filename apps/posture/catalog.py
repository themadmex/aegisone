"""Released assessment content. Add a new version when changing questions or scoring."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    key: str
    section: str
    prompt: str
    priority: int
    action: str
    steps: str
    confirmation: str


HIGH, MEDIUM, LOW = 1, 2, 3
PRIORITIES = [(HIGH, "High"), (MEDIUM, "Medium"), (LOW, "Low")]
CHOICES = [("yes", "Yes"), ("partly", "Partly"), ("no", "No"), ("unsure", "Unsure")]
POINTS = {"yes": 2, "partly": 1, "no": 0, "unsure": 0}
CURRENT_VERSION = 2
_V1_QUESTIONS = (
    Question("Q01", "Accounts", "Do all administrator accounts use multi-factor authentication?", HIGH, "Protect administrator accounts with MFA", "List administrators and require an authenticator or security key on each account.", "Check the administrator list for successful enrollment."),
    Question("Q02", "Accounts", "Does everyone use multi-factor authentication on company email?", HIGH, "Require MFA for company email", "Turn on the provider's MFA requirement and help staff enrol.", "Review the email provider's enrollment report."),
    Question("Q03", "Accounts", "Does each team member use an individual login for daily work?", MEDIUM, "Replace shared daily logins", "List shared logins and give each person an account with the access they need.", "Confirm routine changes show an individual account in the audit log."),
    Question("Q04", "Accounts", "Do you promptly remove access when someone leaves?", HIGH, "Create a leaver checklist", "List systems to review and assign someone to disable accounts, revoke sessions and recover devices.", "Work through a recent or simulated departure."),
    Question("Q05", "Devices and updates", "Do you keep a list of computers and phones used for work?", MEDIUM, "Start a device register", "Record each work device, its owner and the date its information was checked.", "Compare the register with a sample of devices."),
    Question("Q06", "Devices and updates", "Do all work devices run a supported operating system?", HIGH, "Replace or upgrade unsupported devices", "Compare the operating systems in your register with vendor support dates and schedule upgrades.", "Check the version and support status after upgrading."),
    Question("Q07", "Devices and updates", "Do you install security updates promptly?", HIGH, "Review and install security updates", "Enable automatic updates where practical and assign an owner to check outstanding patches.", "Confirm current security updates on a sample of devices."),
    Question("Q08", "Devices and updates", "Do work devices lock automatically when left unattended?", MEDIUM, "Turn on automatic screen lock", "Set an inactivity timeout and require a PIN, password or approved biometric to unlock.", "Check the timeout and unlock behavior on a representative device."),
    Question("Q09", "Backups", "Do you regularly back up important business data?", HIGH, "Back up business-critical data", "List essential data, assign backup owners and schedule backups for each source.", "Review recent successful backup runs."),
    Question("Q10", "Backups", "Is access to backups separate from everyday work accounts?", HIGH, "Restrict who can change backups", "Give backup access to dedicated accounts and remove unneeded permissions.", "Review who can read, change and delete backups."),
    Question("Q11", "Backups", "Have you recently tested restoring data from a backup?", HIGH, "Test a backup restore", "Restore a representative sample to an isolated location and record how long it took.", "Open restored files and confirm they match the expected data."),
    Question("Q12", "Backups", "Do people know who leads recovery and what should be restored first?", MEDIUM, "Write down recovery responsibilities", "Name a recovery lead and alternate, and list the systems the business needs first.", "Ask both leads to locate the plan and explain the first steps."),
    Question("Q13", "Email and phishing", "Can staff quickly report suspicious email?", MEDIUM, "Publish a suspicious email reporting contact", "Choose a shared reporting route and tell staff what to include.", "Use a harmless sample to practice reporting."),
    Question("Q14", "Email and phishing", "Do you independently confirm payment-detail changes before acting?", HIGH, "Verify payment-detail changes independently", "Require a call to a known number before changing payment instructions.", "Rehearse the callback with a sample change request."),
    Question("Q15", "Email and phishing", "Have staff received guidance on unexpected links and attachments?", MEDIUM, "Brief staff on suspicious links and attachments", "Show common warning signs and tell staff how to review unexpected requests.", "Run a short recognition exercise and discuss the answers."),
    Question("Q16", "Email and phishing", "Has your email provider reviewed your sending domains' SPF and DMARC settings?", MEDIUM, "Review email authentication with your provider", "Ask the provider to review SPF and DMARC for each sending domain before making policy changes.", "Record the provider's findings and approved changes."),
    Question("Q17", "Incident readiness", "Have you named a lead and alternate for security incidents?", MEDIUM, "Name an incident lead and alternate", "Assign a lead and alternate and document how to reach them.", "Confirm both know their responsibilities and can be reached."),
    Question("Q18", "Incident readiness", "Do staff know whom to contact during a security incident?", MEDIUM, "Share the incident escalation route", "Publish contact details and keep them somewhere accessible if company systems are down.", "Ask a few staff to locate the contact information."),
    Question("Q19", "Incident readiness", "Do you keep emergency contacts for critical suppliers?", LOW, "Record critical supplier contacts", "Document support channels and internal account owners for critical suppliers.", "Check that the contacts and account ownership are current."),
    Question("Q20", "Incident readiness", "Have you rehearsed how your team responds to a security incident?", LOW, "Rehearse your incident response", "Run a short tabletop exercise and agree who will make each decision.", "Record the exercise date, lessons and follow-up actions."),
)

CATALOGS = {
    1: _V1_QUESTIONS,
    2: (
        *_V1_QUESTIONS,
        Question(
            "Q21",
            "Incident readiness",
            "If a key work laptop fell off the map tomorrow, would your backups and remote sign-out still save your week?",
            LOW,
            "Run a lost-laptop recovery check",
            "Confirm how to sign out or lock a missing laptop remotely, rotate key credentials, and restore current work onto a spare device.",
            "Walk through what happens in the first hour if a work laptop is left in a taxi.",
        ),
    ),
}


def score(answers, catalog):
    points = sum(POINTS[answers[question.key]] for question in catalog)
    maximum = len(catalog) * 2
    return (100 * points + maximum // 2) // maximum
