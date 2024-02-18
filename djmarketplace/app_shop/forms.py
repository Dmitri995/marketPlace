from datetime import datetime
from django.contrib.auth.forms import UserCreationForm
from .models import User, GoodCart
from django import forms

class UserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

class CartAddForm(forms.ModelForm):

    class Meta:
        model = GoodCart
        fields = ('good_num', )

class RefillBalanceForm(forms.Form):
    card_number = forms.CharField(label='Номер карты', max_length=18, min_length=16,
                                  widget=forms.TextInput(attrs={'placeholder': 'Введите номер карты'}))
    ending_card = forms.DateField(label='Срок действия карты', input_formats=['%m/%y'],
                                      widget=forms.DateInput(attrs={'placeholder': 'MM/YY'}))
    cvv = forms.CharField(label='CVV код', max_length=3, min_length=3,
                          widget=forms.TextInput(attrs={'placeholder': 'CVV'}))
    amount = forms.FloatField(label='Сумма пополнения', min_value=0.01)

    def clean_expiration_date(self):
        expiration_date = self.cleaned_data.get('expiration_date')
        if expiration_date:
            current_year = datetime.now().year % 100
            card_year = expiration_date.year % 100
            if card_year < current_year:
                raise forms.ValidationError('Срок действия карты истек')
        return expiration_date









