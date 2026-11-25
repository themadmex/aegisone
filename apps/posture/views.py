from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.workspaces.access import workspace_view

from . import catalog, services
from .forms import ActionStatusForm, AnswerForm, RevisionForm
from .models import Action, Assessment


@require_GET
@workspace_view()
def assessment_home(request):
    draft = services.draft_for(request.workspace)
    if draft:
        questions = catalog.CATALOGS[draft.template_version]
        next_item = next((item for item in questions if item.key not in draft.answers), None)
        if next_item:
            return redirect("posture:question", assessment_id=draft.pk, key=next_item.key)
        return redirect("posture:assessment_review", assessment_id=draft.pk)
    return render(request, "posture/assessment_home.html", {
        "nav": "assessment", "latest": services.latest_assessment(request.workspace),
    })


@require_POST
@workspace_view()
def assessment_start(request):
    services.start_assessment(request.workspace, request.user)
    return redirect("posture:assessment")


@require_http_methods(["GET", "POST"])
@workspace_view()
def question(request, assessment_id, key):
    assessment = get_object_or_404(services.assessments(request.workspace), pk=assessment_id)
    if assessment.submitted_at:
        return redirect("posture:assessment_review", assessment_id=assessment.pk)
    questions = catalog.CATALOGS[assessment.template_version]
    positions = {item.key: index for index, item in enumerate(questions)}
    if key not in positions:
        raise Http404
    index = positions[key]
    form = AnswerForm(
        request.POST if request.method == "POST" else None,
        initial={"answer": assessment.answers.get(key), "revision": assessment.revision},
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                services.save_answer(request.workspace, assessment.pk, form.cleaned_data["revision"], key, form.cleaned_data["answer"])
            except services.Conflict:
                messages.error(request, "This assessment changed in another tab. Check the saved answer and try again.")
                return redirect("posture:question", assessment_id=assessment.pk, key=key)
            except Assessment.DoesNotExist as exc:
                raise Http404 from exc
            messages.success(request, "Answer saved.")
            if index + 1 == len(questions):
                return redirect("posture:assessment_review", assessment_id=assessment.pk)
            return redirect("posture:question", assessment_id=assessment.pk, key=questions[index + 1].key)
        status = 400
    return render(request, "posture/question.html", {
        "nav": "assessment", "assessment": assessment, "item": questions[index], "form": form,
        "previous": questions[index - 1] if index else None, "number": index + 1, "total": len(questions),
    }, status=status)


@require_GET
@workspace_view()
def assessment_review(request, assessment_id):
    assessment = get_object_or_404(services.assessments(request.workspace), pk=assessment_id)
    questions = catalog.CATALOGS[assessment.template_version]
    labels = dict(catalog.CHOICES)
    rows = [(item, labels.get(assessment.answers.get(item.key), "Unanswered")) for item in questions]
    return render(request, "posture/assessment_review.html", {
        "nav": "assessment", "assessment": assessment, "rows": rows, "complete": len(assessment.answers) == len(questions),
        "form": RevisionForm(initial={"revision": assessment.revision}),
    })


@require_POST
@workspace_view()
def assessment_submit(request, assessment_id):
    form = RevisionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Reload the assessment before submitting.")
    else:
        try:
            services.submit_assessment(request.workspace, request.user, assessment_id, form.cleaned_data["revision"])
        except services.Conflict:
            messages.error(request, "Finish all answers and review the latest saved changes before submitting.")
        except Assessment.DoesNotExist as exc:
            raise Http404 from exc
        else:
            messages.success(request, "Assessment submitted.")
    return redirect("posture:assessment_review", assessment_id=assessment_id)


@require_GET
@workspace_view()
def actions(request):
    items = Action.objects.filter(workspace=request.workspace)
    selected = request.GET.get("status", "")
    priority = request.GET.get("priority", "")
    if selected in Action.Status.values:
        items = items.filter(status=selected)
    if priority in {"1", "2", "3"}:
        items = items.filter(priority=int(priority))
    if request.GET.get("history") != "1":
        items = items.filter(current_gap=True)
    return render(request, "posture/actions.html", {
        "nav": "actions", "items": items, "statuses": Action.Status.choices, "selected": selected,
        "priorities": [(str(value), label) for value, label in catalog.PRIORITIES], "priority": priority,
        "history": request.GET.get("history") == "1",
    })


@require_http_methods(["GET", "POST"])
@workspace_view()
def action_detail(request, action_id):
    action = get_object_or_404(Action, workspace=request.workspace, pk=action_id)
    if request.method == "POST":
        form = ActionStatusForm(request.POST)
        if form.is_valid():
            try:
                services.transition_action(request.workspace, request.user, action.pk, revision=form.cleaned_data["revision"], target=form.cleaned_data["status"])
            except services.Conflict:
                messages.error(request, "The status changed or that transition is unavailable. Review the current action.")
            else:
                messages.success(request, "Action updated.")
        else:
            messages.error(request, "Choose an available status and try again.")
        return redirect("posture:action_detail", action_id=action.pk)

    targets = [(state, "Reopen" if action.status == Action.Status.DONE else state.label) for state in services.TRANSITIONS[action.status]]
    return render(request, "posture/action_detail.html", {
        "nav": "actions", "action": action, "targets": targets, "history": action.history.all()[:50],
    })
