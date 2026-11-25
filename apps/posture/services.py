from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.core import audit
from apps.workspaces.models import Workspace

from . import catalog
from .models import Action, ActionEvent, Assessment


class Conflict(Exception):
    pass


def lock_workspace(workspace, *, allow_closed=False):
    locked = Workspace.objects.select_for_update().only("status").get(pk=workspace.pk)
    if not allow_closed and locked.status != Workspace.ACTIVE:
        raise PermissionDenied


def assessments(workspace):
    return Assessment.objects.filter(workspace=workspace)


def latest_assessment(workspace):
    return assessments(workspace).filter(submitted_at__isnull=False).order_by("-submitted_at", "-pk").first()


def draft_for(workspace):
    return assessments(workspace).filter(submitted_at__isnull=True).first()


@transaction.atomic
def start_assessment(workspace, actor):
    lock_workspace(workspace)
    draft = draft_for(workspace)
    return draft or Assessment.objects.create(
        workspace=workspace, created_by=actor, template_version=catalog.CURRENT_VERSION
    )


@transaction.atomic
def save_answer(workspace, assessment_id, revision, question, answer):
    lock_workspace(workspace)
    assessment = assessments(workspace).get(pk=assessment_id)
    if assessment.submitted_at or revision != assessment.revision:
        raise Conflict
    if question not in {item.key for item in catalog.CATALOGS[assessment.template_version]} or answer not in catalog.POINTS:
        raise ValueError("Invalid question or response")
    if assessment.answers.get(question) != answer:
        assessment.answers = {**assessment.answers, question: answer}
        assessment.revision += 1
        assessment.save(update_fields=["answers", "revision", "updated_at"])
    return assessment


@transaction.atomic
def submit_assessment(workspace, actor, assessment_id, revision):
    lock_workspace(workspace)
    assessment = assessments(workspace).get(pk=assessment_id)
    if assessment.submitted_at:
        return assessment
    questions = catalog.CATALOGS[assessment.template_version]
    if assessment.revision != revision or not all(assessment.answers.get(item.key) in catalog.POINTS for item in questions):
        raise Conflict

    assessment.score = catalog.score(assessment.answers, questions)
    assessment.unsure_count = sum(assessment.answers[item.key] == "unsure" for item in questions)
    assessment.submitted_at = timezone.now()
    assessment.revision += 1
    assessment.save(update_fields=["score", "unsure_count", "submitted_at", "revision", "updated_at"])
    existing = {action.key: action for action in Action.objects.filter(workspace=workspace, source_kind="assessment")}
    for question in questions:
        answer = assessment.answers[question.key]
        action = existing.get(question.key)
        if action is None and answer == "yes":
            continue
        reason = {
            "yes": "Your latest assessment reports this practice is in place.",
            "partly": "Your latest assessment reports incomplete coverage.",
            "no": "Your latest assessment reports this practice is missing.",
            "unsure": "Your latest assessment was unsure. Verify the current setup first.",
        }[answer]
        record_finding(
            workspace, actor, action, key=question.key, title=question.action, priority=question.priority,
            reason=reason, steps=question.steps, confirmation=question.confirmation,
            guidance_version=assessment.template_version, source_kind="assessment",
            source_id=assessment.pk, observed_at=assessment.submitted_at, gap=answer != "yes",
        )
    audit.record("assessment.submitted", actor=actor, workspace=workspace, target=assessment.pk)
    return assessment


def record_finding(
    workspace, actor, action, *, key, title, priority, reason, steps, confirmation,
    guidance_version, source_kind, source_id, observed_at, gap,
):
    """Record a new observation while the caller holds the workspace lock."""
    if action is None:
        action = Action(workspace=workspace, key=key)
    elif observed_at <= action.observed_at or action.source_id == source_id:
        return

    reopened = gap and action.done_at is not None and observed_at > action.done_at
    action.title = title
    action.priority = priority
    action.reason = reason
    action.steps = steps
    action.confirmation = confirmation
    action.guidance_version = guidance_version
    action.source_kind = source_kind
    action.source_id = source_id
    action.observed_at = observed_at
    action.current_gap = gap
    if reopened:
        action.status = Action.Status.OPEN
        action.done_at = None
    action.revision += 1
    action.save()
    ActionEvent.objects.create(
        workspace=workspace, action=action, actor=actor,
        event="reopened" if reopened else "evidence_recorded", detail=reason,
    )
    if reopened:
        audit.record("action.reopened", actor=actor, workspace=workspace, target=action.pk)


TRANSITIONS = {
    Action.Status.OPEN: (Action.Status.IN_PROGRESS, Action.Status.DONE),
    Action.Status.IN_PROGRESS: (Action.Status.OPEN, Action.Status.DONE),
    Action.Status.DONE: (Action.Status.OPEN,),
}


@transaction.atomic
def transition_action(workspace, actor, action_id, revision, target):
    lock_workspace(workspace)
    action = Action.objects.get(workspace=workspace, pk=action_id)
    if action.revision != revision or target not in TRANSITIONS[action.status]:
        raise Conflict
    old = action.get_status_display()
    action.status = target
    action.done_at = timezone.now() if target == Action.Status.DONE else None
    action.revision += 1
    action.save(update_fields=["status", "done_at", "revision"])
    ActionEvent.objects.create(
        workspace=workspace, action=action, actor=actor, event="status_changed",
        detail=f"{old} to {Action.Status(target).label}",
    )
    audit.record("action.status_changed", actor=actor, workspace=workspace, target=action.pk)
    return action
