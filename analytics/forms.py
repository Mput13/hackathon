"""
Формы для создания и редактирования воронок
"""
from django import forms
from .models import ConversionFunnel, ProductVersion


class FunnelStepForm(forms.Form):
    """Форма для одного шага воронки"""
    step_type = forms.ChoiceField(
        choices=[
            ('url', 'URL'),
            ('goal', 'Цель (Goal)'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    step_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название шага'})
    )
    step_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://priem.mai.ru/...'})
    )
    step_goal_code = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Код цели из goals.yaml'})
    )


class CreateFunnelForm(forms.ModelForm):
    """Форма для создания кастомной воронки"""
    
    class Meta:
        model = ConversionFunnel
        fields = ['version', 'name', 'description', 'require_sequence', 'allow_skip_steps']
        widgets = {
            'version': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название воронки'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание воронки (необязательно)'}),
            'require_sequence': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_skip_steps': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['version'].queryset = ProductVersion.objects.all().order_by('name')
        self.fields['version'].label = 'Версия продукта'
        self.fields['name'].label = 'Название воронки'
        self.fields['description'].label = 'Описание'
        self.fields['description'].required = False
        self.fields['require_sequence'].label = 'Требовать последовательность шагов'
        self.fields['allow_skip_steps'].label = 'Разрешить пропуск шагов'
    
    # Шаги воронки будут обрабатываться отдельно через JavaScript

