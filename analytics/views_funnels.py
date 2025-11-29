from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import ProductVersion, ConversionFunnel, FunnelMetrics
from .forms import CreateFunnelForm
from .utils import GoalParser
import json as json_module


def funnels_list(request):
    """Список воронок для версии"""
    version_id = request.GET.get('version')

    versions = ProductVersion.objects.all()
    selected_version = None

    if version_id:
        try:
            selected_version = ProductVersion.objects.get(id=version_id)
        except ProductVersion.DoesNotExist:
            pass

    # Если версия не выбрана, берем первую доступную
    if not selected_version and versions.exists():
        selected_version = versions.first()

    funnels = []
    if selected_version:
        # Показываем все воронки (preset и кастомные)
        funnels = ConversionFunnel.objects.filter(
            version=selected_version
        ).order_by('-is_preset', 'name')  # Сначала preset, потом кастомные

        # Добавляем информацию о метриках
        for funnel in funnels:
            cached_metrics = FunnelMetrics.objects.filter(
                funnel=funnel,
                version=selected_version,
                includes_cohorts=False
            ).first()

            funnel.has_metrics = cached_metrics is not None
            if cached_metrics:
                metrics = cached_metrics.metrics_json
                funnel.total_entered = metrics.get('total_entered', 0)
                funnel.total_completed = metrics.get('total_completed', 0)
                funnel.overall_conversion = metrics.get('overall_conversion', 0)

    context = {
        'versions': versions,
        'selected_version': selected_version,
        'funnels': funnels
    }
    return render(request, 'analytics/funnels.html', context)


def funnel_detail(request, funnel_id):
    """Детальный просмотр воронки"""
    try:
        funnel = ConversionFunnel.objects.select_related('version').get(id=funnel_id)
    except ConversionFunnel.DoesNotExist:
        from django.http import Http404
        raise Http404("Воронка не найдена")

    # Получаем метрики
    cached_metrics = FunnelMetrics.objects.filter(
        funnel=funnel,
        version=funnel.version,
        includes_cohorts=False
    ).first()

    # Получаем метрики по когортам
    cohort_metrics = FunnelMetrics.objects.filter(
        funnel=funnel,
        version=funnel.version,
        includes_cohorts=True
    ).first()

    context = {
        'funnel': funnel,
        'metrics': cached_metrics.metrics_json if cached_metrics else None,
        'cohort_breakdown': cohort_metrics.metrics_json.get('cohort_breakdown', {}) if cohort_metrics else None,
        'has_cohort_metrics': cohort_metrics is not None,
    }

    return render(request, 'analytics/funnel_detail.html', context)


def api_funnels(request):
    """JSON: список воронок для версии"""
    version_id = request.GET.get('version')
    if not version_id:
        return JsonResponse({'error': 'version parameter is required'}, status=400)

    try:
        version = ProductVersion.objects.get(id=version_id)
    except ProductVersion.DoesNotExist:
        return JsonResponse({'error': 'Version not found'}, status=404)

    # Возвращаем все воронки (preset и кастомные)
    funnels = ConversionFunnel.objects.filter(
        version=version
    ).order_by('-is_preset', 'name')

    results = []
    for funnel in funnels:
        # Получаем кэшированные метрики если есть
        cached_metrics = FunnelMetrics.objects.filter(
            funnel=funnel,
            version=version,
            includes_cohorts=False
        ).first()

        funnel_data = {
            'id': funnel.id,
            'name': funnel.name,
            'description': funnel.description,
            'steps_count': len(funnel.steps),
            'steps': funnel.steps,
            'is_preset': funnel.is_preset,
            'has_metrics': cached_metrics is not None,
        }

        if cached_metrics:
            metrics = cached_metrics.metrics_json
            funnel_data.update({
                'total_entered': metrics.get('total_entered', 0),
                'total_completed': metrics.get('total_completed', 0),
                'overall_conversion': metrics.get('overall_conversion', 0),
                'calculated_at': cached_metrics.calculated_at.isoformat(),
            })

        results.append(funnel_data)

    return JsonResponse({'count': len(results), 'results': results})


def api_funnel_detail(request, funnel_id):
    """JSON: детальная информация о воронке с метриками"""
    try:
        funnel = ConversionFunnel.objects.select_related('version').get(id=funnel_id)
    except ConversionFunnel.DoesNotExist:
        return JsonResponse({'error': 'Funnel not found'}, status=404)

    # Получаем кэшированные метрики
    cached_metrics = FunnelMetrics.objects.filter(
        funnel=funnel,
        version=funnel.version,
        includes_cohorts=False
    ).first()

    result = {
        'id': funnel.id,
        'name': funnel.name,
        'description': funnel.description,
        'version': {
            'id': funnel.version.id,
            'name': funnel.version.name
        },
        'steps': funnel.steps,
        'require_sequence': funnel.require_sequence,
        'allow_skip_steps': funnel.allow_skip_steps,
        'is_preset': funnel.is_preset,
    }

    if cached_metrics:
        result['metrics'] = cached_metrics.metrics_json
        result['calculated_at'] = cached_metrics.calculated_at.isoformat()
        result['calculation_duration_sec'] = cached_metrics.calculation_duration_sec
    else:
        result['metrics'] = None
        result['message'] = 'Метрики еще не рассчитаны. Используйте команду calculate_funnels.'

    return JsonResponse({'funnel': result})


def api_funnel_by_cohorts(request, funnel_id):
    """JSON: метрики воронки с разбивкой по когортам"""
    try:
        funnel = ConversionFunnel.objects.select_related('version').get(id=funnel_id)
    except ConversionFunnel.DoesNotExist:
        return JsonResponse({'error': 'Funnel not found'}, status=404)

    # Получаем кэшированные метрики с когортами
    cached_metrics = FunnelMetrics.objects.filter(
        funnel=funnel,
        version=funnel.version,
        includes_cohorts=True
    ).first()

    if not cached_metrics:
        return JsonResponse({
            'error': 'Metrics with cohort breakdown not calculated yet',
            'message': 'Запустите calculate_funnels с флагом --by-cohorts'
        }, status=404)

    result = {
        'funnel': {
            'id': funnel.id,
            'name': funnel.name,
            'version': funnel.version.name
        },
        'overall_metrics': {
            'total_entered': cached_metrics.metrics_json.get('total_entered', 0),
            'total_completed': cached_metrics.metrics_json.get('total_completed', 0),
            'overall_conversion': cached_metrics.metrics_json.get('overall_conversion', 0),
        },
        'cohort_breakdown': cached_metrics.metrics_json.get('cohort_breakdown', {}),
        'calculated_at': cached_metrics.calculated_at.isoformat(),
    }

    return JsonResponse(result)


def funnel_create(request):
    """Создание новой кастомной воронки"""
    if request.method == 'POST':
        form = CreateFunnelForm(request.POST)
        
        # Получаем шаги из JSON
        steps_json = request.POST.get('steps_json', '[]')
        try:
            steps = json_module.loads(steps_json)
        except json_module.JSONDecodeError:
            steps = []
        
        if form.is_valid() and steps:
            funnel = form.save(commit=False)
            funnel.is_preset = False  # Кастомная воронка
            funnel.steps = steps
            funnel.save()
            
            messages.success(request, f'Воронка "{funnel.name}" успешно создана!')
            return redirect('funnel_detail', funnel_id=funnel.id)
        else:
            if not steps:
                form.add_error(None, 'Добавьте хотя бы один шаг воронки')
    else:
        form = CreateFunnelForm()
        # Если передан version_id, устанавливаем его по умолчанию
        version_id = request.GET.get('version')
        if version_id:
            try:
                form.fields['version'].initial = ProductVersion.objects.get(id=version_id)
            except ProductVersion.DoesNotExist:
                pass
    
    # Загружаем список целей для подсказок
    goal_parser = GoalParser()
    goals = goal_parser.get_goals()
    
    context = {
        'form': form,
        'goals_json': json_module.dumps([{'code': g.get('code', ''), 'name': g.get('name', '')} for g in goals]),
        'versions': ProductVersion.objects.all().order_by('name')
    }
    return render(request, 'analytics/funnel_create.html', context)


def funnel_edit(request, funnel_id):
    """Редактирование воронки"""
    funnel = get_object_or_404(ConversionFunnel, id=funnel_id)
    
    # Preset-воронки нельзя редактировать
    if funnel.is_preset:
        messages.error(request, 'Предустановленные воронки нельзя редактировать.')
        return redirect('funnel_detail', funnel_id=funnel.id)
    
    if request.method == 'POST':
        form = CreateFunnelForm(request.POST, instance=funnel)
        
        # Получаем шаги из JSON
        steps_json = request.POST.get('steps_json', '[]')
        try:
            steps = json_module.loads(steps_json)
        except json_module.JSONDecodeError:
            steps = []
        
        if form.is_valid() and steps:
            funnel = form.save(commit=False)
            funnel.steps = steps
            funnel.save()
            
            # Удаляем старые метрики, чтобы они пересчитались
            FunnelMetrics.objects.filter(funnel=funnel).delete()
            
            messages.success(request, f'Воронка "{funnel.name}" успешно обновлена! Не забудьте пересчитать метрики.')
            return redirect('funnel_detail', funnel_id=funnel.id)
        else:
            if not steps:
                form.add_error(None, 'Добавьте хотя бы один шаг воронки')
    else:
        form = CreateFunnelForm(instance=funnel)
    
    # Загружаем список целей для подсказок
    goal_parser = GoalParser()
    goals = goal_parser.get_goals()
    
    context = {
        'form': form,
        'funnel': funnel,
        'goals_json': json_module.dumps([{'code': g.get('code', ''), 'name': g.get('name', '')} for g in goals]),
        'current_steps_json': json_module.dumps(funnel.steps),
        'versions': ProductVersion.objects.all().order_by('name')
    }
    return render(request, 'analytics/funnel_edit.html', context)


def funnel_delete(request, funnel_id):
    """Удаление воронки"""
    funnel = get_object_or_404(ConversionFunnel, id=funnel_id)
    
    # Preset-воронки нельзя удалять
    if funnel.is_preset:
        messages.error(request, 'Предустановленные воронки нельзя удалить.')
        return redirect('funnel_detail', funnel_id=funnel.id)
    
    if request.method == 'POST':
        funnel_name = funnel.name
        funnel.delete()
        messages.success(request, f'Воронка "{funnel_name}" успешно удалена.')
        return redirect('funnels_list')
    
    context = {
        'funnel': funnel
    }
    return render(request, 'analytics/funnel_delete.html', context)


__all__ = [
    'funnels_list',
    'funnel_detail',
    'funnel_create',
    'funnel_edit',
    'funnel_delete',
    'api_funnels',
    'api_funnel_detail',
    'api_funnel_by_cohorts',
]
